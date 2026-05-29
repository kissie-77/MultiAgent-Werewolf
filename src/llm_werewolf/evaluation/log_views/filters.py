"""日志视图过滤：visible_to、截断、剔除 thinking 噪声。"""

from __future__ import annotations

import re
from typing import Any

_THINKING_BLOCK_RE = re.compile(
    r"(?is)(?:^|\n)\s*(?:thinking|thought|思考过程)\s*[:：]\s*\n.*?(?=\n\s*(?:public_speech|发言|##|\Z))",
    re.MULTILINE,
)
_JSON_THINKING_RE = re.compile(r'"thinking"\s*:\s*"[^"]*"', re.IGNORECASE)


def event_is_visible_to(event: dict[str, Any], player_id: str) -> bool:
    """Dict 形式 event 的 visible_to 判定（与 Event.is_visible_to 一致）。"""
    visible_to = event.get("visible_to")
    if visible_to is None:
        return True
    if not isinstance(visible_to, list):
        return True
    return player_id in visible_to


def filter_events_for_player(
    events: list[dict[str, Any]], player_id: str, *, since_round: int | None = None
) -> list[dict[str, Any]]:
    filtered = [e for e in events if event_is_visible_to(e, player_id)]
    if since_round is not None:
        filtered = [e for e in filtered if int(e.get("round_number", 0)) >= since_round]
    return filtered


def strip_thinking(text: str) -> str:
    if not text:
        return text
    cleaned = _THINKING_BLOCK_RE.sub("", text)
    cleaned = _JSON_THINKING_RE.sub("", cleaned)
    return cleaned.strip()


def truncate_text(text: str, max_len: int = 500) -> str:
    text = strip_thinking(text)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def sanitize_event_message(event: dict[str, Any], *, max_len: int = 500) -> str:
    return truncate_text(str(event.get("message", "")), max_len=max_len)


def event_line(event: dict[str, Any], *, max_len: int = 500) -> str:
    etype = event.get("event_type", "?")
    rnd = event.get("round_number", 0)
    phase = event.get("phase", "?")
    msg = sanitize_event_message(event, max_len=max_len)
    return f"[R{rnd}/{phase}] {etype}: {msg}"


def estimate_tokens(text: str) -> int:
    """粗算 token（中文按字符、英文按词）。"""
    if not text:
        return 0
    return max(1, len(text) // 2)
