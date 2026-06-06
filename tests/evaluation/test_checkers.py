from llm_werewolf.game_runtime.types import Camp, Event, EventType
from llm_werewolf.evaluation.core.checkers import (
    AsyncFlowChecker,
    RoleSkillChecker,
    PromptBadCaseChecker,
    VictoryCheckerEvaluator,
    DecisionConsistencyChecker,
    InformationIsolationChecker,
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


def test_role_skill_checker_covers_extended_skill_events() -> None:
    events = [
        Event(event_type=event_type, round_number=1, phase="night", message="skill", data={})
        for event_type in (
            EventType.WHITE_WOLF_KILLED,
            EventType.WOLF_BEAUTY_CHARMED,
            EventType.NIGHTMARE_BLOCKED,
            EventType.GUARDIAN_WOLF_PROTECTED,
            EventType.RAVEN_MARKED,
        )
    ]

    results = RoleSkillChecker().check(events)

    assert {result.data["event_type"] for result in results} == {
        "white_wolf_killed",
        "wolf_beauty_charmed",
        "nightmare_blocked",
        "guardian_wolf_protected",
        "raven_marked",
    }
    assert all(result.data["missing_fields"] == ["actor_id", "target_id"] for result in results)


def test_role_skill_checker_treats_witch_poison_death_as_plain_death() -> None:
    event = Event(
        event_type=EventType.PLAYER_DIED,
        round_number=1,
        phase="night",
        message="Player was poisoned by witch",
        data={"player_id": "player_2", "reason": "witch_poison", "cause": "witch_poison"},
    )

    results = RoleSkillChecker().check(events=[event])

    assert results == []


def test_decision_checker_detects_target_mismatch() -> None:
    event = Event(
        event_type=EventType.VOTE_CAST,
        round_number=1,
        phase="day_voting",
        message="vote",
        data={
            "voter_id": "player_1",
            "target_id": "player_2",
            "decision": {"resolved_target_id": "player_3"},
        },
    )

    results = DecisionConsistencyChecker().check([event])

    assert len(results) == 1
    assert results[0].checker == "DecisionConsistencyChecker"


def test_decision_checker_detects_private_markers_in_public_speech() -> None:
    event = Event(
        event_type=EventType.PLAYER_SPEECH,
        round_number=1,
        phase="day_discussion",
        message="speech",
        data={"player_id": "player_1", "speech": "{我是狼人} 大家好"},
    )

    results = DecisionConsistencyChecker().check([event])

    assert len(results) == 1
    assert "private-thought" in results[0].message


def test_prompt_bad_case_checker_detects_short_or_generic_speech() -> None:
    event = Event(
        event_type=EventType.PLAYER_SPEECH,
        round_number=1,
        phase="day_discussion",
        message="Player speaks",
        data={"player_id": "player_1", "speech": "大家谨慎一点"},
    )

    results = PromptBadCaseChecker().check(events=[event])

    assert any(
        "too generic" in r.message or "too short" in r.message or "seat token" in r.message
        for r in results
    )


def test_prompt_bad_case_checker_detects_repeated_seer_target() -> None:
    events = [
        Event(
            event_type=EventType.SEER_CHECKED,
            round_number=1,
            phase="night",
            message="Seer checked player 2",
            data={"target_id": "player_2", "result": "villager"},
        ),
        Event(
            event_type=EventType.SEER_CHECKED,
            round_number=2,
            phase="night",
            message="Seer checked player 2 again",
            data={"target_id": "player_2", "result": "villager"},
        ),
    ]

    results = PromptBadCaseChecker().check(events=events)

    assert len(results) == 1
    assert results[0].data["target_id"] == "player_2"


def test_prompt_bad_case_checker_detects_death_shot_on_villager() -> None:
    event = Event(
        event_type=EventType.HUNTER_REVENGE,
        round_number=2,
        phase="day_voting",
        message="Hunter shoots player 3",
        data={"shooter_id": "player_1", "target_id": "player_3", "role": "Hunter"},
    )

    results = PromptBadCaseChecker().check(
        events=[event],
        player_roles={"player_3": "Villager"},
        player_camps={"player_3": Camp.VILLAGER},
    )

    assert len(results) == 1
    assert results[0].data["target_role"] == "Villager"


def test_prompt_bad_case_checker_detects_witch_poison_used_on_villager() -> None:
    event = Event(
        event_type=EventType.WITCH_POISON_USED,
        round_number=2,
        phase="night",
        message="Witch poisoned player 3",
        data={"player_id": "player_1", "target_id": "player_3"},
    )

    results = PromptBadCaseChecker().check(
        events=[event],
        player_roles={"player_3": "Villager"},
        player_camps={"player_3": Camp.VILLAGER},
    )

    assert len(results) == 1
    assert results[0].data["target_role"] == "Villager"


def test_prompt_bad_case_checker_detects_unsupported_public_role_claim() -> None:
    event = Event(
        event_type=EventType.PLAYER_SPEECH,
        round_number=1,
        phase="day_discussion",
        message="speech",
        data={"player_id": "player_6", "speech": "2号跳女巫救了3号，这点很关键。"},
    )

    results = PromptBadCaseChecker().check(events=[event])

    assert any("without prior public support" in result.message for result in results)
    unsupported = next(
        result for result in results if "without prior public support" in result.message
    )
    assert unsupported.data["bad_case_kind"] == "hallucination"
    assert unsupported.data["confidence"] == "high"
    assert unsupported.data["confidence_score"] == 0.86


def test_prompt_bad_case_checker_detects_night_claim_before_public_context() -> None:
    event = Event(
        event_type=EventType.PLAYER_DISCUSSION,
        round_number=1,
        phase="night",
        message="wolf talk",
        data={
            "player_id": "player_2",
            "speech": "我建议刀5号，5号在白天发言时感觉比较活跃，容易带队。",
        },
    )

    results = PromptBadCaseChecker().check(events=[event])

    unsupported = next(
        result for result in results if "before any public context" in result.message
    )
    assert unsupported.data["bad_case_kind"] == "hallucination"
    assert unsupported.data["confidence"] == "high"
    assert unsupported.data["confidence_score"] == 0.88


def test_prompt_bad_case_checker_allows_night_claim_after_public_context() -> None:
    events = [
        Event(
            event_type=EventType.PLAYER_SPEECH,
            round_number=1,
            phase="day_discussion",
            message="speech",
            data={"player_id": "player_5", "speech": "我今天先强势站边2号。"},
        ),
        Event(
            event_type=EventType.PLAYER_DISCUSSION,
            round_number=2,
            phase="night",
            message="wolf talk",
            data={
                "player_id": "player_2",
                "speech": "5号白天发言站边很明确，今晚可以考虑刀5号。",
            },
        ),
    ]

    results = PromptBadCaseChecker().check(events=events)

    assert not any("before any public context" in result.message for result in results)


def test_prompt_bad_case_checker_classifies_generic_speech() -> None:
    event = Event(
        event_type=EventType.PLAYER_SPEECH,
        round_number=1,
        phase="day_discussion",
        message="speech",
        data={"player_id": "player_1", "speech": "我同意前面的说法，大家谨慎一点，先稳住再继续观察。"},
    )

    results = PromptBadCaseChecker().check(events=[event])

    generic = next(result for result in results if "too generic" in result.message)
    assert generic.data["bad_case_kind"] == "low_information"
    assert generic.data["confidence"] == "medium"


def test_prompt_bad_case_checker_allows_claim_with_prior_public_support() -> None:
    events = [
        Event(
            event_type=EventType.PLAYER_SPEECH,
            round_number=1,
            phase="day_discussion",
            message="speech",
            data={"player_id": "player_2", "speech": "我是女巫，昨晚救了3号。"},
        ),
        Event(
            event_type=EventType.PLAYER_SPEECH,
            round_number=1,
            phase="day_discussion",
            message="speech",
            data={"player_id": "player_6", "speech": "2号跳女巫救了3号，我先记下。"},
        ),
    ]

    results = PromptBadCaseChecker().check(events=events)

    assert not any("without prior public support" in result.message for result in results)
