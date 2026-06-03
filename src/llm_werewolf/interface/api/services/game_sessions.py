"""In-process game session manager for web-triggered runs."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from llm_werewolf.interface.api.models.state import GameStateResponse, LastNight
    from llm_werewolf.interface.api.models.view import ViewResponse

from llm_werewolf.evaluation.post_game.event_adapter import event_to_dict
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.config.player_config import PlayersConfig
from llm_werewolf.game_runtime.types import GamePhase
from llm_werewolf.game_runtime.utils import load_config
from llm_werewolf.interface.api.models.actions import (
    CancelGameResponse,
    ControlGameResponse,
    GameStatusResponse,
    StartGameRequest,
    StartGameResponse,
    TriggerPostGameResponse,
)
from llm_werewolf.interface.api.services.config_resolve import resolve_config_for_start
from llm_werewolf.interface.api.services.roster_customize import (
    has_roster_customizations,
    prepare_start_players_config,
    resolve_start_rules,
)
from llm_werewolf.interface.api.services.replay import extract_game_snapshot
from llm_werewolf.interface.api.services.runs import get_run_detail
from llm_werewolf.interface.bootstrap import (
    create_information_hub,
    prepare_game_roster,
    wire_agentscope_after_setup,
)
from llm_werewolf.interface.cli.runtime.finalize_run import finalize_run, persist_run_artifacts

logger = logging.getLogger(__name__)


def _has_human_player(players_config: PlayersConfig) -> bool:
    return any(player.model == "human" for player in players_config.players)


def _write_full_roster(engine: Any, run_dir: Path) -> None:
    """Persist god-view roster (seat -> role/camp/model) at game start for /view."""
    state = getattr(engine, "game_state", None)
    if state is None:
        return
    players = []
    for player in state.players:
        camp = None
        role = getattr(player, "role", None)
        if role is not None and getattr(role, "camp", None) is not None:
            camp = role.camp.value
        try:
            seat = int(player.player_id.rsplit("_", 1)[-1])
        except (ValueError, AttributeError):
            logger.warning(
                "Skipping roster entry with unparseable player_id: %r",
                getattr(player, "player_id", None),
            )
            continue
        players.append({
            "seat": seat,
            "player_id": player.player_id,
            "name": player.name,
            "role": player.get_role_name(),
            "camp": camp,
            "model": getattr(player, "ai_model", "unknown"),
        })
    players.sort(key=lambda p: p["seat"])
    (run_dir / "roster.json").write_text(
        json.dumps({"players": players}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _seat_of(player_id: str) -> int | None:
    """Parse the 1-based seat number out of a 'player_N' id."""
    try:
        return int(player_id.rsplit("_", 1)[-1])
    except (ValueError, AttributeError):
        return None


def _captured_last_night(captured: dict | None) -> "LastNight | None":
    """Convert a capture_phase_snapshot() dict into the typed LastNight model.

    Returns None when no capture exists yet (live composition is then the fallback).
    """
    from llm_werewolf.interface.api.models.state import LastNight, NightDeath

    if not captured:
        return None
    deaths = [
        NightDeath(seat=d["seat"], cause=d.get("cause"))
        for d in captured.get("deaths", [])
        if isinstance(d, dict) and d.get("seat") is not None
    ]
    return LastNight(
        deaths=deaths,
        saved_seat=captured.get("saved_seat"),
        guarded_seat=captured.get("guarded_seat"),
        poisoned_seat=captured.get("poisoned_seat"),
    )


def _dump_roster_without_secrets(players_config: PlayersConfig) -> dict:
    """Serialize roster for disk, stripping per-seat literal api_key."""
    data = players_config.model_dump(mode="json", exclude={"use_agentscope_backend"})
    for player in data.get("players", []):
        player.pop("api_key", None)
    return data


def _playing_event() -> asyncio.Event:
    """Control gate that starts in the 'playing' (set) state."""
    ev = asyncio.Event()
    ev.set()
    return ev


class GameSessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GameSession:
    run_id: str
    run_dir: Path
    config_path: Path
    config_id: str
    status: GameSessionStatus = GameSessionStatus.PENDING
    task: asyncio.Task[Any] | None = None
    error: str | None = None
    result_text: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    completed_at: str | None = None
    players_config: PlayersConfig | None = None
    badge_flow: bool = False
    participation: str | None = None
    rules: str | None = None
    human_seats: list[int] = field(default_factory=list)
    engine: Any | None = None
    gate: asyncio.Event = field(default_factory=lambda: _playing_event())
    step_once: bool = False
    speed: int = 1
    last_night: dict[str, Any] = field(default_factory=dict)

    def capture_phase_snapshot(self) -> None:
        """Snapshot night results BEFORE next_phase()/reset_deaths() clears them."""
        engine = self.engine
        state = getattr(engine, "game_state", None) if engine else None
        if state is None:
            return
        if state.get_phase() != GamePhase.NIGHT:
            return
        deaths = [
            {"seat": _seat_of(pid), "cause": state.death_causes.get(pid, "unknown")}
            for pid in sorted(state.night_deaths)
        ]
        self.last_night = {
            "deaths": [d for d in deaths if d["seat"] is not None],
            "saved_seat": _seat_of(state.witch_saved_target) if state.witch_saved_target else None,
            "guarded_seat": _seat_of(state.guard_protected) if state.guard_protected else None,
            "poisoned_seat": _seat_of(state.witch_poison_target) if state.witch_poison_target else None,
        }


class IncrementalEventWriter:
    """Append engine events to events.jsonl for live spectate polling."""

    def __init__(self, run_dir: Path) -> None:
        self._path = run_dir / "events.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, event: object) -> None:
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event_to_dict(event), ensure_ascii=False) + "\n")


class GameSessionManager:
    """Registry of background game runs started via HTTP POST."""

    def __init__(self) -> None:
        self._sessions: dict[str, GameSession] = {}
        self._lock = asyncio.Lock()

    def reset(self) -> None:
        self._sessions.clear()

    async def start_game(
        self,
        *,
        configs_dir: Path,
        runs_dir: Path,
        request: StartGameRequest,
    ) -> StartGameResponse:
        resolved = resolve_config_for_start(
            configs_dir,
            config_id=request.config_id,
            config_path=request.config_path,
            participation=request.participation,
            rules=request.rules,
        )
        stem = resolved.stem
        base_config = load_config(config_path=resolved)
        participation, rules = resolve_start_rules(request)
        players_config = prepare_start_players_config(base_config, request)
        effective_players_config = players_config or base_config
        if _has_human_player(effective_players_config):
            msg = "Web human-player games are not supported yet; use the CLI werewolf command for human mixed games."
            raise ValueError(msg)
        custom_roster = has_roster_customizations(request)
        badge_flow = bool(request.badge_flow)
        human_seats = list(request.human_seats or [])
        effective_count = len(players_config.players) if players_config else len(base_config.players)

        label = (request.run_label or stem).replace("llm-", "")
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_id = f"{label}-{ts}"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "run_id": run_id,
            "config_id": stem,
            "config_path": str(resolved.as_posix()),
            "status": GameSessionStatus.PENDING.value,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "participation": participation,
            "rules": rules,
            "custom_roster": custom_roster,
            "player_count": effective_count,
            "human_seats": human_seats,
            "badge_flow": badge_flow,
        }
        (run_dir / "run_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if players_config is not None:
            (run_dir / "launch_roster.json").write_text(
                json.dumps(_dump_roster_without_secrets(players_config), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        session = GameSession(
            run_id=run_id,
            run_dir=run_dir,
            config_path=resolved,
            config_id=stem,
            players_config=players_config,
            badge_flow=badge_flow,
            participation=participation,
            rules=rules,
            human_seats=human_seats,
        )

        async with self._lock:
            self._sessions[run_id] = session

        session.task = asyncio.create_task(
            self._run_game(session),
            name=f"game-session-{run_id}",
        )
        session.status = GameSessionStatus.RUNNING

        amp = "&"
        return StartGameResponse(
            run_id=run_id,
            status=session.status.value,
            config_id=stem,
            run_dir=str(run_dir.as_posix()),
            game_page_path=f"/game?run_id={run_id}{amp}source=runs",
            status_path=f"/api/v1/games/{run_id}/status{amp}source=runs",
            replay_page_path=f"/replay/{run_id}{amp}source=runs",
            participation=participation,
            rules=rules,
            player_count=effective_count,
            human_seats=human_seats,
            badge_flow=badge_flow,
            custom_roster=custom_roster,
        )

    @staticmethod
    async def _run_step_pump(session: GameSession, *, dwell: float = 0.4) -> str:
        """Pump engine.step() one phase at a time, honoring the control gate."""
        engine = session.engine
        while not engine.is_over():
            await session.gate.wait()                 # honor pause/step
            await engine.step()                       # one phase
            session.capture_phase_snapshot()          # snapshot BEFORE next clear
            if session.step_once:
                session.step_once = False
                session.gate.clear()
            if dwell:
                await asyncio.sleep(dwell / max(session.speed, 1))
        if engine.game_state and engine.game_state.winner:
            return engine.locale.get("game_over", winner=engine.game_state.winner)
        return engine.locale.get("game_ended", winner="unknown", reason="")

    async def _run_game(self, session: GameSession) -> None:
        try:
            players_config = session.players_config or load_config(config_path=session.config_path)
            players, roles, game_config = prepare_game_roster(players_config)
            if session.badge_flow:
                game_config = game_config.model_copy(update={"enable_sheriff": True})
            engine = GameEngine(
                game_config,
                language=players_config.language,
                information_hub=create_information_hub(),
            )
            writer = IncrementalEventWriter(session.run_dir)
            engine.on_event = writer
            engine.setup_game(players=players, roles=roles)
            session.engine = engine
            _write_full_roster(engine, session.run_dir)
            wire_agentscope_after_setup(engine, players_config)

            session.engine = engine
            result = await self._run_step_pump(session)
            session.result_text = result
            persist_run_artifacts(engine, session.run_dir)
            post = await finalize_run(
                engine,
                session.run_dir,
                game_result_text=result,
                config_path=session.config_path,
                prompt_version=players_config.prompt_version,
            )
            if post.error:
                logger.warning("PostGame failed for %s: %s", session.run_id, post.error)
            session.status = GameSessionStatus.COMPLETED
        except asyncio.CancelledError:
            session.status = GameSessionStatus.CANCELLED
            session.error = "cancelled by client"
            raise
        except Exception as exc:
            session.status = GameSessionStatus.FAILED
            session.error = str(exc) or type(exc).__name__
            logger.exception("Game session %s failed", session.run_id)
        finally:
            session.completed_at = datetime.now().isoformat(timespec="seconds")
            self._write_meta(session)

    def _write_meta(self, session: GameSession) -> None:
        meta = {
            "run_id": session.run_id,
            "config_id": session.config_id,
            "config_path": str(session.config_path.as_posix()),
            "status": session.status.value,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "error": session.error,
            "result_text": session.result_text,
        }
        (session.run_dir / "run_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_status(
        self,
        run_id: str,
        *,
        runs_dir: Path,
        eval_runs_dir: Path,
        source: str | None = None,
    ) -> GameStatusResponse | None:
        session = self._sessions.get(run_id)
        run_dir: Path | None = None
        if session is not None:
            run_dir = session.run_dir
            status = session.status.value
            error = session.error
            result_text = session.result_text
        else:
            detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source or "runs")
            if detail is None:
                return None
            run_dir = Path(detail.path)
            meta_path = run_dir / "run_meta.json"
            status = "completed"
            error = None
            result_text = detail.game_result_text
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    status = str(meta.get("status") or status)
                    error = meta.get("error")
                    result_text = meta.get("result_text") or result_text
                except json.JSONDecodeError:
                    pass

        snapshot = extract_game_snapshot(run_dir) if run_dir and run_dir.is_dir() else None
        detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source or "runs")
        has_post_game = detail.has_post_game if detail else False
        has_replay = detail.has_replay if detail else False

        return GameStatusResponse(
            run_id=run_id,
            source=source or "runs",
            status=status,
            snapshot=snapshot,
            error=error,
            result_text=result_text,
            has_post_game=has_post_game,
            has_replay=has_replay,
        )

    def get_view(
        self, run_id: str, *, runs_dir: Path, eval_runs_dir: Path,
        since: int = 0, source: str | None = None,
    ) -> "ViewResponse | None":
        from llm_werewolf.interface.api.services.view import build_view

        session = self._sessions.get(run_id)
        if session is not None:
            run_dir = session.run_dir
            status_map = {
                GameSessionStatus.RUNNING: "running", GameSessionStatus.PENDING: "running",
                GameSessionStatus.COMPLETED: "ended", GameSessionStatus.CANCELLED: "cancelled",
                GameSessionStatus.FAILED: "error",
            }
            status = status_map.get(session.status, "running")
            error = session.error
        else:
            detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source or "runs")
            if detail is None:
                return None
            run_dir = Path(detail.path)
            status, error = "ended", None
        if not run_dir.is_dir():
            return None
        return build_view(run_dir, since=since, status=status, error=error)

    def get_state(
        self, run_id: str, *, runs_dir: Path, eval_runs_dir: Path,
        source: str | None = None,
    ) -> "GameStateResponse | None":
        from llm_werewolf.game_runtime.state.serialization import serialize_game_state
        from llm_werewolf.interface.api.services.state import (
            build_state_from_snapshot,
            build_state_from_view,
        )
        from llm_werewolf.interface.api.services.view import build_view

        status_map = {
            GameSessionStatus.RUNNING: "running", GameSessionStatus.PENDING: "running",
            GameSessionStatus.COMPLETED: "ended", GameSessionStatus.CANCELLED: "cancelled",
            GameSessionStatus.FAILED: "error",
        }

        session = self._sessions.get(run_id)
        if session is not None and session.engine is not None:
            engine = session.engine
            game_state = getattr(engine, "game_state", None)
            if game_state is not None:
                snapshot = serialize_game_state(game_state)
                camps = {
                    p.player_id: p.get_camp().value
                    for p in game_state.players
                    if getattr(p, "role", None) is not None
                }
                cursor = self._count_events(session.run_dir)
                base_status = status_map.get(session.status, "running")
                play_state = "playing" if session.gate.is_set() else "paused"
                # spec §5.1: a paused RUNNING game collapses status -> "paused"
                status = (
                    "paused"
                    if (base_status == "running" and play_state == "paused")
                    else base_status
                )
                captured = _captured_last_night(session.last_night)
                return build_state_from_snapshot(
                    snapshot,
                    status=status,
                    error=session.error,
                    cursor=cursor,
                    camps=camps,
                    play_state=play_state,
                    speed=session.speed,
                    captured_last_night=captured,
                )

        if session is not None:
            run_dir = session.run_dir
            status = status_map.get(session.status, "running")
            error = session.error
        else:
            detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source or "runs")
            if detail is None:
                return None
            run_dir = Path(detail.path)
            status, error = "ended", None
        if not run_dir.is_dir():
            return None
        view = build_view(run_dir, since=0, status=status, error=error)
        return build_state_from_view(view)

    @staticmethod
    def _count_events(run_dir: Path) -> int:
        path = run_dir / "events.jsonl"
        if not path.is_file():
            return 0
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

    async def cancel_game(self, run_id: str) -> CancelGameResponse | None:
        session = self._sessions.get(run_id)
        if session is None:
            return None
        if session.task and not session.task.done():
            session.task.cancel()
            try:
                await session.task
            except asyncio.CancelledError:
                pass
        if session.status not in {GameSessionStatus.COMPLETED, GameSessionStatus.FAILED}:
            session.status = GameSessionStatus.CANCELLED
            session.completed_at = datetime.now().isoformat(timespec="seconds")
            self._write_meta(session)
        return CancelGameResponse(
            run_id=run_id,
            status=session.status.value,
            message="Game task cancelled",
        )

    async def control(
        self, run_id: str, *, action: str, value: int | None = None
    ) -> ControlGameResponse | None:
        session = self._sessions.get(run_id)
        if session is None:
            return None
        if action == "pause":
            session.gate.clear()
        elif action == "resume":
            session.gate.set()
        elif action == "step":
            session.step_once = True
            session.gate.set()
        elif action == "speed":
            if value not in (1, 2, 4):
                msg = f"speed value must be one of 1, 2, 4; got {value}"
                raise ValueError(msg)
            session.speed = value
        state = getattr(session.engine, "game_state", None)
        phase = state.get_phase().value if state else GamePhase.SETUP.value
        return ControlGameResponse(
            run_id=run_id,
            play_state="playing" if session.gate.is_set() else "paused",
            speed=session.speed,
            phase=phase,
        )

    async def trigger_post_game(
        self,
        run_id: str,
        *,
        runs_dir: Path,
        eval_runs_dir: Path,
        source: str | None = None,
        force: bool = False,
    ) -> TriggerPostGameResponse | None:
        detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source or "runs")
        if detail is None:
            return None
        run_dir = Path(detail.path)
        manifest = run_dir / "post_game_manifest.json"
        if manifest.is_file() and not force:
            return TriggerPostGameResponse(
                run_id=run_id,
                status="skipped",
                message="PostGame artifacts already exist",
                artifacts=[a.name for a in detail.artifacts],
            )

        events_path = run_dir / "events.jsonl"
        if not events_path.is_file():
            return TriggerPostGameResponse(
                run_id=run_id,
                status="failed",
                message="events.jsonl not found; cannot run PostGame",
                artifacts=[],
            )

        post = await finalize_run(
            None,
            run_dir,
            game_result_text=detail.game_result_text,
            config_path=None,
        )
        if post.error:
            return TriggerPostGameResponse(
                run_id=run_id,
                status="failed",
                message=post.error,
                artifacts=post.artifacts,
            )
        return TriggerPostGameResponse(
            run_id=run_id,
            status="completed",
            message="PostGame pipeline finished",
            artifacts=post.artifacts,
        )


game_session_manager = GameSessionManager()
