"""投票意向追踪，用于复盘 / 说服分析（Foaster 风格）。"""

from __future__ import annotations

from enum import Enum
import json
from typing import TYPE_CHECKING, Any
from pathlib import Path
from dataclasses import field, dataclass

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import PlayerProtocol


class VoteIntentionAnchor(str, Enum):
    """全桌意向快照的采集时机。"""

    INITIAL = "initial"
    AFTER_SPEECH = "after_speech"
    BEFORE = "before"  # 已弃用：仅旧日志使用


@dataclass
class VoteIntentionEntry:
    """某次快照中一名玩家声明的投票意向。"""

    player_id: str
    player_name: str
    seat: int
    target_id: str | None
    target_name: str | None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "seat": self.seat,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "reason": self.reason,
        }


@dataclass
class VoteSwing:
    """两次快照之间某玩家意向的变化。"""

    player_id: str
    player_name: str
    from_seat: int
    to_seat: int
    from_target_id: str | None
    to_target_id: str | None
    from_target_name: str | None
    to_target_name: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "from_seat": self.from_seat,
            "to_seat": self.to_seat,
            "from_target_id": self.from_target_id,
            "to_target_id": self.to_target_id,
            "from_target_name": self.from_target_name,
            "to_target_name": self.to_target_name,
        }


@dataclass
class VoteIntentionSnapshot:
    """某一锚点时刻的全桌投票意向。"""

    round_number: int
    phase: str
    channel: str
    anchor: VoteIntentionAnchor
    speaker_id: str
    speaker_name: str
    intentions: dict[str, VoteIntentionEntry]

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_number": self.round_number,
            "phase": self.phase,
            "channel": self.channel,
            "anchor": self.anchor.value,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "intentions": {pid: entry.to_dict() for pid, entry in self.intentions.items()},
        }


@dataclass
class SpeechVoteIntentionRecord:
    """圆桌发言前后意向对比记录。"""

    round_number: int
    phase: str
    channel: str
    speaker_id: str
    speaker_name: str
    public_speech: str
    before: dict[str, VoteIntentionEntry]
    after: dict[str, VoteIntentionEntry]
    swings: list[VoteSwing] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_number": self.round_number,
            "phase": self.phase,
            "channel": self.channel,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "public_speech": self.public_speech,
            "before": {pid: e.to_dict() for pid, e in self.before.items()},
            "after": {pid: e.to_dict() for pid, e in self.after.items()},
            "swings": [s.to_dict() for s in self.swings],
            "swing_count": len(self.swings),
        }


def compute_vote_swings(
    before: dict[str, VoteIntentionEntry], after: dict[str, VoteIntentionEntry]
) -> list[VoteSwing]:
    """返回意向投票目标发生变化的玩家。"""
    swings: list[VoteSwing] = []
    for player_id, before_entry in before.items():
        after_entry = after.get(player_id)
        if after_entry is None:
            continue
        if (
            before_entry.seat == after_entry.seat
            and before_entry.target_id == after_entry.target_id
        ):
            continue
        swings.append(
            VoteSwing(
                player_id=player_id,
                player_name=before_entry.player_name,
                from_seat=before_entry.seat,
                to_seat=after_entry.seat,
                from_target_id=before_entry.target_id,
                to_target_id=after_entry.target_id,
                from_target_name=before_entry.target_name,
                to_target_name=after_entry.target_name,
            )
        )
    return swings


def format_intentions_line(intentions: dict[str, VoteIntentionEntry]) -> str:
    """事件日志 / 控制台用的一行紧凑摘要。"""
    parts: list[str] = []
    for entry in sorted(intentions.values(), key=lambda e: e.player_id):
        if entry.seat == 0 or entry.target_name is None:
            parts.append(f"{entry.player_name}→无")
        else:
            parts.append(f"{entry.player_name}→{entry.target_name}")
    return ", ".join(parts)


class VoteIntentionTracker:
    """累积与发言关联的意向快照，供导出 / 事件使用。"""

    def __init__(self) -> None:
        self.snapshots: list[VoteIntentionSnapshot] = []
        self.speech_records: list[SpeechVoteIntentionRecord] = []

    def add_snapshot(self, snapshot: VoteIntentionSnapshot) -> None:
        self.snapshots.append(snapshot)

    def record_speech_block(
        self,
        *,
        round_number: int,
        phase: str,
        channel: str,
        speaker: PlayerProtocol,
        public_speech: str,
        before: dict[str, VoteIntentionEntry],
        after: dict[str, VoteIntentionEntry],
    ) -> SpeechVoteIntentionRecord:
        swings = compute_vote_swings(before, after)
        record = SpeechVoteIntentionRecord(
            round_number=round_number,
            phase=phase,
            channel=channel,
            speaker_id=speaker.player_id,
            speaker_name=speaker.name,
            public_speech=public_speech,
            before=before,
            after=after,
            swings=swings,
        )
        self.speech_records.append(record)
        return record

    def export_records(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.speech_records]

    def save_jsonl(self, path: str | Path) -> None:
        """将发言关联的意向记录持久化，供离线分析。"""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            for record in self.export_records():
                handle.write(json.dumps(record, ensure_ascii=False))
                handle.write("\n")
