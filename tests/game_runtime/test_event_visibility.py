"""game_runtime/event_visibility.py 的测试。"""

from llm_werewolf.game_runtime.types import EventType
from llm_werewolf.game_runtime.events.event_visibility import resolve_visible_to


def test_werewolf_killed_visible_to_wolf_team_and_witch() -> None:
    visible = resolve_visible_to(
        EventType.WEREWOLF_KILLED,
        {"target_id": "v1", "target_name": "Alice"},
        wolf_player_ids=["wolf_1", "wolf_2"],
        witch_player_ids=["witch_1"],
    )
    assert visible == ["wolf_1", "wolf_2", "witch_1"]


def test_werewolf_killed_no_witch_in_game() -> None:
    visible = resolve_visible_to(
        EventType.WEREWOLF_KILLED,
        {"target_id": "v1"},
        wolf_player_ids=["wolf_1"],
        witch_player_ids=[],
    )
    assert visible == ["wolf_1"]


def test_werewolf_killed_without_wolves_or_witch_is_not_public() -> None:
    visible = resolve_visible_to(EventType.WEREWOLF_KILLED, {"target_id": "v1"})

    assert visible == []


def test_seer_checked_still_actor_only() -> None:
    visible = resolve_visible_to(
        EventType.SEER_CHECKED, {"player_id": "seer_1"}, witch_player_ids=["witch_1"]
    )
    assert visible == ["seer_1"]


def test_witch_poison_used_visible_to_actor_only() -> None:
    visible = resolve_visible_to(
        EventType.WITCH_POISON_USED,
        {"player_id": "witch_1", "target_id": "player_2"},
        witch_player_ids=["witch_1"],
    )
    assert visible == ["witch_1"]


def test_witch_poison_death_is_public_death_event() -> None:
    visible = resolve_visible_to(
        EventType.PLAYER_DIED,
        {"player_id": "player_2", "reason": "witch_poison", "cause": "witch_poison"},
        witch_player_ids=["witch_1"],
    )
    assert visible is None


def test_role_acting_visible_to_actor_only() -> None:
    visible = resolve_visible_to(EventType.ROLE_ACTING, {"player_id": "wolf_1"})
    assert visible == ["wolf_1"]


def test_private_actor_event_without_actor_id_is_not_public() -> None:
    visible = resolve_visible_to(EventType.ROLE_ACTING, {})
    assert visible == []


def test_lovers_linked_without_cupid_id_is_not_public() -> None:
    visible = resolve_visible_to(EventType.LOVERS_LINKED, {})
    assert visible == []


def test_replay_only_events_are_hidden_from_observation() -> None:
    assert resolve_visible_to(EventType.VOTE_INTENTION_SNAPSHOT, {}) == []
    assert resolve_visible_to(EventType.BELIEF_SNAPSHOT, {}) == []


def test_day_vote_cast_is_public() -> None:
    assert resolve_visible_to(EventType.VOTE_CAST, {"voter_id": "player_1"}) is None


def test_werewolf_narrator_messages_visible_to_wolf_team_only() -> None:
    visible = resolve_visible_to(
        EventType.MESSAGE,
        {"action": "werewolves_wake"},
        wolf_player_ids=["wolf_1", "wolf_2"],
    )

    assert visible == ["wolf_1", "wolf_2"]


def test_wolf_team_message_without_wolves_is_not_public() -> None:
    visible = resolve_visible_to(
        EventType.MESSAGE,
        {"visibility": "wolf_team"},
        wolf_player_ids=[],
    )

    assert visible == []


def test_white_wolf_and_guardian_wolf_visible_to_wolf_team() -> None:
    wolves = ["w1", "w2"]
    assert resolve_visible_to(
        EventType.WHITE_WOLF_KILLED, {"target_id": "v1"}, wolf_player_ids=wolves
    ) == ["w1", "w2"]
    assert resolve_visible_to(
        EventType.GUARDIAN_WOLF_PROTECTED, {"actor_id": "w2", "target_id": "w1"},
        wolf_player_ids=wolves,
    ) == ["w1", "w2"]


def test_wolf_beauty_nightmare_raven_visible_to_actor_only() -> None:
    for event_type in (
        EventType.WOLF_BEAUTY_CHARMED,
        EventType.NIGHTMARE_BLOCKED,
        EventType.RAVEN_MARKED,
    ):
        assert resolve_visible_to(
            event_type, {"actor_id": "a1", "target_id": "t1"}, wolf_player_ids=["a1"]
        ) == ["a1"]


def test_magician_swap_visible_to_actor_only() -> None:
    # Magician 走 PRIVATE_ACTOR_TYPES（player_id），不在 actor_id 系的 ACTOR_ONLY_SKILL_TYPES。
    assert resolve_visible_to(
        EventType.MAGICIAN_SWAPPED,
        {"player_id": "actor_1", "target1_id": "t1", "target2_id": "t2"},
        wolf_player_ids=["wolf_1"],
    ) == ["actor_1"]


def test_sub_phase_is_public() -> None:
    assert resolve_visible_to(EventType.SUB_PHASE, {"name": "werewolf_chat"}) is None


def test_actor_thinking_is_public() -> None:
    assert resolve_visible_to(EventType.ACTOR_THINKING, {"player_id": "player_1"}) is None
