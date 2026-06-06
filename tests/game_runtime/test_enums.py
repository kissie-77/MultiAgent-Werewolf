"""game_runtime/types/enums.py 的事件类型测试。"""

from llm_werewolf.game_runtime.types import EventType


def test_sub_phase_event_type_exists() -> None:
    assert EventType.SUB_PHASE.value == "sub_phase"


def test_typed_skill_event_types_exist() -> None:
    assert EventType.WHITE_WOLF_KILLED.value == "white_wolf_killed"
    assert EventType.WOLF_BEAUTY_CHARMED.value == "wolf_beauty_charmed"
    assert EventType.NIGHTMARE_BLOCKED.value == "nightmare_blocked"
    assert EventType.GUARDIAN_WOLF_PROTECTED.value == "guardian_wolf_protected"
    assert EventType.RAVEN_MARKED.value == "raven_marked"
