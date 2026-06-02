"""HumanInteractiveAgent prompt rendering tests."""

from llm_werewolf.agent_team.agents.human_interactive_agent import HumanInteractiveAgent


def test_human_prompt_filters_internal_schema_noise() -> None:
    agent = HumanInteractiveAgent(name="玩家1", model="human")
    prompt = "\n".join([
        "你是Seer。",
        "任务：请投票选择你想淘汰的玩家",
        "【本阶段输出】仅 SeatChoiceDecision：seat=整数全局座位号；reason 必填。",
        "- public_speech (string, 必填): 完整中文公开发言。",
        "- private_thought (string, 可选): 仅自己可见。",
        "可选目标：",
        "- 座位 2：玩家2（ID: player_2）",
    ])

    rendered = agent._render_prompt(prompt)

    assert "请投票选择你想淘汰的玩家" in rendered
    assert "可选目标" in rendered
    assert "SeatChoiceDecision" not in rendered
    assert "public_speech" not in rendered
    assert "private_thought" not in rendered


def test_human_prompt_classifies_wolf_discussion_as_speech() -> None:
    agent = HumanInteractiveAgent(name="玩家1", model="human")
    prompt = "\n".join([
        "你是 玩家1，身份为狼人。",
        "可选目标：机器人2, 机器人3, 机器人4。",
        "与狼队友讨论今晚要淘汰谁，简要说明理由（1-2 句）。",
        "【子阶段·仅发言】",
    ])

    kind, _, _ = agent._classify(prompt)

    assert kind == "speech"
