import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_werewolf.core.serialization import serialize_game_state
from llm_werewolf.core.types import Event, GameStateProtocol
from llm_werewolf.evaluation.models import CheckResult


class EvaluationRecorder:
    """Writes one game's replay artifacts to disk."""

    def __init__(self, game_dir: str | Path) -> None:
        self.game_dir = Path(game_dir)
        self.game_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.game_dir / "events.jsonl"
        self.snapshots_path = self.game_dir / "snapshots.jsonl"
        self.errors_path = self.game_dir / "errors.jsonl"
        self.checks_path = self.game_dir / "checks.json"

    def record_event(self, event: Event) -> None:
        """Append one event as JSONL."""
        self._append_jsonl(self.events_path, event.model_dump(mode="json"))

    def record_snapshot(self, game_state: GameStateProtocol | None, label: str) -> None:
        """Append a game state snapshot with a descriptive label."""
        if game_state is None:
            return

        payload = {
            "label": label,
            "timestamp": datetime.now().isoformat(),
            "state": serialize_game_state(game_state).model_dump(mode="json"),
        }
        self._append_jsonl(self.snapshots_path, payload)

    def record_error(
        self,
        exc: BaseException,
        phase: str | None = None,
        round_number: int | None = None,
        role_name: str | None = None,
    ) -> None:
        """Append an exception with enough context for later triage."""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(exc).__name__,
            "message": str(exc),
            "phase": phase,
            "round_number": round_number,
            "role_name": role_name,
            "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        }
        self._append_jsonl(self.errors_path, payload)

    def finalize_checks(self, results: list[CheckResult]) -> None:
        """Write checker results for the game."""
        payload = [result.model_dump(mode="json") for result in results]
        self.checks_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False))
            f.write("\n")
