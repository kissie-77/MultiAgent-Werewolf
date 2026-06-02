"""game_runtime/event_visibility.py 的测试。"""

from llm_werewolf.game_runtime.types import EventType
from llm_werewolf.game_runtime.events.event_visibility import resolve_visible_to


def test_werewolf_killed_visible_to_witch_only() -> None:
    visible = resolve_visible_to(
        EventType.WEREWOLF_KILLED,
        {"target_id": "v1", "target_name": "Alice"},
        witch_player_ids=["witch_1"],
    )
    assert visible == ["witch_1"]


def test_werewolf_killed_no_witch_in_game() -> None:
    visible = resolve_visible_to(
        EventType.WEREWOLF_KILLED, {"target_id": "v1"}, witch_player_ids=[]
    )
    assert visible == []


def test_seer_checked_still_actor_only() -> None:
    visible = resolve_visible_to(
        EventType.SEER_CHECKED, {"player_id": "seer_1"}, witch_player_ids=["witch_1"]
    )
    assert visible == ["seer_1"]


def test_role_acting_visible_to_actor_only() -> None:
    visible = resolve_visible_to(EventType.ROLE_ACTING, {"player_id": "wolf_1"})
    assert visible == ["wolf_1"]


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
