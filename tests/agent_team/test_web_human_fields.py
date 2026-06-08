from llm_werewolf.agent_team.agents.human_interactive_agent import HumanInteractiveAgent

WITCH_MSG = """你是 Player1，身份为 Witch。
身份： 女巫 (Witch)
阵营： 好人阵营
- 解药可用： 是。
- 毒药可用： 是。
- 今晚狼人目标是Player3。
可选目标：
- 座位 2：Player2（player_2）
- 座位 4：Player4（player_4）
救人(save) / 毒人 / 不行动。"""


def test_prepare_web_prompt_adds_structured_fields():
    ui = HumanInteractiveAgent.prepare_web_prompt(WITCH_MSG)
    assert ui["self_role"] == "Witch"
    assert ui["kill_target_seat"] == 3
    assert ui["remaining_potions"] == {"save": True, "poison": True}
    assert ui["target_meta"] == [
        {"seat": 2, "name": "Player2"},
        {"seat": 4, "name": "Player4"},
    ]
    assert isinstance(ui["question"], str) and ui["question"]


def test_prepare_web_prompt_no_kill_target_when_absent():
    ui = HumanInteractiveAgent.prepare_web_prompt(
        "你是 Player1，身份为 Seer。\n请查验一名玩家。\n- 座位 2：Player2（player_2）"
    )
    assert ui["self_role"] == "Seer"
    assert ui["kill_target_seat"] is None
    assert ui["remaining_potions"] is None
