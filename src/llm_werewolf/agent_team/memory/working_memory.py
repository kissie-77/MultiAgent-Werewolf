"""工作记忆：管理当前决策窗口内的活跃信息。"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class MemoryItem:
    """工作记忆中的单条信息。"""

    content: str
    tag: str
    round_number: int
    priority: int = 1


class WorkingMemory:
    """当前回合推理所需的活跃信息，带简单滑动窗口。"""

    def __init__(self, max_rounds: int = 5, max_dynamic_items: int = 20):
        self._persistent: list[MemoryItem] = []
        self._dynamic: list[MemoryItem] = []
        self._summaries: deque[str] = deque(maxlen=max_rounds)
        self._max_dynamic = max_dynamic_items
        self._current_round = 0

    @property
    def current_round(self) -> int:
        """当前工作记忆轮次。"""
        return self._current_round

    def add_persistent(self, content: str, tag: str = "identity", priority: int = 3) -> None:
        """添加常驻记忆。"""
        if not content.strip():
            return
        self._persistent.append(
            MemoryItem(
                content=content.strip(),
                tag=tag,
                round_number=self._current_round,
                priority=priority,
            )
        )

    def add_dynamic(
        self,
        content: str,
        tag: str,
        round_number: int | None = None,
        priority: int = 1,
    ) -> None:
        """添加当前轮动态记忆。"""
        if not content.strip():
            return
        item = MemoryItem(
            content=content.strip(),
            tag=tag,
            round_number=self._current_round if round_number is None else round_number,
            priority=priority,
        )
        self._dynamic.append(item)
        if len(self._dynamic) > self._max_dynamic:
            self._dynamic = self._dynamic[-self._max_dynamic :]

    def end_round(self) -> str:
        """轮结束时压缩动态记忆并清空当前轮缓存。"""
        summary = self._compress_dynamic()
        self._summaries.append(summary)
        self._dynamic.clear()
        self._current_round += 1
        return summary

    def get_context(self) -> str:
        """格式化为可注入提示词的上下文片段。"""
        parts: list[str] = []
        if self._persistent:
            parts.append(
                "【稳定经验】\n" + "\n".join(f"- {item.content}" for item in self._persistent)
            )
        if self._summaries:
            parts.append("【历史回顾】\n" + "\n".join(self._summaries))
        if self._dynamic:
            parts.append(
                "【本轮记忆】\n" + "\n".join(f"- {item.content}" for item in self._dynamic)
            )
        return "\n\n".join(parts)

    def clear(self) -> None:
        """清空全部工作记忆。"""
        self._persistent.clear()
        self._dynamic.clear()
        self._summaries.clear()
        self._current_round = 0

    def _compress_dynamic(self) -> str:
        """用规则式摘要压缩当前轮动态信息。"""
        round_label = self._current_round + 1
        if not self._dynamic:
            return f"第{round_label}轮：无重要事件"

        decisions = [item for item in self._dynamic if item.tag == "decision"]
        speeches = [item for item in self._dynamic if item.tag == "speech"]
        events = [item for item in self._dynamic if item.tag == "event"]
        summary_parts: list[str] = []
        if decisions:
            summary_parts.append(f"做了{len(decisions)}个决策")
        if speeches:
            summary_parts.append(f"听到{len(speeches)}段发言")
        if events:
            summary_parts.append(f"记录了{len(events)}条事件")
        if not summary_parts:
            summary_parts.append(f"保留了{len(self._dynamic)}条动态信息")
        return f"第{round_label}轮：{'，'.join(summary_parts)}"
