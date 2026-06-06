"""WorkingMemory 上下文压缩精细度测试。

验证目标：
- 第 5 轮时历史压缩只保留关键信息（摘要形式）而非暴力截断
- 摘要 deque 最多保留 max_rounds 条，早期记录自然淘汰
- 压缩后输出保留决策/事件/发言的语义类别标记
- protected 标签（belief 等）在整个生命周期中不会被驱逐
- 动态记忆超限时按 priority 驱逐低优先级条目而非截断
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from llm_werewolf.agent_team.memory.working_memory import (
    MemoryItem,
    WorkingMemory,
    PROTECTED_PERSISTENT_TAGS,
)
from llm_werewolf.agent_team.memory.llm_compressor import fallback_compress


class TestHistoryCompressionNotTruncation:
    """证明多轮后历史以摘要形式保留关键信息，而非暴力丢弃或截断。"""

    def test_five_rounds_produce_five_summaries(self) -> None:
        """5 轮结束后 _summaries 包含 5 条摘要。"""
        wm = WorkingMemory(max_rounds=5)
        for i in range(5):
            wm.add_dynamic(f"第{i+1}轮有人发言讨论", "speech", round_number=i)
            wm.add_dynamic(f"我决策投票给{i+1}号", "decision", round_number=i)
            wm.add_dynamic(f"{i+1}号被投票淘汰", "event", round_number=i)
            wm.end_round()

        context = wm.get_context()
        assert "【历史回顾】" in context
        assert "第1轮" in context
        assert "第5轮" in context

    def test_sixth_round_evicts_oldest_summary_not_recent(self) -> None:
        """第 6 轮开始时，第 1 轮摘要被淘汰，但第 2-6 轮保留。"""
        wm = WorkingMemory(max_rounds=5)
        for i in range(6):
            wm.add_dynamic(f"本轮发言内容_{i+1}", "speech", round_number=i)
            wm.end_round()

        context = wm.get_context()
        # fallback_compress 输出 "第N轮：..." 格式
        assert "第1轮" not in context
        assert "第2轮" in context
        assert "第6轮" in context

    def test_summaries_are_semantic_not_raw_dump(self) -> None:
        """压缩后的摘要包含语义类别统计，而非原始信息的暴力拼接。"""
        wm = WorkingMemory(max_rounds=5)
        for _ in range(3):
            wm.add_dynamic("长篇发言内容" * 20, "speech")
        for _ in range(2):
            wm.add_dynamic("我的投票决策", "decision")
        wm.add_dynamic("有人被淘汰", "event")

        summary = wm.end_round()

        assert "决策" in summary or "发言" in summary or "事件" in summary
        total_raw_chars = sum(len(item.content) for item in [
            MemoryItem("长篇发言内容" * 20, "speech", 0),
            MemoryItem("长篇发言内容" * 20, "speech", 0),
            MemoryItem("长篇发言内容" * 20, "speech", 0),
        ])
        assert len(summary) < total_raw_chars

    def test_llm_compressor_produces_richer_summary(self) -> None:
        """配置 LLM 压缩器时，使用 LLM 而非规则摘要（mock 验证调用）。"""
        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = "预言家验出3号为狼人，全票淘汰3号"

        wm = WorkingMemory(max_rounds=5, compressor=mock_compressor)
        wm.add_dynamic("预言家发言说验了3号", "speech")
        wm.add_dynamic("3号被投票淘汰", "event")
        wm.add_dynamic("我决定投3号", "decision")

        summary = wm.end_round()

        mock_compressor.compress.assert_called_once()
        assert "预言家验出3号为狼人" in summary
        assert "第1轮" in summary


class TestProtectedTagsNeverEvicted:
    """belief / wolf_camp / belief_rules 在任何操作下都不会被清除。"""

    def test_belief_persists_through_persistent_overflow(self) -> None:
        """当 persistent 超出字符限制时，belief 不会被驱逐。"""
        wm = WorkingMemory(max_persistent_chars=200)
        wm.add_persistent("我的信念矩阵：3号是狼人", "belief", priority=10)
        wm.add_persistent("狼队思维：今晚刀4号", "wolf_camp", priority=10)

        for i in range(20):
            wm.add_persistent(f"一些很长的经验内容 {i}" * 5, "experience", priority=1)

        context = wm.get_context()
        assert "我的信念矩阵" in context
        assert "狼队思维" in context

    def test_belief_survives_multiple_rounds(self) -> None:
        """belief 在 5 轮 end_round 后依然存在。"""
        wm = WorkingMemory(max_rounds=5)
        wm.add_persistent("初始信念", "belief", priority=10)

        for i in range(5):
            wm.add_dynamic(f"第{i+1}轮事件", "event")
            wm.end_round()

        context = wm.get_context()
        assert "初始信念" in context


class TestDynamicEvictionByPriority:
    """动态记忆超限时按 priority 驱逐，而非 FIFO 截断。"""

    def test_low_priority_evicted_first(self) -> None:
        """max_dynamic_items=3 时，低 priority 项优先被驱逐。"""
        wm = WorkingMemory(max_dynamic_items=3)
        wm.add_dynamic("重要决策", "decision", priority=10)
        wm.add_dynamic("次要发言1", "speech", priority=1)
        wm.add_dynamic("次要发言2", "speech", priority=1)
        wm.add_dynamic("关键事件", "event", priority=8)

        context = wm.get_context()
        assert "重要决策" in context
        assert "关键事件" in context

    def test_high_priority_always_retained(self) -> None:
        """高 priority 项即使最先加入也不会被后续低 priority 项挤出。"""
        wm = WorkingMemory(max_dynamic_items=2)
        wm.add_dynamic("最关键信息", "decision", priority=99)
        wm.add_dynamic("普通1", "speech", priority=1)
        wm.add_dynamic("普通2", "speech", priority=1)
        wm.add_dynamic("普通3", "speech", priority=1)

        context = wm.get_context()
        assert "最关键信息" in context


class TestFallbackCompressCategories:
    """规则式压缩保留语义类别信息。"""

    def test_fallback_compress_categorizes_items(self) -> None:
        items = [
            MemoryItem("投票给3号", "decision", 1),
            MemoryItem("投票给5号", "decision", 1),
            MemoryItem("听到4号发言", "speech", 1),
            MemoryItem("3号被淘汰", "event", 1),
        ]
        result = fallback_compress(items)
        assert "2个决策" in result
        assert "1段发言" in result
        assert "1条事件" in result

    def test_fallback_compress_empty_items(self) -> None:
        items = [MemoryItem("一些信息", "other", 1)]
        result = fallback_compress(items)
        assert "1条动态信息" in result
