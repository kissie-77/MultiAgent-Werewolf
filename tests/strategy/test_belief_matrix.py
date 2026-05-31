"""Tests for belief matrix core modules."""

from __future__ import annotations

from llm_werewolf.game_runtime.types import Camp
from llm_werewolf.strategy.belief_state import BeliefLog, BeliefSnapshotRecord, BeliefState
from llm_werewolf.strategy.belief_format import (
    build_agent_belief_context,
    format_belief_context,
    format_belief_summary,
)
from llm_werewolf.strategy.belief_updater import (
    apply_public_elimination_to_all_agents,
    apply_revealed_role,
    ensure_agent_belief_state,
    init_belief_state,
    merge_llm_beliefs,
)
from llm_werewolf.strategy.decisions import (
    BeliefEntry,
    SecondOrderEntry,
    WolfCampDelta,
    GodRoleDelta,
    ExposureRadarDelta,
    MindStateDecision,
    SeatChoiceDecision,
    validate_mind_state_decision,
    validate_seat_choice_reason,
)
from llm_werewolf.strategy.wolf_camp_mind import (
    init_wolf_camp_mind,
    merge_wolf_camp_delta,
    format_wolf_camp_board,
)
from llm_werewolf.evaluation.scoring.belief_calibration import compute_belief_brier_scores


class _Player:
    def __init__(self, player_id: str, *, wolf: bool = False) -> None:
        self.player_id = player_id
        self.name = player_id
        self._alive = True
        self._wolf = wolf
        self.role = type("R", (), {"name": "Werewolf" if wolf else "Villager"})()
        self.agent = type("A", (), {"belief_state": None})()

    def is_alive(self) -> bool:
        return self._alive

    def get_role_name(self) -> str:
        return "Werewolf" if self._wolf else "Villager"

    def get_camp(self):
        return Camp.WEREWOLF if self._wolf else Camp.VILLAGER


def test_init_and_merge_beliefs() -> None:
    players = [_Player("player_1"), _Player("player_2", wolf=True), _Player("player_3")]
    state = init_belief_state(players[0], players)
    merge_llm_beliefs(
        state,
        [BeliefEntry(target_seat=2, wolf_probability=0.8, reason="demo update")],
        [SecondOrderEntry(observer_seat=3, suspects_me_as_wolf=0.4, reason="demo b2")],
        alive_seats={1, 2, 3},
    )
    assert state.first_order[2].wolf_probability == 0.8
    assert state.second_order[3].suspects_me_as_wolf == 0.4


def test_apply_revealed_role_and_public_elimination() -> None:
    players = [_Player("player_1"), _Player("player_2", wolf=True)]
    for player in players:
        ensure_agent_belief_state(player, players)
    apply_public_elimination_to_all_agents(players, eliminated_seat=2, is_werewolf=True)
    assert players[0].agent.belief_state.first_order[2].wolf_probability == 1.0


def test_wolf_camp_merge_and_format() -> None:
    wolves = [_Player("player_3", wolf=True), _Player("player_4", wolf=True)]
    model = init_wolf_camp_mind(wolves)
    delta = WolfCampDelta(
        god_role_intel=[GodRoleDelta(target_seat=1, delta={"Seer": 0.6, "Villager": 0.4})],
        exposure_radar=[ExposureRadarDelta(wolf_seat=3, observer_seat=1, suspicion=0.55)],
    )
    merge_wolf_camp_delta(model, delta, contributor_seat=3, round_number=1)
    text = format_wolf_camp_board(model)
    assert "神职定位" in text
    assert model.revision >= 2


def test_belief_log_jsonl_and_brier(tmp_path) -> None:
    log = BeliefLog()
    log.append(
        BeliefSnapshotRecord(
            round_number=1,
            phase="Day",
            anchor="initial",
            observer_id="player_1",
            observer_seat=1,
            speaker_id="",
            vote_seat=2,
            vote_reason=None,
            first_order=[{"target_seat": 2, "wolf_probability": 0.9}],
            second_order=[],
        )
    )
    path = tmp_path / "beliefs.jsonl"
    log.save_jsonl(path)
    scores = compute_belief_brier_scores(tmp_path, seat_roles={2: "Werewolf"})
    assert scores["aggregate_brier"] == 0.01


def test_format_belief_context_and_summary_include_vote_intention() -> None:
    state = BeliefState(observer_seat=1, last_vote_seat=3)
    state.set_entry(BeliefEntry(target_seat=2, wolf_probability=0.6, note="可疑"))
    state.second_order[2] = SecondOrderEntry(observer_seat=2, suspects_me_as_wolf=0.4)

    context = format_belief_context(state)
    summary = format_belief_summary(state)

    assert "当前信念矩阵" in context
    assert "当前投票意向: 3 号" in context
    assert "上一帧投票意向: 3 号" in summary
    assert "仅填写需要修改的条目" in summary


def test_build_agent_belief_context_for_wolf_includes_wolf_panel() -> None:
    wolves = [_Player("player_3", wolf=True), _Player("player_4", wolf=True)]
    wolf = wolves[0]
    wolf.agent.belief_state = init_belief_state(wolf, wolves)
    model = init_wolf_camp_mind(wolves)
    merge_wolf_camp_delta(
        model,
        WolfCampDelta(
            god_role_intel=[GodRoleDelta(target_seat=1, delta={"Seer": 0.5}, reason="test")],
        ),
        contributor_seat=3,
        round_number=1,
    )

    text = build_agent_belief_context(wolf, alive=wolves, wolf_camp_mind=model)
    assert "当前信念矩阵" in text
    assert "神职定位" in text


def test_validate_mind_state_requires_reason_on_changes() -> None:
    decision = MindStateDecision(
        seat=4,
        reason=None,
        first_order=[BeliefEntry(target_seat=4, wolf_probability=0.8, reason="更可疑")],
        second_order=[],
    )
    errors = validate_mind_state_decision(decision, previous_vote_seat=2)
    assert any("变更投票意向" in err for err in errors)

    decision = MindStateDecision(
        seat=2,
        reason=None,
        first_order=[BeliefEntry(target_seat=4, wolf_probability=0.8)],
        second_order=[],
    )
    errors = validate_mind_state_decision(decision, previous_vote_seat=2)
    assert any("first_order" in err for err in errors)


def test_validate_seat_choice_reason() -> None:
    assert validate_seat_choice_reason(SeatChoiceDecision(seat=2, reason="归票")) == []
    assert validate_seat_choice_reason(SeatChoiceDecision(seat=2, reason=None)) != []


def test_format_belief_batch_log() -> None:
    from llm_werewolf.strategy.belief_format import format_belief_batch_log
    from llm_werewolf.strategy.belief_state import BeliefSnapshotRecord

    records = [
        BeliefSnapshotRecord(
            round_number=1,
            phase="Day",
            anchor="after_speech",
            observer_id="player_1",
            observer_seat=1,
            speaker_id="player_2",
            vote_seat=3,
            vote_reason="更可疑",
            first_order=[{"target_seat": 3, "wolf_probability": 0.7}],
            second_order=[{"observer_seat": 2, "suspects_me_as_wolf": 0.2}],
        )
    ]
    text = format_belief_batch_log(
        records,
        round_number=1,
        phase="Day",
        anchor="after_speech",
        speaker_name="玩家2",
        player_names={"player_1": "玩家1"},
    )
    assert "信念矩阵" in text
    assert "B1[3:0.70]" in text
    assert "意向→3号" in text


def test_sync_belief_context_writes_working_memory() -> None:
    from llm_werewolf.agent_team.memory.runtime_memory_manager import RuntimeMemoryManager
    from llm_werewolf.game_runtime.config.memory_config import MemoryConfig

    manager = RuntimeMemoryManager(
        event_logger=object(),
        role="villager",
        player_id="player_1",
        config=MemoryConfig(),
    )
    state = BeliefState(observer_seat=1, last_vote_seat=2)
    state.set_entry(BeliefEntry(target_seat=3, wolf_probability=0.7, note="可疑"))

    manager.sync_belief_context(state)
    context = manager.get_context_for_decision()

    assert "【内心信念】" in context
    assert "3→0.70" in context
    assert "当前投票意向: 2 号" in context
    assert "【信念/意向更新规则】" in context
