"""Compatibility exports for AgentScope structured invocation helpers."""

from llm_werewolf.agent_team.structured_invoke import (
    agent_uses_structured_output,
    coerce_speech,
    invoke_structured,
    unwrap_structured_metadata,
)

__all__ = [
    "agent_uses_structured_output",
    "coerce_speech",
    "invoke_structured",
    "unwrap_structured_metadata",
]
