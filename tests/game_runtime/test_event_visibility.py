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


def test_typed_wolf_team_skill_events_visible_to_wolves_only() -> None:
    for event_type in {
        EventType.WHITE_WOLF_KILLED,
        EventType.GUARDIAN_WOLF_PROTECTED,
    }:
        visible = resolve_visible_to(
            event_type,
            {"player_id": "wolf_1", "target_id": "wolf_2"},
            wolf_player_ids=["wolf_1", "wolf_2"],
        )

        assert visible == ["wolf_1", "wolf_2"]


def test_typed_private_skill_events_visible_to_actor_only() -> None:
    for event_type in {
        EventType.WOLF_BEAUTY_CHARMED,
        EventType.NIGHTMARE_BLOCKED,
        EventType.MAGICIAN_SWAPPED,
        EventType.RAVEN_MARKED,
    }:
        visible = resolve_visible_to(
            event_type,
            {"player_id": "actor_1", "target_id": "player_2"},
            wolf_player_ids=["wolf_1"],
        )

        assert visible == ["actor_1"]


def test_error_event_is_scoped_to_actor_not_public() -> None:
    # BUG-2: a night-action-failure ERROR carries the actor's player_id; it must
    # default to actor-only (the wolves must NOT learn which seat failed to act,
    # which would leak that the seat has a night role).
    visible = resolve_visible_to(
        EventType.ERROR,
        {"player_id": "player_1", "error": "boom", "error_type": "TimeoutError"},
        wolf_player_ids=["wolf_1", "wolf_2"],
    )
    assert visible == ["player_1"]


def test_error_event_without_actor_is_not_public() -> None:
    # An anonymous error (no player_id, e.g. speech_failed player="*") must fall
    # back to god-only, never broadcast to every seat.
    visible = resolve_visible_to(EventType.ERROR, {"error": "boom"})
    assert visible == []
