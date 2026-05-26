"""打分模型 dataclass。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpeechIntentionScore:
    speaker_id: str
    speaker_name: str
    round_number: int
    swing_count: int
    camp_aligned_swings: int
    camp_aligned_score: int
    matched_elimination: bool
    swing_to_final_vote: int
    persuasion_net: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "round_number": self.round_number,
            "swing_count": self.swing_count,
            "camp_aligned_swings": self.camp_aligned_swings,
            "camp_aligned_score": self.camp_aligned_score,
            "matched_elimination": self.matched_elimination,
            "swing_to_final_vote": self.swing_to_final_vote,
            "persuasion_net": self.persuasion_net,
            "intention_total": self.camp_aligned_score + self.swing_to_final_vote * 5,
        }


@dataclass
class PlayerBenefitScore:
    player_id: str
    player_name: str
    role_name: str | None
    camp: str | None
    game_won: int
    elimination_aligned: int
    camp_persuasion_sum: int
    total: int
    breakdown: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "role_name": self.role_name,
            "camp": self.camp,
            "breakdown": self.breakdown,
            "total": self.total,
        }
