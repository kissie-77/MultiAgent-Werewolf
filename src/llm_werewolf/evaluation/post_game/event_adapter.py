"""PostGame 与 game_runtime 事件模型之间的适配（events.jsonl ↔ Event / EventLogger）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from llm_werewolf.game_runtime.events.events import EventLogger
from llm_werewolf.game_runtime.types import Event
from llm_werewolf.game_runtime.types.enums import EventType, GamePhase


def event_from_dict(raw: dict[str, Any]) -> Event | None:
    """将 events.jsonl 单行 dict 转为 Event；无法解析时返回 None。"""
    try:
        phase_raw = str(raw.get("phase", "setup"))
        timestamp_raw = raw.get("timestamp")
        if isinstance(timestamp_raw, str) and timestamp_raw:
            timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now()
        return Event(
            event_type=EventType(str(raw["event_type"])),
            timestamp=timestamp,
            message=str(raw.get("message", "")),
            round_number=int(raw.get("round_number", 0)),
            phase=GamePhase(phase_raw),
            data=dict(raw.get("data") or {}),
            visible_to=raw.get("visible_to"),
        )
    except (ValueError, KeyError, TypeError):
        return None


def events_from_dicts(rows: list[dict[str, Any]]) -> list[Event]:
    """批量解析事件，跳过无效行。"""
    events: list[Event] = []
    for raw in rows:
        event = event_from_dict(raw)
        if event is not None:
            events.append(event)
    return events


def event_logger_from_dicts(rows: list[dict[str, Any]]) -> EventLogger:
    """从 PostGame 只读事件列表构建 EventLogger（供 EpisodicMemory 复用）。"""
    logger = EventLogger()
    for event in events_from_dicts(rows):
        logger.log_event(event)
    return logger


def event_logger_from_engine(engine: Any) -> EventLogger | None:
    """对局进行中：直接复用引擎上的 EventLogger。"""
    if engine is None:
        return None
    event_logger = getattr(engine, "event_logger", None)
    if event_logger is None:
        return None
    return event_logger
