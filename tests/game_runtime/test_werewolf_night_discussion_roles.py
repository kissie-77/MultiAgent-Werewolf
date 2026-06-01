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
    assert "补充一个不同角度的理由" in notes[1]
    assert "检查当前刀口的风险" in notes[2]
    assert "收束狼队共识" in notes[3]
    assert len(set(notes)) == 4
