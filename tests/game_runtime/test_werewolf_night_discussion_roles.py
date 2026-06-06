from dataclasses import dataclass

from llm_werewolf.game_runtime.engine.night_phase import NightPhaseMixin


@dataclass
class FakeWolf:
    player_id: str


def test_werewolf_discussion_role_note_varies_by_team_order() -> None:
    wolves = [FakeWolf("p1"), FakeWolf("p2"), FakeWolf("p3"), FakeWolf("p4")]

    notes = [
        NightPhaseMixin._werewolf_discussion_role_note(wolf, wolves) for wolf in wolves
    ]

    assert "提出一个明确刀口" in notes[0]
    assert "综合前面已发言队友" in notes[1]
    assert "检查前面提案的风险" in notes[2]
    assert "收束前面所有队友的共识和分歧" in notes[3]
    assert len(set(notes)) == 4


def test_first_night_werewolf_grounding_note_blocks_day_evidence() -> None:
    note = NightPhaseMixin._werewolf_discussion_grounding_note(1)

    assert "尚未经历白天公开发言和投票" in note
    assert "禁止引用任何白天发言" in note
    assert "票型" in note
    assert "活跃度" in note
