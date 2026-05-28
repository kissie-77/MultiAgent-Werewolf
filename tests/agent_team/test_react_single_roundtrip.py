"""结构化决策必须只花一次模型往返（性能报告 ③：消除无用的第二次 round-trip）。

agentscope ReActAgent 在结构化决策时，若模型同一条消息只吐 tool_use、不吐 text，
就会再打一次纯文本 _reasoning（第二次 HTTP），而游戏只读 metadata。本测试通过真实
factory 构建 agent 并注入一个计数假模型，断言"只吐工具调用、不吐文本"时仅一次模型调用。
"""

from __future__ import annotations

import os
from typing import Any

from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg
from agentscope.model import ChatResponse

from llm_werewolf.agent_team.factory import create_react_agent
from llm_werewolf.game_runtime.config import PlayerConfig
from llm_werewolf.strategy.decisions import SeatChoiceDecision


class CountingFakeModel:
    """计数假模型，复刻 agentscope ChatModelBase 的非流式契约。

    reply()/_reasoning 在 stream=False 下只读取 ``res.id`` 与 ``res.content``，
    并检查 ``self.model.stream``，故此处暴露 ``stream = False`` 即可。
    """

    def __init__(self, responses: list[list[dict[str, Any]]]) -> None:
        self.stream = False
        self.n_calls = 0
        self._responses = responses

    async def __call__(self, *_args: Any, **_kwargs: Any) -> ChatResponse:
        idx = min(self.n_calls, len(self._responses) - 1)
        self.n_calls += 1
        return ChatResponse(content=list(self._responses[idx]), id=f"resp-{idx}")


def _make_agent():
    os.environ.setdefault("WW_TEST_KEY", "test-key")
    config = PlayerConfig(
        name="P1",
        model="fake-model",
        base_url="http://localhost:1",
        api_key_env="WW_TEST_KEY",
    )
    return create_react_agent(config, agent_name="P1", sys_prompt="You are a player.")


async def test_tool_call_without_text_makes_single_round_trip():
    """只吐 generate_response 工具调用、不吐文本时，应只发生 1 次模型调用。"""
    agent = _make_agent()
    tool_only = [
        {
            "type": "tool_use",
            "id": "call_1",
            "name": "generate_response",
            "input": {"seat": 4},
        },
    ]
    # 第二条罐装响应模拟 doubao 当前被浪费的"纯文本"第二次往返——修复后不应被触发。
    wasted_text = [{"type": "text", "text": "我选择 4 号玩家。"}]
    agent.model = CountingFakeModel([tool_only, wasted_text])

    result = await agent(
        Msg(name="Moderator", content="选择一个座位", role="user"),
        structured_model=SeatChoiceDecision,
    )

    assert agent.model.n_calls == 1
    assert result.metadata is not None
    assert result.metadata.get("seat") == 4


async def test_tool_call_with_text_is_unchanged_single_round_trip():
    """模型同一步同时吐 tool_use + text 时，基类本就单次往返——修复不得破坏该路径。"""
    agent = _make_agent()
    tool_and_text = [
        {
            "type": "tool_use",
            "id": "call_1",
            "name": "generate_response",
            "input": {"seat": 7},
        },
        {"type": "text", "text": "我建议出 7 号。"},
    ]
    agent.model = CountingFakeModel([tool_and_text, [{"type": "text", "text": "未使用"}]])

    result = await agent(
        Msg(name="Moderator", content="选择一个座位", role="user"),
        structured_model=SeatChoiceDecision,
    )

    assert agent.model.n_calls == 1
    assert result.metadata.get("seat") == 7


async def test_post_decision_memory_is_well_formed_for_next_call():
    """补的空 TextBlock 不得产生畸形 prompt：tool_call 仍被 tool_result 应答。

    关闭对抗校验提出的残留疑点（formatter 是否容忍"工具调用轮无尾随 assistant 文本"）。
    """
    agent = _make_agent()
    tool_only = [
        {
            "type": "tool_use",
            "id": "call_1",
            "name": "generate_response",
            "input": {"seat": 4},
        },
    ]
    agent.model = CountingFakeModel([tool_only])

    await agent(
        Msg(name="Moderator", content="选择一个座位", role="user"),
        structured_model=SeatChoiceDecision,
    )

    history = await agent.memory.get_memory()
    formatted = await OpenAIChatFormatter().format(
        msgs=[Msg(name="system", content="sys", role="system"), *history],
    )
    assistant_tool_msgs = [
        m for m in formatted if m.get("role") == "assistant" and m.get("tool_calls")
    ]
    assert len(assistant_tool_msgs) == 1
    # 关键不变式：每个 tool_call 都必须被 tool_result 应答，否则下一轮 prompt 非法。
    call_ids = {tc["id"] for m in assistant_tool_msgs for tc in m["tool_calls"]}
    answered = {m.get("tool_call_id") for m in formatted if m.get("role") == "tool"}
    assert call_ids and call_ids <= answered
    # 记忆与基类首轮一致：补的空 TextBlock 只作用于返回消息以触发 break，不写入 memory；
    # 且末尾不残留任何"纯文本 assistant 轮"（即被消除的第二次往返产物）。
    trailing_text_turns = [
        m
        for m in formatted
        if m.get("role") == "assistant" and not m.get("tool_calls") and m.get("content")
    ]
    assert trailing_text_turns == []
