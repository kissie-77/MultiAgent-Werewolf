"""Frontend write-action HTTP routes (POST)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

from fastapi import Query, Depends, Request, APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from llm_werewolf.interface.api.deps import get_runs_dir, get_configs_dir, get_eval_runs_dir
from llm_werewolf.interface.api.models import ApiResponse
from llm_werewolf.interface.api.models.actions import (
    PageActionSpec,
    HumanInputRequest,
    StartGameRequest,
    HumanInputResponse,
    StartGameResponse,
    ActionSpecResponse,
    CancelGameResponse,
    GameStatusResponse,
    ModelCompareRequest,
    ModelCompareResponse,
    StartGameModesResponse,
    TriggerPostGameRequest,
    TriggerPostGameResponse,
)
from llm_werewolf.interface.api.services.config import compare_models
from llm_werewolf.interface.api.services.replay import extract_game_snapshot
from llm_werewolf.interface.api.services.start_modes import build_start_modes
from llm_werewolf.interface.api.services.event_stream import (
    get_broadcaster,
    event_visible_for,
    read_events_after,
)
from llm_werewolf.interface.api.services.game_sessions import game_session_manager
from llm_werewolf.interface.api.services.human_input import get_input_broker

if TYPE_CHECKING:
    from pathlib import Path
    from collections.abc import AsyncIterator

    from llm_werewolf.interface.api.services.event_stream import EventBroadcaster

router = APIRouter(tags=["actions"])

ACTION_SPECS: list[PageActionSpec] = [
    PageActionSpec(
        page_key="home",
        frontend_route="/",
        action="list_start_modes",
        method="GET",
        api_path="/api/v1/games/modes",
        description="List selectable start modes and preset configs",
        response_model="StartGameModesResponse",
    ),
    PageActionSpec(
        page_key="home",
        frontend_route="/",
        action="start_game",
        method="POST",
        api_path="/api/v1/games/start",
        description="Start a new game from home page",
        request_model="StartGameRequest",
        response_model="StartGameResponse",
    ),
    PageActionSpec(
        page_key="game",
        frontend_route="/game",
        action="start_game",
        method="POST",
        api_path="/api/v1/games/start",
        description="Start game from game page",
        request_model="StartGameRequest",
        response_model="StartGameResponse",
    ),
    PageActionSpec(
        page_key="game",
        frontend_route="/game",
        action="poll_status",
        method="GET",
        api_path="/api/v1/games/{run_id}/status",
        description="Poll game progress for spectate page",
        response_model="GameStatusResponse",
    ),
    PageActionSpec(
        page_key="game",
        frontend_route="/game",
        action="stream_events",
        method="GET",
        api_path="/api/v1/games/{run_id}/stream",
        description="SSE event stream (god or seat view; seat view for web-human requires token)",
        response_model=None,
    ),
    PageActionSpec(
        page_key="game",
        frontend_route="/game",
        action="submit_human_input",
        method="POST",
        api_path="/api/v1/games/{run_id}/input",
        description="Resolve a web-human awaiting_input decision",
        request_model="HumanInputRequest",
        response_model="HumanInputResponse",
    ),
    PageActionSpec(
        page_key="game",
        frontend_route="/game",
        action="cancel_game",
        method="POST",
        api_path="/api/v1/games/{run_id}/cancel",
        description="Cancel running game task",
        response_model="CancelGameResponse",
    ),
    PageActionSpec(
        page_key="replay",
        frontend_route="/replay/{run_id}",
        action="trigger_post_game",
        method="POST",
        api_path="/api/v1/runs/{run_id}/post-game",
        description="Generate or regenerate PostGame artifacts",
        request_model="TriggerPostGameRequest",
        response_model="TriggerPostGameResponse",
    ),
    PageActionSpec(
        page_key="models",
        frontend_route="/models/compare",
        action="compare_models",
        method="POST",
        api_path="/api/v1/models/compare",
        description="Compare models by ID list",
        request_model="ModelCompareRequest",
        response_model="ModelCompareResponse",
    ),
]


@router.get("/actions/spec")
def action_specs() -> ApiResponse[ActionSpecResponse]:
    return ApiResponse(data=ActionSpecResponse(actions=ACTION_SPECS))


@router.get("/games/modes")
def list_start_modes(
    configs_dir=Depends(get_configs_dir),
) -> ApiResponse[StartGameModesResponse]:
    return ApiResponse(data=build_start_modes(configs_dir))


@router.post("/games/start")
async def start_game(
    body: StartGameRequest,
    configs_dir=Depends(get_configs_dir),
    runs_dir=Depends(get_runs_dir),
) -> ApiResponse[StartGameResponse]:
    try:
        data = await game_session_manager.start_game(
            configs_dir=configs_dir,
            runs_dir=runs_dir,
            request=body,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=data)


@router.get("/games/{run_id}/status")
def game_status(
    run_id: str,
    source: Annotated[str | None, Query(pattern="^(runs|eval)$")] = None,
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse[GameStatusResponse]:
    data = game_session_manager.get_status(
        run_id,
        runs_dir=runs_dir,
        eval_runs_dir=eval_runs_dir,
        source=source,
    )
    if data is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return ApiResponse(data=data)


@router.post("/games/{run_id}/cancel")
async def cancel_game(run_id: str) -> ApiResponse[CancelGameResponse]:
    data = await game_session_manager.cancel_game(run_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Active session not found: {run_id}")
    return ApiResponse(data=data)


@router.post("/games/{run_id}/input")
async def submit_human_input(
    run_id: str,
    body: HumanInputRequest,
) -> ApiResponse[HumanInputResponse]:
    """Resolve a suspended web-human decision identified by ``request_id``.

    The per-seat ``token`` (minted by ``start_game``) gates submission so only the seat
    owner can answer. Returns 404 for an unknown run, 403 for a bad token, and 409 when
    no broker is registered or the ``request_id`` is unknown/already consumed/timed out.
    """
    session = game_session_manager._sessions.get(run_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Active session not found: {run_id}")
    if body.token != session.player_token:
        raise HTTPException(status_code=403, detail="Invalid seat token")
    broker = get_input_broker(run_id)
    if broker is None:
        raise HTTPException(status_code=409, detail="No input broker for this run")
    accepted = broker.submit(request_id=body.request_id, payload=body.payload)
    if not accepted:
        raise HTTPException(
            status_code=409,
            detail="Unknown, already-consumed, or expired request_id",
        )
    return ApiResponse(data=HumanInputResponse(run_id=run_id, accepted=True))


@router.post("/runs/{run_id}/post-game")
async def trigger_post_game(
    run_id: str,
    body: TriggerPostGameRequest | None = None,
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse[TriggerPostGameResponse]:
    payload = body or TriggerPostGameRequest()
    data = await game_session_manager.trigger_post_game(
        run_id,
        runs_dir=runs_dir,
        eval_runs_dir=eval_runs_dir,
        source=payload.source,
        force=payload.force,
    )
    if data is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return ApiResponse(data=data)


@router.post("/models/compare")
def compare_models_post(body: ModelCompareRequest) -> ApiResponse[ModelCompareResponse]:
    compare = compare_models(body.ids)
    return ApiResponse(data=ModelCompareResponse(compare=compare))


def _count_events(run_dir: Path) -> int:
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def _sse(event: dict) -> dict:
    """Format an enriched event dict as an unnamed SSE message.

    Intentionally omits a named ``event:`` field so the browser EventSource's
    default ``onmessage`` handler receives every event. The ``snapshot`` and
    ``end`` frames stay named so the client can hook them explicitly; the
    ``event_type`` still travels inside the ``data`` JSON for the reducer.
    """
    return {
        "id": str(event.get("event_id", "")),
        "data": json.dumps(event, ensure_ascii=False),
    }


def _load_god_roster(run_dir: Path) -> object | None:
    """Read the persisted god-view roster, or None when absent/unreadable."""
    roster_path = run_dir / "god_roster.json"
    if not roster_path.is_file():
        return None
    try:
        return json.loads(roster_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _redact_roster_for_seat(roster: object | None, seat: int | None) -> list[dict]:
    """Seat-view roster: seat/name/is_alive for everyone; role/camp only for the
    human's own seat (and fellow werewolves when the human is a werewolf)."""
    if not isinstance(roster, list) or not roster:
        return []
    self_entry = next((r for r in roster if r.get("seat") == seat), None)
    self_is_wolf = bool(self_entry) and self_entry.get("camp") == "werewolf"
    out: list[dict] = []
    for r in roster:
        reveal = (r.get("seat") == seat) or (self_is_wolf and r.get("camp") == "werewolf")
        out.append({
            "seat": r.get("seat"),
            "name": r.get("name"),
            "is_alive": r.get("is_alive", True),
            "role": r.get("role") if reveal else None,
            "camp": r.get("camp") if reveal else None,
        })
    return out


def _initial_snapshot(run_dir: Path, view: str, seat: int | None = None) -> dict:
    """Build the snapshot first-frame payload. god = full roster; seat = redacted."""
    try:
        snap = extract_game_snapshot(run_dir).model_dump()
    except Exception:  # pragma: no cover - snapshot best-effort
        snap = {}
    roster = _load_god_roster(run_dir)
    if roster is not None:
        if view == "god":
            snap["roster"] = roster
        elif view == "seat":
            snap["roster"] = _redact_roster_for_seat(roster, seat)
    return snap


async def _stream_events(
    run_id: str,
    run_dir: Path,
    request: Request,
    broadcaster: EventBroadcaster | None,
    *,
    view: str,
    seat: int | None,
    last_event_id: int,
) -> AsyncIterator[dict]:
    """Yield SSE frames: snapshot, replayed events, then live events until close."""
    # 1) first frame: coarse snapshot (god carries full roster; seat redacted)
    snap = _initial_snapshot(run_dir, view, seat)
    yield {"event": "snapshot", "data": json.dumps(snap, ensure_ascii=False)}

    # 2) replay already-persisted events after last_event_id
    for ev in read_events_after(run_dir, last_event_id):
        if event_visible_for(ev, view=view, seat=seat):
            yield _sse(ev)

    # 3) if the run is live, stream new events until it closes
    if broadcaster is not None and not broadcaster.closed:
        replayed = max(last_event_id, _count_events(run_dir))
        async for ev in broadcaster.subscribe():
            if ev.get("event_id", 0) <= replayed:
                continue
            if await request.is_disconnected():
                break
            if event_visible_for(ev, view=view, seat=seat):
                yield _sse(ev)

    yield {"event": "end", "data": json.dumps({"run_id": run_id})}


@router.get("/games/{run_id}/stream")
async def stream_game(
    run_id: str,
    request: Request,
    view: Annotated[str, Query(pattern="^(god|seat)$")] = "god",
    seat: Annotated[int | None, Query(ge=1, le=20)] = None,
    last_event_id: Annotated[int, Query(ge=0)] = 0,
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> EventSourceResponse:
    run_dir = runs_dir / run_id
    if not run_dir.is_dir():
        alt = eval_runs_dir / run_id
        run_dir = alt if alt.is_dir() else run_dir
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    # Honor the SSE reconnect header if the client sent one.
    header_id = request.headers.get("last-event-id")
    if header_id and header_id.isdigit():
        last_event_id = int(header_id)

    broadcaster = get_broadcaster(run_id)
    return EventSourceResponse(
        _stream_events(
            run_id,
            run_dir,
            request,
            broadcaster,
            view=view,
            seat=seat,
            last_event_id=last_event_id,
        )
    )
