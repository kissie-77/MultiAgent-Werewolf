"""generate_response 元数据解包与结构化检测的测试。"""

import pytest

from llm_werewolf.strategy.decisions import SeatChoiceDecision, WitchNightDecision
from llm_werewolf.agent_team.structured_invoke import (
    invoke_structured,
    parse_structured_from_text,
    unwrap_structured_metadata,
    agent_uses_structured_output,
)


def test_unwrap_flat_metadata() -> None:
    meta = {"seat": 3, "reason": "可疑"}
    assert unwrap_structured_metadata(meta) == meta


def test_unwrap_nested_structured_output() -> None:
    meta = {"success": True, "structured_output": {"seat": 5}}
    assert unwrap_structured_metadata(meta) == {"seat": 5}


def test_agent_uses_structured_when_agentscope_present() -> None:
    class FakeAgent:
        agentscope_agent = object()

    assert agent_uses_structured_output(FakeAgent()) is True


def test_agent_uses_structured_flag_without_backend() -> None:
    class FlagAgent:
        uses_structured_output = True

    assert agent_uses_structured_output(FlagAgent()) is False


def test_seat_choice_schema_fields() -> None:
    d = SeatChoiceDecision(seat=2, reason="验人")
    assert d.seat == 2


def test_parse_structured_from_text_recovers_deepseek_content_json() -> None:
    text = """
W(thinking): 我决定首夜救刀口3号，毒药先留着。
W: {"action": "save", "seat": 0, "reason": "首夜信息少，先救刀口。"}
"""

    decision = parse_structured_from_text(text, WitchNightDecision)

    assert decision is not None
    assert decision.action == "save"
    assert decision.seat == 0


def test_parse_structured_from_text_unwraps_tool_call_arguments() -> None:
    text = (
        'final: {"name": "generate_response", '
        '"arguments": {"seat": 4, "reason": "首夜查验中置位。"}}'
    )

    decision = parse_structured_from_text(text, SeatChoiceDecision)

    assert decision is not None
    assert decision.seat == 4


def test_parse_structured_from_text_recovers_seat_only_choice() -> None:
    decision = parse_structured_from_text("[[5]]", SeatChoiceDecision)

    assert decision is not None
    assert decision.seat == 5


def test_parse_structured_from_text_does_not_treat_seat_as_witch_action() -> None:
    decision = parse_structured_from_text("[[5]]", WitchNightDecision)

    assert decision is None


@pytest.mark.asyncio
async def test_invoke_structured_appends_schema_specific_instruction() -> None:
    class CapturingAgent:
        name = "P1"
        seen_message = ""

        async def get_structured_response(self, message, model) -> None:
            self.seen_message = message

    agent = CapturingAgent()

    await invoke_structured(agent, "请选择夜晚目标", SeatChoiceDecision, retries=1)

    assert "SeatChoiceDecision Schema" in agent.seen_message
    assert "SpeechDecision Schema" not in agent.seen_message
    assert "public_speech / private_thought" not in agent.seen_message
