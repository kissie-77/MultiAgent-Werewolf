"""Frontend write-action HTTP routes (POST)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from llm_werewolf.interface.api.deps import get_runs_dir, get_configs_dir, get_eval_runs_dir
from llm_werewolf.interface.api.models import ApiResponse
from llm_werewolf.interface.api.models.actions import (
    PageActionSpec,
    StartGameRequest,
    StartGameResponse,
    ActionSpecResponse,
    CancelGameResponse,
    ControlGameRequest,
    ControlGameResponse,
    GameStatusResponse,
    ModelCompareRequest,
    ModelCompareResponse,
    StartGameModesResponse,
    TriggerPostGameRequest,
    TriggerPostGameResponse,
)
from llm_werewolf.interface.api.models.state import GameStateResponse
from llm_werewolf.interface.api.services.config import compare_models
from llm_werewolf.interface.api.services.runs import get_run_detail
from llm_werewolf.interface.api.services.sse_stream import stream_game
from llm_werewolf.interface.api.services.start_modes import build_start_modes
from llm_werewolf.interface.api.services.game_sessions import game_session_manager

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
        action="get_state",
        method="GET",
        api_path="/api/v1/games/{run_id}/state",
        description="Authoritative live game state snapshot",
        response_model="GameStateResponse",
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
        page_key="game",
        frontend_route="/game",
        action="control_game",
        method="POST",
        api_path="/api/v1/games/{run_id}/control",
        description="Pause / resume / single-step / set speed for a running game",
        request_model="ControlGameRequest",
        response_model="ControlGameResponse",
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


@router.get("/games/{run_id}/view")
def game_view(
    run_id: str,
    since: int = Query(0, ge=0),
    source: str | None = Query(None, pattern="^(runs|eval)$"),
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse:
    data = game_session_manager.get_view(
        run_id, runs_dir=runs_dir, eval_runs_dir=eval_runs_dir, since=since, source=source,
    )
    if data is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return ApiResponse(data=data)


@router.get("/games/{run_id}/stream")
def game_stream(
    run_id: str,
    source: str | None = Query(None, pattern="^(runs|eval)$"),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> StreamingResponse:
    # 0-based seqs: a fresh connection (no Last-Event-ID) uses after_seq=-1 so
    # the very first event (seq 0) is included; Last-Event-ID=N resumes after N.
    try:
        after_seq = int(last_event_id) if last_event_id else -1
    except ValueError:
        after_seq = -1

    from pathlib import Path

    session = game_session_manager.get_session(run_id)
    if session is not None:
        run_dir = session.run_dir
    else:
        detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source or "runs")
        if detail is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        run_dir = Path(detail.path)

    generator = stream_game(session=session, run_dir=run_dir, last_event_id=after_seq)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/games/{run_id}/state")
def game_state_snapshot(
    run_id: str,
    source: str | None = Query(None, pattern="^(runs|eval)$"),
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse[GameStateResponse]:
    data = game_session_manager.get_state(
        run_id, runs_dir=runs_dir, eval_runs_dir=eval_runs_dir, source=source,
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


@router.post("/games/{run_id}/control")
async def control_game(
    run_id: str,
    body: ControlGameRequest,
) -> ApiResponse[ControlGameResponse]:
    try:
        data = await game_session_manager.control(
            run_id, action=body.action, value=body.value
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if data is None:
        raise HTTPException(status_code=404, detail=f"Active session not found: {run_id}")
    return ApiResponse(data=data)


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
