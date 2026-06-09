"""通过 generate_response → Msg.metadata 的统一 AgentScope 结构化输出。"""

from __future__ import annotations

import re
import json
from typing import Any, TypeVar
import logging

from pydantic import BaseModel, ValidationError

from llm_werewolf.strategy.contracts.decisions import (
    SpeechDecision,
    normalize_speech_decision,
    generate_response_instruction,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def agent_uses_structured_output(agent: Any) -> bool:
    """仅当已挂载可用的 AgentScope ReAct 后端时返回 True。"""
    return getattr(agent, "agentscope_agent", None) is not None


def unwrap_structured_metadata(metadata: Any) -> dict[str, Any] | None:
    """将 ReActAgent 的 Msg.metadata 规范为供 Pydantic 使用的扁平 dict。"""
    if metadata is None:
        return None
    if not isinstance(metadata, dict):
        return None
    # AgentScope 中断标记不是有效结构化输出
    if metadata.get("_is_interrupted"):
        return None
    nested = metadata.get("structured_output")
    if isinstance(nested, dict) and nested:
        return nested
    if metadata.get("success") is False:
        return None
    # 最终回复直接存字段（seat、choice、public_speech 等）
    if any(key in metadata for key in ("seat", "choice", "public_speech", "seats", "beliefs", "first_order")):
        return metadata
    return metadata if metadata else None


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def _iter_balanced_json_objects(text: str) -> list[str]:
    """提取文本中的平衡 JSON 对象，保留字符串内部花括号。"""
    objects: list[str] = []
    start: int | None = None
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                objects.append(text[start : index + 1])
                start = None
    return objects


def _unwrap_tool_payload(data: dict[str, Any]) -> dict[str, Any]:
    """兼容模型把 generate_response 工具调用包装进 content JSON 的形态。"""
    for key in ("generate_response", "structured_output", "input", "arguments", "kwargs"):
        value = data.get(key)
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                return decoded
    return data


def _parse_legacy_scalar_text(text: str, model: type[T]) -> T | None:
    """兼容旧提示下模型返回 [[seat]] / YES / NO 的非发言决策。"""
    stripped = text.strip()
    seat_match = re.fullmatch(r"(?:\[\[\s*)?(\d+)(?:\s*\]\])?", stripped)
    if seat_match and model.__name__ in {"SeatChoiceDecision", "VoteIntentionDecision", "MindStateDecision"}:
        return model.model_validate({"seat": int(seat_match.group(1)), "reason": None})

    if model.__name__ == "YesNoDecision":
        upper = stripped.upper()
        if upper in {"YES", "NO"}:
            return model.model_validate({"choice": upper == "YES", "reason": None})
        if seat_match and seat_match.group(1) in {"0", "1"}:
            return model.model_validate({"choice": seat_match.group(1) == "1", "reason": None})

    # ── 中文文本兜底：从自然语言中提取座位号 ──
    if model.__name__ in {"SeatChoiceDecision", "VoteIntentionDecision", "MindStateDecision"}:
        cn_seat = re.search(r"(\d+)\s*号", stripped)
        if cn_seat:
            return model.model_validate({"seat": int(cn_seat.group(1)), "reason": None})

    if model.__name__ == "YesNoDecision":
        if re.search(r"\b是\b|\b同意\b|好", stripped):
            return model.model_validate({"choice": True, "reason": None})
        if re.search(r"\b不\b|\b否\b|\b拒绝\b|\b不要\b", stripped):
            return model.model_validate({"choice": False, "reason": None})

    return None


def _parse_yaml_like_lines(text: str, model: type[T]) -> T | None:
    """当模型以 `key: value` 形式而非完整 JSON 输出时的兜底解析。"""
    pairs: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^\s*(\w+)\s*:\s*(.+)\s*$", line)
        if m:
            key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
            if val.lower() in {"true", "false"}:
                pairs[key] = val.lower() == "true"
            elif val.isdigit():
                pairs[key] = int(val)
            elif val == "null" or val == "none":
                pairs[key] = None
            else:
                pairs[key] = val
    if pairs:
        try:
            # 优先严格校验，失败则用 model_construct 宽松兜底
            return model.model_validate(pairs)
        except ValidationError:
            try:
                return model.model_construct(**pairs)
            except (ValidationError, TypeError):
                pass
    return None


def parse_structured_from_text(text: str, model: type[T]) -> T | None:
    """从模型纯文本 content 中恢复结构化决策。"""
    if not text or not text.strip():
        return None

    legacy = _parse_legacy_scalar_text(text, model)
    if legacy is not None:
        return legacy

    candidates = [_strip_json_fence(text)]
    candidates.extend(_iter_balanced_json_objects(text))
    parsed: T | None = None
    for candidate in candidates:
        try:
            data = json.loads(_strip_json_fence(candidate))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        data = _unwrap_tool_payload(data)
        try:
            parsed = model.model_validate(data)
        except ValidationError:
            continue
    if parsed is not None:
        return parsed

    # ── 最终兜底：YAML 风格 key:value 行解析 ──
    return _parse_yaml_like_lines(text, model)


async def invoke_structured(
    agent: Any, prompt: str, model: type[T], *, retries: int = 2
) -> T | None:
    """调用 agent.get_structured_response；prompt 须要求 generate_response JSON。"""
    getter = getattr(agent, "get_structured_response", None)
    if not callable(getter):
        return None

    full_prompt = prompt
    if "generate_response" not in prompt:
        allow_legacy = model.__name__ != "SpeechDecision"
        full_prompt = f"{prompt}\n\n{generate_response_instruction(model.__name__, allow_legacy_scalar=allow_legacy)}"

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
    else:
        logger.debug(
            "structured_invoke_returned_none agent=%s model=%s attempts=%s",
            getattr(agent, "name", "?"),
            model.__name__,
            retries,
        )
    return None


def coerce_speech(decision: SpeechDecision | None) -> SpeechDecision:
    if decision is None:
        return SpeechDecision.model_construct(public_speech="（无公开发言）", private_thought=None)
    return normalize_speech_decision(decision)
