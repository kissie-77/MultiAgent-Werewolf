"""工作记忆：管理当前决策窗口内的活跃信息。"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_werewolf.agent_team.memory.base import CompressorProtocol

logger = logging.getLogger(__name__)

PROTECTED_PERSISTENT_TAGS = frozenset({"belief", "wolf_camp", "belief_rules"})
FIXED_GAME_INFO_TAGS = frozenset({"role_pool"})
BELIEF_PERSISTENT_PRIORITY = 10
_BELIEF_RULES_TEXT = "\n".join([
    "【信念/意向更新规则】",
    "- first_order / second_order 仅填写需要修改的条目；无变化则留空数组 []。",
    "- 每条信念修改必须含 reason，说明依据。",
    "- 若 seat 与上一帧不同，必须在顶层 reason 说明改票理由。",
])


@dataclass
class MemoryItem:
    """工作记忆中的单条信息。"""

    content: str
    tag: str
    round_number: int
    priority: int = 1


class WorkingMemory:
    """当前回合推理所需的活跃信息，带简单滑动窗口。"""

    def __init__(
        self,
        max_rounds: int = 5,
        max_dynamic_items: int = 20,
        max_persistent_chars: int = 4000,
        compressor: CompressorProtocol | None = None,
    ):
        self._persistent: list[MemoryItem] = []
        self._dynamic: list[MemoryItem] = []
        self._summaries: deque[str] = deque(maxlen=max_rounds)
        self._max_dynamic = max_dynamic_items
        self._max_persistent_chars = max_persistent_chars
        self._current_round = 0
        self._compressor = compressor

    @property
    def current_round(self) -> int:
        """当前工作记忆轮次。"""
        return self._current_round

    def add_persistent(self, content: str, tag: str = "identity", priority: int = 3) -> None:
        """添加常驻记忆。超出字符限制时截断低优先级条目。"""
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
        self._trim_persistent()

    def upsert_persistent(self, content: str, tag: str, priority: int = 3) -> None:
        """Replace the persistent slot for ``tag`` (protected tags are never evicted)."""
        self._persistent = [item for item in self._persistent if item.tag != tag]
        if content.strip():
            self._persistent.append(
                MemoryItem(
                    content=content.strip(),
                    tag=tag,
                    round_number=self._current_round,
                    priority=priority,
                )
            )
            self._trim_persistent()

    def remove_persistent(self, tag: str) -> None:
        self._persistent = [item for item in self._persistent if item.tag != tag]

    def _trim_persistent(self) -> None:
        """Ensure non-protected persistent zone stays within char budget."""
        total = sum(len(item.content) for item in self._persistent)
        trimmable = [item for item in self._persistent if item.tag not in PROTECTED_PERSISTENT_TAGS]
        while total > self._max_persistent_chars and trimmable:
            if len(self._persistent) <= 1:
                break
            weakest = min(trimmable, key=lambda item: (item.priority, item.round_number))
            self._persistent.remove(weakest)
            trimmable.remove(weakest)
            total = sum(len(item.content) for item in self._persistent)

    def add_dynamic(
        self, content: str, tag: str, round_number: int | None = None, priority: int = 1
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
            # priority 高的优先保留；同 priority 保留最新的（后加入的）
            indexed = list(enumerate(self._dynamic))
            indexed.sort(key=lambda t: (t[1].priority, t[0]), reverse=True)
            self._dynamic = [item for _, item in indexed[: self._max_dynamic]]

    def end_round(self) -> str:
        """轮结束时压缩动态记忆并清空当前轮缓存。"""
        summary = self._compress_dynamic()
        self._summaries.append(summary)
        self._dynamic.clear()
        self._current_round += 1
        return summary

    def get_context(self, *, include_belief: bool = True) -> str:
        """格式化为可注入提示词的上下文片段。"""
        parts: list[str] = []
        belief_items = []
        if include_belief:
            belief_items = [
                item
                for item in self._persistent
                if item.tag in PROTECTED_PERSISTENT_TAGS
            ]
        fixed_game_items = [
            item
            for item in self._persistent
            if item.tag in FIXED_GAME_INFO_TAGS
        ]
        stable_items = [
            item
            for item in self._persistent
            if item.tag not in PROTECTED_PERSISTENT_TAGS
            and item.tag not in FIXED_GAME_INFO_TAGS
        ]
        if fixed_game_items:
            parts.append(
                "【本局固定信息】\n" + "\n".join(f"- {item.content}" for item in fixed_game_items)
            )
        if belief_items:
            ordered = sorted(
                belief_items,
                key=lambda item: {"belief_rules": 0, "belief": 1, "wolf_camp": 2}.get(item.tag, 9),
            )
            parts.append(
                "【内心信念】\n" + "\n".join(f"- {item.content}" for item in ordered)
            )
        if stable_items:
            parts.append(
                "【稳定经验】\n" + "\n".join(f"- {item.content}" for item in stable_items)
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
        """压缩当前轮动态信息。有 LLM 压缩器时用语义压缩，否则用规则式摘要。"""
        from llm_werewolf.agent_team.memory.llm_compressor import fallback_compress

        round_label = self._current_round + 1
        if not self._dynamic:
            return f"第{round_label}轮：无重要事件"

        if self._compressor is not None:
            try:
                compressed = self._compressor.compress(self._dynamic)
                return f"第{round_label}轮：{compressed}"
            except Exception:
                logger.warning("Working memory LLM compression failed, using fallback", exc_info=True)

        return f"第{round_label}轮：{fallback_compress(self._dynamic, separator='，')}"
