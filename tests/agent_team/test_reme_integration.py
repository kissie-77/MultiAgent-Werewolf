"""ReMe 集成测试（mock ReMe 实例，不依赖外部 API）。"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_werewolf.agent_team.memory.reme_backend import LLMCompressor, ReMeSemanticBackend
from llm_werewolf.agent_team.memory.working_memory import MemoryItem, WorkingMemory
from llm_werewolf.game_runtime.config.memory_config import MemoryConfig


@pytest.fixture()
def reme_config():
    return MemoryConfig(
        reme_enabled=True,
        reme_llm_api_key="test-key",
        reme_llm_base_url="https://test.example.com/v1",
        reme_embedding_api_key="test-emb-key",
        reme_embedding_base_url="https://test-emb.example.com/v1",
        reme_compress_working_memory=True,
    )


@pytest.fixture()
def mock_reme():
    reme = AsyncMock()
    reme.start = AsyncMock(return_value=reme)
    reme.close = AsyncMock()
    reme.add_memory = AsyncMock()
    reme.list_memory = AsyncMock(return_value=[])
    reme.get_memory = AsyncMock(return_value=None)
    reme.update_memory = AsyncMock()
    reme.summarize_memory = AsyncMock(return_value="语义压缩结果")
    return reme


class TestReMeSemanticBackend:
    def test_store_calls_add_memory(self, reme_config, mock_reme):
        backend = ReMeSemanticBackend(reme_config)
        backend._reme = mock_reme

        backend.store("card-1", {"role": "werewolf", "content": "优先刀预言家"})

        mock_reme.add_memory.assert_called_once()
        call_kwargs = mock_reme.add_memory.call_args
        assert "werewolf" in call_kwargs.kwargs.get("memory_content", call_kwargs.args[0] if call_kwargs.args else "")
        assert "优先刀预言家" in call_kwargs.kwargs.get("memory_content", call_kwargs.args[0] if call_kwargs.args else "")

    def test_retrieve_returns_parsed_cards(self, reme_config, mock_reme):
        mock_reme.list_memory = AsyncMock(return_value=[
            {"memory_content": "[策略卡片] 角色：werewolf\n内容：优先刀预言家\ncard_id：abc123"},
        ])
        backend = ReMeSemanticBackend(reme_config)
        backend._reme = mock_reme

        cards = backend.retrieve("werewolf", limit=3)

        assert len(cards) == 1
        assert cards[0]["role"] == "werewolf"
        assert "优先刀预言家" in cards[0]["content"]

    def test_retrieve_empty_when_no_results(self, reme_config, mock_reme):
        mock_reme.list_memory = AsyncMock(return_value=[])
        backend = ReMeSemanticBackend(reme_config)
        backend._reme = mock_reme

        cards = backend.retrieve("villager", limit=5)

        assert cards == []

    def test_update_weight_calls_update_memory(self, reme_config, mock_reme):
        mock_reme.get_memory = AsyncMock(return_value={"score": 1.0})
        backend = ReMeSemanticBackend(reme_config)
        backend._reme = mock_reme

        backend.update_weight("card-1", 0.1)

        mock_reme.update_memory.assert_called_once()
        call_kwargs = mock_reme.update_memory.call_args
        assert call_kwargs.kwargs.get("score", call_kwargs.args[1] if len(call_kwargs.args) > 1 else None) == pytest.approx(1.1)

    def test_update_weight_noop_when_card_missing(self, reme_config, mock_reme):
        mock_reme.get_memory = AsyncMock(return_value=None)
        backend = ReMeSemanticBackend(reme_config)
        backend._reme = mock_reme

        backend.update_weight("missing-card", 0.1)

        mock_reme.update_memory.assert_not_called()

    def test_parse_card_fallback(self):
        card = ReMeSemanticBackend._parse_card("some raw text", "villager")
        assert card is not None
        assert card["role"] == "villager"


class TestLLMCompressor:
    def test_compress_with_reme_instance(self, reme_config, mock_reme):
        compressor = LLMCompressor(reme_config, reme_instance=mock_reme)
        items = [
            MemoryItem(content="玩家A发言：我觉得B是狼", tag="speech", round_number=1),
            MemoryItem(content="投票给B", tag="decision", round_number=1),
        ]

        result = compressor.compress(items)

        assert "语义压缩结果" in result
        mock_reme.summarize_memory.assert_called_once()

    def test_compress_fallback_on_error(self, reme_config, mock_reme):
        mock_reme.summarize_memory = AsyncMock(side_effect=Exception("API error"))
        compressor = LLMCompressor(reme_config, reme_instance=mock_reme)
        items = [
            MemoryItem(content="发言内容", tag="speech", round_number=1),
        ]

        result = compressor.compress(items)

        assert "听到1段发言" in result

    def test_compress_empty_items(self, reme_config):
        compressor = LLMCompressor(reme_config, reme_instance=None)

        result = compressor.compress([])

        assert result == "无重要事件"


class TestWorkingMemoryWithCompressor:
    def test_compress_dynamic_uses_compressor(self):
        mock_compressor = MagicMock()
        mock_compressor.compress.return_value = "LLM 压缩结果"
        wm = WorkingMemory(max_rounds=3, max_dynamic_items=10, compressor=mock_compressor)

        wm.add_dynamic("发言内容", tag="speech", round_number=1)
        summary = wm.end_round()

        mock_compressor.compress.assert_called_once()
        assert "LLM 压缩结果" in summary

    def test_compress_dynamic_fallback_on_compressor_error(self):
        mock_compressor = MagicMock()
        mock_compressor.compress.side_effect = RuntimeError("LLM down")
        wm = WorkingMemory(max_rounds=3, max_dynamic_items=10, compressor=mock_compressor)

        wm.add_dynamic("发言内容", tag="speech", round_number=1)
        summary = wm.end_round()

        assert "听到1段发言" in summary

    def test_compress_dynamic_without_compressor(self):
        wm = WorkingMemory(max_rounds=3, max_dynamic_items=10)

        wm.add_dynamic("发言内容", tag="speech", round_number=1)
        summary = wm.end_round()

        assert "听到1段发言" in summary


class TestMemoryManagerWithReMe:
    def test_reme_backend_created_when_enabled(self, reme_config):
        from llm_werewolf.agent_team.memory.memory_manager import MemoryManager

        manager = MemoryManager(
            event_logger=MagicMock(),
            role="werewolf",
            config=reme_config,
        )

        assert manager._reme_backend is not None

    def test_reme_backend_not_created_when_disabled(self):
        from llm_werewolf.agent_team.memory.memory_manager import MemoryManager

        config = MemoryConfig(reme_enabled=False)
        manager = MemoryManager(
            event_logger=MagicMock(),
            role="werewolf",
            config=config,
        )

        assert manager._reme_backend is None
