"""对局日志中的兜底决策标记（发言 / 投票 / 技能）。"""

from __future__ import annotations

from typing import Any


def format_fallback_tag(*, reason: str | None = None, kind: str | None = None) -> str:
    label = (reason or kind or "unknown").strip() or "unknown"
    return f"⚠️[兜底:{label}]"


def infer_decision_kind_from_prompt(message: str) -> str:
    lowered = message.lower()
    if "发言" in message or "speech" in lowered or "演说" in message or "roundtable" in lowered:
        return "speech"
    if "vote" in lowered or "投票" in message or "vote_intention" in lowered:
        return "vote"
    if "yes" in lowered or "no" in lowered or "是否" in message:
        return "yesno"
    if "only the number" in lowered or "座位" in message or "[[0]]" in message or "弃票" in message:
        return "seat"
    return "skill"


def mark_agent_fallback(agent: Any, *, kind: str, reason: str) -> None:
    if agent is None:
        return
    object.__setattr__(
        agent,
        "_last_decision_metadata",
        {
            "fallback": True,
            "fallback_reason": reason,
            "decision_kind": kind,
        },
    )


def clear_agent_decision_metadata(agent: Any) -> None:
    if agent is None:
        return
    object.__setattr__(agent, "_last_decision_metadata", None)


def merge_agent_decision_into_event_data(data: dict[str, Any], agent: Any) -> dict[str, Any]:
    meta = getattr(agent, "_last_decision_metadata", None)
    if isinstance(meta, dict) and meta:
        return {**data, "decision": dict(meta)}
    return data


def fallback_prefix_from_data(data: dict[str, Any] | None) -> str:
    if not data:
        return ""
    decision = data.get("decision")
    is_fallback = bool(data.get("fallback"))
    if isinstance(decision, dict):
        is_fallback = is_fallback or bool(decision.get("fallback"))
    if not is_fallback:
        return ""
    reason = data.get("fallback_reason")
    kind = data.get("decision_kind")
    if isinstance(decision, dict):
        reason = reason or decision.get("fallback_reason")
        kind = kind or decision.get("decision_kind")
    return format_fallback_tag(
        reason=str(reason) if reason else None,
        kind=str(kind) if kind else None,
    ) + " "


def annotate_log_message(message: str, data: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    """若 data 含 fallback 决策，在 message 前加可见标记并规范化 data。"""
    payload = dict(data or {})
    decision = payload.get("decision")
    is_fallback = bool(payload.get("fallback"))
    if isinstance(decision, dict):
        is_fallback = is_fallback or bool(decision.get("fallback"))

    if not is_fallback:
        return message, payload

    reason = payload.get("fallback_reason")
    kind = payload.get("decision_kind")
    if isinstance(decision, dict):
        reason = reason or decision.get("fallback_reason")
        kind = kind or decision.get("decision_kind")

    tag = format_fallback_tag(reason=str(reason) if reason else None, kind=str(kind) if kind else None)
    payload["fallback"] = True
    if reason:
        payload["fallback_reason"] = reason
    if kind:
        payload["decision_kind"] = kind

    if tag in message:
        return message, payload
    return f"{tag} {message}", payload
