from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.core.player import Player
from llm_werewolf.core.roles import Villager, Werewolf


def test_parse_speech_splits_public_and_private() -> None:
    raw = "[[我认为2号玩家发言前后矛盾，需要再听一轮解释]] {我在装村民，不能暴露}"
    decision = WerewolfAdapterBridge.parse_speech(raw)

    assert "2号" in decision.public_speech
    assert decision.private_thought is not None
    assert "装村民" in decision.private_thought


def test_bridge_seat_resolution_uses_global_seat_numbers() -> None:
    targets = [
        Player("player_2", "玩家2", Villager),
        Player("player_4", "玩家4", Werewolf),
    ]
    selected = WerewolfAdapterBridge.parse_target_selection("[[4]]", targets)
    assert selected is targets[1]
