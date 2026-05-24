import json
from pathlib import Path

from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.agent_team.base import DemoAgent
from llm_werewolf.game_runtime.config import create_game_config_from_player_count
from llm_werewolf.game_runtime.role_registry import create_roles
from llm_werewolf.game_runtime.types import Event, EventType
from llm_werewolf.evaluation.models import CheckResult
from llm_werewolf.evaluation.recorder import EvaluationRecorder


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _build_engine() -> GameEngine:
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config)
    players = [DemoAgent(name=f"Player{i}", model="demo") for i in range(config.num_players)]
    roles = create_roles(config.role_names)
    engine.setup_game(players=players, roles=roles)
    return engine


def test_recorder_writes_events_snapshots_errors_and_checks(tmp_path: Path) -> None:
    recorder = EvaluationRecorder(game_dir=tmp_path)
    event = Event(
        event_type=EventType.GAME_STARTED,
        round_number=0,
        phase="setup",
        message="Game started",
        data={"player_count": 6},
    )
    engine = _build_engine()

    recorder.record_event(event)
    recorder.record_snapshot(engine.game_state, label="after_setup")
    recorder.record_error(
        ValueError("bad target"),
        phase="night",
        round_number=1,
        role_name="Werewolf",
    )
    recorder.finalize_checks(
        [
            CheckResult(
                checker="RoleSkillChecker",
                passed=False,
                message="Missing target_id",
            )
        ]
    )

    events = _read_jsonl(tmp_path / "events.jsonl")
    snapshots = _read_jsonl(tmp_path / "snapshots.jsonl")
    errors = _read_jsonl(tmp_path / "errors.jsonl")
    checks = json.loads((tmp_path / "checks.json").read_text(encoding="utf-8"))

    assert events[0]["event_type"] == "game_started"
    assert events[0]["data"] == {"player_count": 6}
    assert snapshots[0]["label"] == "after_setup"
    assert snapshots[0]["state"]["phase"] == "setup"
    assert errors[0]["error_type"] == "ValueError"
    assert errors[0]["role_name"] == "Werewolf"
    assert checks[0]["checker"] == "RoleSkillChecker"
