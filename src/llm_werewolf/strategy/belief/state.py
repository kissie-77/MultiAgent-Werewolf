"""Per-agent and god-view belief matrix state."""

from __future__ import annotations

import json
from typing import Any
from pathlib import Path
from dataclasses import field, dataclass

from llm_werewolf.strategy.contracts.decisions import BeliefEntry, SecondOrderEntry, WolfCampDelta


@dataclass
class BeliefState:
    """One agent's first- and second-order beliefs about other seats."""

    observer_seat: int = 0
    first_order: dict[int, BeliefEntry] = field(default_factory=dict)
    second_order: dict[int, SecondOrderEntry] = field(default_factory=dict)
    last_vote_seat: int | None = None

    def get_entry(self, target_seat: int) -> BeliefEntry | None:
        return self.first_order.get(target_seat)

    def set_entry(self, entry: BeliefEntry) -> None:
        self.first_order[entry.target_seat] = entry

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "observer_seat": self.observer_seat,
            "first_order": [e.model_dump() for e in sorted(self.first_order.values(), key=lambda x: x.target_seat)],
            "second_order": [
                e.model_dump() for e in sorted(self.second_order.values(), key=lambda x: x.observer_seat)
            ],
        }


@dataclass
class BeliefSnapshotRecord:
    """One mind-state collection event for beliefs.jsonl."""

    round_number: int
    phase: str
    anchor: str
    observer_id: str
    observer_seat: int
    speaker_id: str
    vote_seat: int
    vote_reason: str | None
    first_order: list[dict[str, Any]]
    second_order: list[dict[str, Any]]
    wolf_camp_delta: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "belief_snapshot_v1",
            "round": self.round_number,
            "phase": self.phase,
            "anchor": self.anchor,
            "speaker_id": self.speaker_id,
            "observer_id": self.observer_id,
            "observer_seat": self.observer_seat,
            "vote_intention": {"seat": self.vote_seat, "reason": self.vote_reason},
            "first_order": self.first_order,
            "second_order": self.second_order,
            "wolf_camp_delta": self.wolf_camp_delta,
        }


@dataclass
class BeliefLog:
    """God-view belief timeline persisted after the game."""

    records: list[BeliefSnapshotRecord] = field(default_factory=list)

    def append(self, record: BeliefSnapshotRecord) -> None:
        self.records.append(record)

    def save_jsonl(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            for record in self.records:
                handle.write(json.dumps(record.to_dict(), ensure_ascii=False))
                handle.write("\n")


@dataclass
class MindStateResult:
    """Combined vote intention + belief update from one LLM call."""

    vote_seat: int
    vote_reason: str | None
    first_order: list[BeliefEntry]
    second_order: list[SecondOrderEntry]
    wolf_camp_delta: WolfCampDelta | None = None
