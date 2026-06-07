"""HumanInteractiveAgent prompt rendering tests."""

import pytest

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


def test_human_prompt_keeps_player_facts_but_hides_strategy_noise() -> None:
    agent = HumanInteractiveAgent(name="玩家6", model="human")
    prompt = "\n".join([
        "你是 玩家6。",
        "当前阶段：day_discussion",
        "私密信息：",
        "- 你的身份是 Villager。",
        "- 【身份提示】",
        "身份：平民（Villager）",
        "阵营：好人阵营",
        "策略建议：记录发言逻辑，避免跟风投票。",
        "",
        "【当前信念矩阵 · 仅自己可见】",
        "一阶（狼概率，高→低）: 1→0.33, 5→0.33",
        "请结合公开信息与上述信念做出发言或投票决策。",
        "",
        "【本轮已听到的发言】",
        "- 玩家1: 我先观察。",
        "【对话记忆 · MsgHub】",
        "本轮已在对话中出现的公开发言由系统注入你的历史。",
        "【子阶段·仅发言】",
        "【任务】白天公开讨论轮。分析局势、回应前置发言、表明站队。",
    ])

    rendered = agent._render_prompt(prompt)

    assert "你的身份是 Villager" in rendered
    assert "【本轮已听到的发言】" in rendered
    assert "玩家1: 我先观察" in rendered
    assert "身份：平民" not in rendered
    assert "策略建议" not in rendered
    assert "当前信念矩阵" not in rendered
    assert "MsgHub" not in rendered


def test_human_prompt_hides_internal_memory_and_wolf_panel() -> None:
    agent = HumanInteractiveAgent(name="玩家1", model="human")
    prompt = "\n".join([
        "你是 玩家1。",
        "当前阶段：day_discussion",
        "私密信息：",
        "- 你的身份是 Villager。",
        "【内心信念】",
        "- 【信念/意向更新规则】",
        "- first_order / second_order 仅填写需要修改的条目；无变化则留空数组 []。",
        "- 【当前信念矩阵 · 仅自己可见】",
        "- 一阶（狼概率，高→低）: 2→0.80, 3→0.50",
        "- 【狼队共享战术面板 · revision 1 · 仅狼队可见】",
        "- ■ 神职定位",
        "【本轮记忆】",
        "- 🐺 玩家2(狼人): 今晚刀4号",
        "- Round 1 (wolf_team): You said: 先刀4号",
        "【本轮已听到的发言】",
        "- 玩家3: 我今天先听后置位。",
        "【任务】白天公开讨论轮。",
    ])

    rendered = agent._render_prompt(prompt)

    assert "你的身份是 Villager" in rendered
    assert "玩家3: 我今天先听后置位" in rendered
    assert "内心信念" not in rendered
    assert "当前信念矩阵" not in rendered
    assert "狼队共享战术面板" not in rendered
    assert "今晚刀4号" not in rendered
    assert "wolf_team" not in rendered


def test_human_prompt_hides_public_speech_boundary_block() -> None:
    agent = HumanInteractiveAgent(name="玩家1", model="human")
    prompt = "\n".join([
        "你是 玩家1。",
        "【本局角色池】",
        "本局实际存在的身份类型：Villager x2, Werewolf x2, Witch x1, Seer x1。",
        "【公开发言信息边界】",
        "白天发言只能明说公开可见事实。",
        "public_speech 不要无意识泄露夜间技能结果。",
        "【任务】白天公开讨论轮。",
    ])

    rendered = agent._render_prompt(prompt)

    assert "本局角色池" in rendered
    assert "公开发言信息边界" not in rendered
    assert "不要无意识泄露" not in rendered
    assert "【任务】白天公开讨论轮。" in rendered


def test_prepare_web_prompt_returns_ui_metadata() -> None:
    msg = "\n".join([
        "你是 1 号女巫。",
        "请只回复目标玩家的全局座位号",
        "可选目标:\n- 座位 2\n- 座位 3",
    ])
    ui = HumanInteractiveAgent.prepare_web_prompt(msg)
    assert ui["kind"] == "seat"
    assert ui["title"] == "选择目标"
    assert "Schema" not in str(ui["prompt"])
    assert ui["ui_hint"]
    assert ui["allow_skip"] is False


def test_human_speech_prompt_is_minimal_even_with_roundtable_context() -> None:
    agent = HumanInteractiveAgent(name="玩家2", model="human")
    prompt = "\n".join([
        "- 你的身份是 Villager。",
        "【本轮已听到的发言】",
        "- 玩家1: 我想听大家聊聊平安夜。",
        "请先回应上一位发言者的具体建议。",
        "【子阶段·仅发言】",
        "【任务】白天公开讨论轮。分析局势、回应前置发言、表明站队。",
    ])

    rendered = agent._render_prompt(prompt, kind="speech")

    assert rendered == "请进行白天公开发言。"
    assert "本轮已听到的发言" not in rendered
    assert "子阶段" not in rendered
    assert "任务" not in rendered


def test_human_seat_prompt_is_minimal_for_action_input() -> None:
    agent = HumanInteractiveAgent(name="玩家1", model="human")
    prompt = "\n".join([
        "你是Villager。",
        "当前：第 1 轮 — Voting",
        "任务：请投票选择你想淘汰的玩家",
        "",
        "你是 玩家1。",
        "当前阶段：day_voting",
        "存活概况：5/6 人存活",
        "场上玩家：",
        "- 玩家1（player_1）：存活",
        "可见事件记录：",
        "- 玩家4 被狼人杀害",
        "私密信息：",
        "- 你的身份是 Villager。",
        "可选目标：",
        "- 座位 2：玩家2（ID: player_2）",
        "- 座位 0：跳过（不执行此行动）",
        "",
        "预言家请睁眼，选择你要验的玩家编号，回答编号，放在[[]]里",
        "请只回复目标玩家的全局座位号，放在 [[数字]] 中。",
    ])

    rendered = agent._render_prompt(prompt, kind="seat")

    assert "你是Villager" in rendered
    assert "当前：第 1 轮 — Voting" in rendered
    assert "请投票选择你想淘汰的玩家" in rendered
    assert "座位 2" in rendered
    assert "座位 0" in rendered
    assert "场上玩家" not in rendered
    assert "可见事件记录" not in rendered
    assert "私密信息" not in rendered
    assert "预言家请睁眼" not in rendered


def test_human_yesno_prompt_is_minimal_for_action_input() -> None:
    agent = HumanInteractiveAgent(name="玩家1", model="human")
    prompt = "\n".join([
        "你是Villager。",
        "当前：第 1 轮 — sheriff_election",
        "问题：你是否愿意竞选警长？",
        "",
        "你是 玩家1。",
        "当前阶段：sheriff_election",
        "可见事件记录：",
        "- 玩家4 被狼人杀害",
        "私密信息：",
        "- 你的身份是 Villager。",
        "请只回复 [[1]] 表示是，[[0]] 表示否。不要输出其他文字。",
    ])

    rendered = agent._render_prompt(prompt, kind="yesno")

    assert "你是Villager" in rendered
    assert "你是否愿意竞选警长" in rendered
    assert "可见事件记录" not in rendered
    assert "私密信息" not in rendered
    assert "玩家4 被狼人杀害" not in rendered


def test_human_witch_prompt_keeps_only_action_facts() -> None:
    agent = HumanInteractiveAgent(name="玩家2", model="human")
    prompt = "\n".join([
        "你是Witch。",
        "女巫请睁眼。",
        "当前：第 1 轮 — Night",
        "今晚被狼人击杀的是 5 号玩家5。",
        "你是 玩家2。",
        "当前阶段：night",
        "可见事件记录：",
        "- 狼人选择了 玩家5",
        "若选择 poison，可选毒杀目标：",
        "- 座位 3：玩家3（ID: player_3）",
        "请在本回合三选一：救人(save) / 毒人(poison) / 不行动(none)。",
    ])

    rendered = agent._render_prompt(prompt, kind="witch")

    assert "你是Witch" in rendered
    assert "女巫请睁眼" in rendered
    assert "今晚被狼人击杀的是 5 号" in rendered
    assert "座位 3" in rendered
    assert "三选一" in rendered
    assert "可见事件记录" not in rendered


def test_human_witch_prompt_with_used_antidote_keeps_victim_but_no_save() -> None:
    agent = HumanInteractiveAgent(name="玩家3", model="human")
    prompt = "\n".join([
        "你是Witch。",
        "女巫请睁眼。",
        "当前：第 2 轮 — Night",
        "今晚狼人刀口：玩家2（2号）。你的解药已用完，不能救；你仍可选择是否使用毒药。",
        "若选择 poison，可选毒杀目标：",
        "- 座位 1：玩家1（ID: player_1）",
        "请在本回合二选一：毒人(poison) / 不行动(none)。",
        "解药不可用或没有可救刀口，不能选择 save；毒人需指定 seat。",
    ])

    rendered = agent._render_prompt(prompt, kind="witch")
    kind, _, _ = agent._classify(prompt)

    assert kind == "witch"
    assert "今晚狼人刀口：玩家2" in rendered
    assert "解药已用完，不能救" in rendered
    assert "二选一" in rendered
    assert "救人(save)" not in rendered
    assert not agent._witch_save_allowed(prompt)


def test_human_witch_save_is_rejected_when_antidote_unavailable() -> None:
    normalized, error = HumanInteractiveAgent._normalize(
        "witch",
        0,
        False,
        "救",
        allow_witch_save=False,
    )

    assert normalized is None
    assert "不能救人" in error


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


def test_human_speech_rejects_repeated_placeholder_text() -> None:
    normalized, error = HumanInteractiveAgent._normalize(
        "speech",
        0,
        False,
        "eeeeeeeeeeeeeeeeeeeeeeeeeeee",
    )

    assert normalized is None
    assert "不能是重复字符" in error


def test_human_speech_accepts_meaningful_chinese_text() -> None:
    text = "我认为三号刚才带节奏太明显，今天应该优先听他解释。"

    normalized, error = HumanInteractiveAgent._normalize("speech", 0, False, text)

    assert normalized == text
    assert error == ""


def test_human_submission_confirmation_is_immediate_and_plain() -> None:
    assert HumanInteractiveAgent._confirmation("speech", "我先听完大家发言再判断。").startswith("已提交发言")
    assert HumanInteractiveAgent._confirmation("seat", "3") == "已提交目标：座位 3"
    assert HumanInteractiveAgent._confirmation(
        "seat", "3", is_werewolf_kill=True
    ) == "已提交你的狼刀票：座位 3；最终刀口以狼队结算为准"


def test_human_seat_input_must_be_in_options() -> None:
    normalized, error = HumanInteractiveAgent._normalize(
        "seat",
        0,
        True,
        "2",
        option_seats={0, 1, 5},
    )

    assert normalized is None
    assert "不在可选目标中" in error


def test_human_invalid_fallbacks_do_not_return_raw_input() -> None:
    assert "?" not in HumanInteractiveAgent._fallback_after_invalid("speech", False)
    assert "弃发言" in HumanInteractiveAgent._fallback_after_invalid("speech", False)
    assert HumanInteractiveAgent._fallback_after_invalid("yesno", False) == "0"
    assert HumanInteractiveAgent._fallback_after_invalid("witch", False) == "none"
    assert HumanInteractiveAgent._fallback_after_invalid("seat", True) == "0"
    assert HumanInteractiveAgent._fallback_after_invalid("seat", False) == ""


@pytest.mark.asyncio
async def test_human_get_response_uses_safe_fallback_after_invalid_speech(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = HumanInteractiveAgent(name="玩家1", model="human")
    inputs = iter(["?", "??", "???"])

    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    response = await agent.get_response("【子阶段·仅发言】\n【任务】白天公开讨论轮。")

    assert "弃发言" in response
    assert "?" not in response


@pytest.mark.asyncio
async def test_human_get_response_prints_waiting_hint_after_valid_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = HumanInteractiveAgent(name="玩家1", model="human")
    rendered: list[str] = []

    monkeypatch.setattr("builtins.input", lambda _prompt="": "3")
    monkeypatch.setattr(
        "llm_werewolf.agent_team.agents.human_interactive_agent.console.print",
        lambda message="", *args, **kwargs: rendered.append(str(message)),
    )

    response = await agent.get_response(
        "\n".join([
            "你是Villager。",
            "任务：请投票选择你想淘汰的玩家",
            "可选目标：",
            "- 座位 3：玩家3（ID: player_3）",
            "- 座位 0：跳过（不执行此行动）",
        ])
    )

    assert response == "3"
    assert any("等待其他玩家决策" in line for line in rendered)
