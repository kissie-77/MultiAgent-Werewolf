from llm_werewolf.core.types import Event, EventType
from llm_werewolf.evaluation.checkers import (
    AsyncFlowChecker,
    InformationIsolationChecker,
    RoleSkillChecker,
    VictoryCheckerEvaluator,
)


def test_information_isolation_checker_detects_private_event_leak() -> None:
    event = Event(
        event_type=EventType.PLAYER_DISCUSSION,
        round_number=1,
        phase="night",
        message="secret wolf plan",
        visible_to=["player_1", "player_2"],
    )

    results = InformationIsolationChecker().check(
        events=[event],
        observations_by_player={"player_3": "Visible event history:\n- secret wolf plan"},
    )

    assert len(results) == 1
    assert not results[0].passed
    assert results[0].data["player_id"] == "player_3"


def test_async_flow_checker_detects_illegal_phase_jump() -> None:
    events = [
        Event(
            event_type=EventType.PHASE_CHANGED,
            round_number=1,
            phase="night",
            message="night starts",
        ),
        Event(
            event_type=EventType.PHASE_CHANGED,
            round_number=1,
            phase="day_voting",
            message="voting starts too early",
        ),
    ]

    results = AsyncFlowChecker().check(events=events)

    assert len(results) == 1
    assert not results[0].passed
    assert results[0].data["from_phase"] == "night"
    assert results[0].data["to_phase"] == "day_voting"


def test_victory_checker_evaluator_detects_winner_mismatch() -> None:
    event = Event(
        event_type=EventType.GAME_ENDED,
        round_number=2,
        phase="ended",
        message="werewolf wins",
        data={"winner_camp": "werewolf"},
    )

    results = VictoryCheckerEvaluator().check(events=[event], final_winner="villager")

    assert len(results) == 1
    assert not results[0].passed
    assert results[0].data == {"event_winner": "werewolf", "final_winner": "villager"}


def test_role_skill_checker_detects_missing_structured_fields() -> None:
    event = Event(
        event_type=EventType.WITCH_SAVED,
        round_number=1,
        phase="night",
        message="Witch saved someone",
        data={"actor_id": "player_3"},
    )

    results = RoleSkillChecker().check(events=[event])

    assert len(results) == 1
    assert not results[0].passed
    assert results[0].data["event_type"] == "witch_saved"
    assert results[0].data["missing_fields"] == ["target_id"]
