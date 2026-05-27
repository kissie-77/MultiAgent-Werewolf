"""game_runtime/event_visibility.py 的测试。"""

from llm_werewolf.game_runtime.events.event_visibility import resolve_visible_to
from llm_werewolf.game_runtime.types import EventType


def test_werewolf_killed_visible_to_witch_only() -> None:
    visible = resolve_visible_to(
        EventType.WEREWOLF_KILLED,
        {"target_id": "v1", "target_name": "Alice"},
        witch_player_ids=["witch_1"],
    )
    assert visible == ["witch_1"]


def test_werewolf_killed_no_witch_in_game() -> None:
    visible = resolve_visible_to(
        EventType.WEREWOLF_KILLED,
        {"target_id": "v1"},
        witch_player_ids=[],
    )
    assert visible == []


def test_seer_checked_still_actor_only() -> None:
    visible = resolve_visible_to(
        EventType.SEER_CHECKED,
        {"player_id": "seer_1"},
        witch_player_ids=["witch_1"],
    )
    assert visible == ["seer_1"]
