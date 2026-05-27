"""generate_response 元数据解包与结构化检测的测试。"""

from llm_werewolf.agent_team.invocation.structured_invoke import (
    agent_uses_structured_output,
    unwrap_structured_metadata,
)
from llm_werewolf.strategy.decisions import SeatChoiceDecision


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
