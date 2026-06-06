"""兜底决策日志标记。"""

from llm_werewolf.game_runtime.support.fallback_log import (
    annotate_log_message,
    fallback_prefix_from_data,
    format_fallback_tag,
    mark_agent_fallback,
    merge_agent_decision_into_event_data,
)


class _FakeAgent:
    pass


def test_format_fallback_tag_includes_reason() -> None:
    assert format_fallback_tag(reason="parse_failed", kind="vote") == "⚠️[兜底:parse_failed]"


def test_mark_agent_fallback_sets_metadata() -> None:
    agent = _FakeAgent()
    mark_agent_fallback(agent, kind="speech", reason="interrupted")
    meta = agent._last_decision_metadata
    assert meta["fallback"] is True
    assert meta["decision_kind"] == "speech"
    assert meta["fallback_reason"] == "interrupted"


def test_annotate_log_message_prefixes_fallback_vote() -> None:
    message, data = annotate_log_message(
        "🗳️ Alice 投票给 Bob",
        {
            "decision": {
                "fallback": True,
                "fallback_reason": "vote_intention",
                "decision_kind": "vote",
            }
        },
    )
    assert "⚠️[兜底:vote_intention]" in message
    assert data["fallback"] is True


def test_merge_agent_decision_into_event_data() -> None:
    agent = _FakeAgent()
    mark_agent_fallback(agent, kind="speech", reason="speech_fallback")
    data = merge_agent_decision_into_event_data(
        {"player_name": "P1", "speech": "hello"},
        agent,
    )
    assert data["decision"]["fallback"] is True
    assert fallback_prefix_from_data(data).startswith("⚠️[兜底:")
