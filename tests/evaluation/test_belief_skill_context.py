"""信念分布辅助 Skill「何时使用」文案的测试。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.skill_generation.skill_card_builder import (
    BeliefRunIndex,
    abstract_skill_target_label,
    build_belief_when_clause,
    build_night_action_skill_card,
    build_persuasion_skill_card,
    generalize_seat_references,
)
from llm_werewolf.evaluation.post_game.camp_persuasion import CampSpeechInfluence
from llm_werewolf.evaluation.post_game.run_context import PlayerRosterEntry, RunContext


def _belief_row(
    *,
    observer_id: str,
    observer_seat: int,
    round_number: int = 1,
    anchor: str = "after_speech",
    speaker_id: str = "player_2",
    vote_seat: int = 6,
    first_order: list[dict] | None = None,
    second_order: list[dict] | None = None,
) -> dict:
    return {
        "schema": "belief_snapshot_v1",
        "round": round_number,
        "phase": "day_discussion",
        "anchor": anchor,
        "speaker_id": speaker_id,
        "observer_id": observer_id,
        "observer_seat": observer_seat,
        "vote_intention": {"seat": vote_seat, "reason": "test"},
        "first_order": first_order or [],
        "second_order": second_order or [],
    }


def test_build_belief_when_clause_concentrated() -> None:
    snapshot = _belief_row(
        observer_id="player_2",
        observer_seat=2,
        first_order=[
            {"target_seat": 2, "wolf_probability": 0.0},
            {"target_seat": 6, "wolf_probability": 1.0},
            {"target_seat": 3, "wolf_probability": 0.33},
        ],
    )
    summary = build_belief_when_clause(snapshot)
    assert summary is not None
    assert summary.pattern == "concentrated"
    assert "对单一目标狼信极高" in summary.when_clause
    assert "投票意向已收敛到单一目标" in summary.when_clause
    assert "6号" not in summary.when_clause


def test_build_belief_when_clause_dispersed() -> None:
    snapshot = _belief_row(
        observer_id="player_4",
        observer_seat=4,
        vote_seat=0,
        first_order=[
            {"target_seat": 4, "wolf_probability": 0.0},
            {"target_seat": 1, "wolf_probability": 0.33},
            {"target_seat": 2, "wolf_probability": 0.33},
            {"target_seat": 3, "wolf_probability": 0.33},
        ],
    )
    summary = build_belief_when_clause(snapshot)
    assert summary is not None
    assert summary.pattern in {"dispersed", "undecided"}
    assert "观望" in summary.when_clause


def test_belief_run_index_finds_persuasion_snapshot(tmp_path: Path) -> None:
    rows = [
        _belief_row(
            observer_id="player_2",
            observer_seat=2,
            anchor="initial",
            speaker_id="",
            vote_seat=6,
        ),
        _belief_row(
            observer_id="player_2",
            observer_seat=2,
            anchor="after_speech",
            speaker_id="player_2",
            vote_seat=6,
            first_order=[
                {"target_seat": 2, "wolf_probability": 0.0},
                {"target_seat": 6, "wolf_probability": 1.0},
            ],
        ),
    ]
    (tmp_path / "beliefs.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows),
        encoding="utf-8",
    )
    index = BeliefRunIndex.from_run_dir(tmp_path)
    snapshot = index.find_persuasion_snapshot(observer_id="player_2", round_number=1)
    assert snapshot is not None
    assert snapshot["anchor"] == "after_speech"


def test_persuasion_skill_card_includes_belief_when(tmp_path: Path) -> None:
    speech = CampSpeechInfluence(
        speaker_id="player_2",
        speaker_name="预言家",
        speaker_camp="villager",
        round_number=1,
        phase="day_discussion",
        public_speech="六号是查杀，今天全票出六号，不要分票。",
        swing_count=2,
        camp_aligned_swings=2,
        camp_aligned_score=20,
        matched_round_elimination=True,
    )
    summary = build_belief_when_clause(
        _belief_row(
            observer_id="player_2",
            observer_seat=2,
            first_order=[
                {"target_seat": 2, "wolf_probability": 0.0},
                {"target_seat": 6, "wolf_probability": 1.0},
            ],
            second_order=[{"observer_seat": 6, "suspects_me_as_wolf": 0.8}],
        )
    )
    card = build_persuasion_skill_card(
        role_key="prophet",
        speech=speech,
        ctx=RunContext(run_dir=tmp_path),
        belief_summary=summary,
    )
    assert "信念分布" in card.when_to_use
    assert "对单一目标狼信极高" in card.when_to_use
    assert "6号" not in card.when_to_use
    assert "6号" not in card.public_behavior


def test_generalize_seat_references() -> None:
    assert generalize_seat_references("六号是查杀，今天全票出六号") == "该目标是查杀，今天全票出该目标"
    assert generalize_seat_references("target player_3") == "target 某玩家"


def test_night_action_skill_card_uses_abstract_target() -> None:
    ctx = RunContext(run_dir=Path("."))
    ctx.roster["player_5"] = PlayerRosterEntry(
        player_id="player_5",
        player_name="五号",
        role_name="Werewolf",
        camp="werewolf",
    )
    card = build_night_action_skill_card(
        role_key="prophet",
        event={
            "event_type": "seer_checked",
            "round_number": 1,
            "data": {"target_id": "player_5", "result": "werewolf"},
        },
        ctx=ctx,
    )
    assert "player_5" not in card.public_behavior
    assert "五号" not in card.public_behavior
    assert "验出狼" in card.public_behavior


def test_abstract_skill_target_label_by_role() -> None:
    ctx = RunContext(run_dir=Path("."))
    ctx.roster["player_6"] = PlayerRosterEntry(
        player_id="player_6",
        player_name="六号",
        role_name="Seer",
        camp="villager",
    )
    label = abstract_skill_target_label(ctx, "player_6", action="protect")
    assert label == "疑似预言家位"
    assert "6" not in label
