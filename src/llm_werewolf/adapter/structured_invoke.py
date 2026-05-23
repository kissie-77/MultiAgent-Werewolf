"""Unified AgentScope structured output via generate_response → Msg.metadata."""

from __future__ import annotations

import logging
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

from llm_werewolf.core.decisions import (
    GENERATE_RESPONSE_INSTRUCTION,
    SeatChoiceDecision,
    SpeechDecision,
    YesNoDecision,
    normalize_speech_decision,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def agent_uses_structured_output(agent: Any) -> bool:
    """Whether bridge uses ReAct schemas vs kissie-77 ``[[ ]]`` / ``{{}}`` text prompts."""
    return False


def unwrap_structured_metadata(metadata: Any) -> dict[str, Any] | None:
    """Normalize Msg.metadata from ReActAgent into a flat dict for Pydantic."""
    if metadata is None:
        return None
    if not isinstance(metadata, dict):
        return None
    nested = metadata.get("structured_output")
    if isinstance(nested, dict) and nested:
        return nested
    if metadata.get("success") is False:
        return None
    # Final reply stores fields directly (seat, choice, public_speech, ...)
    if any(
        key in metadata
        for key in ("seat", "choice", "public_speech", "seats", "beliefs")
    ):
        return metadata
    return metadata if metadata else None


async def invoke_structured(
    agent: Any,
    prompt: str,
    model: Type[T],
    *,
    retries: int = 2,
) -> T | None:
    """Call agent.get_structured_response; prompt must ask for generate_response JSON."""
    getter = getattr(agent, "get_structured_response", None)
    if not callable(getter):
        return None

    full_prompt = prompt
    if GENERATE_RESPONSE_INSTRUCTION not in prompt:
        full_prompt = f"{prompt}\n\n{GENERATE_RESPONSE_INSTRUCTION}"

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            raw = await getter(full_prompt, model)
            if raw is None:
                continue
            if isinstance(raw, model):
                return raw
            if isinstance(raw, BaseModel):
                return model.model_validate(raw.model_dump())
            if isinstance(raw, dict):
                return model.model_validate(raw)
        except ValidationError as exc:
            last_error = exc
            logger.warning(
                "structured_validate_failed agent=%s model=%s attempt=%s err=%s",
                getattr(agent, "name", "?"),
                model.__name__,
                attempt + 1,
                exc,
            )
        except Exception as exc:
            last_error = exc
            logger.warning(
                "structured_invoke_failed agent=%s model=%s attempt=%s err=%s",
                getattr(agent, "name", "?"),
                model.__name__,
                attempt + 1,
                exc,
            )

    if last_error is not None:
        logger.warning(
            "structured_invoke_gave_up agent=%s model=%s err=%s",
            getattr(agent, "name", "?"),
            model.__name__,
            last_error,
        )
    return None


def coerce_speech(decision: SpeechDecision | None) -> SpeechDecision:
    if decision is None:
        return SpeechDecision.model_construct(
            public_speech="（无公开发言）",
            private_thought=None,
        )
    return normalize_speech_decision(decision)
