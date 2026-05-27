"""LLMCompressor 工作记忆语义压缩测试。"""

import logging
from unittest.mock import MagicMock, patch

from llm_werewolf.agent_team.memory.llm_compressor import LLMCompressor
from llm_werewolf.agent_team.memory.working_memory import MemoryItem


def _sample_items() -> list[MemoryItem]:
    return [
        MemoryItem(content="我决定先跟票4号", tag="decision", round_number=1),
        MemoryItem(content="3号说5号像狼", tag="speech", round_number=1),
        MemoryItem(content="5号被投票出局", tag="event", round_number=1),
    ]


def test_compress_uses_llm_when_available() -> None:
    compressor = LLMCompressor(
        api_key="test-key",
        base_url="https://api.example.com/v1",
        model="test-model",
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "3号指控5号是狼，我跟票4号，5号被投出"}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("llm_werewolf.agent_team.memory.llm_compressor.httpx.post", return_value=mock_response) as mock_post:
        result = compressor.compress(_sample_items())

    assert "3号指控5号是狼" in result
    mock_post.assert_called_once()


def test_compress_fallback_on_missing_api_key() -> None:
    compressor = LLMCompressor(api_key="", base_url="https://api.example.com/v1")
    result = compressor.compress(_sample_items())

    assert "做了1个决策" in result
    assert "听到1段发言" in result
    assert "记录了1条事件" in result


def test_compress_fallback_on_missing_base_url() -> None:
    compressor = LLMCompressor(api_key="test-key", base_url="")
    result = compressor.compress(_sample_items())

    assert "做了1个决策" in result


def test_compress_fallback_on_llm_exception() -> None:
    compressor = LLMCompressor(
        api_key="test-key",
        base_url="https://api.example.com/v1",
    )

    with patch("llm_werewolf.agent_team.memory.llm_compressor.httpx.post", side_effect=Exception("timeout")):
        result = compressor.compress(_sample_items())

    assert "做了1个决策" in result


def test_compress_logs_first_failure_once_without_traceback(caplog) -> None:
    compressor = LLMCompressor(
        api_key="test-key",
        base_url="https://api.example.com/v1",
    )

    with (
        caplog.at_level(logging.DEBUG, logger="llm_werewolf.agent_team.memory.llm_compressor"),
        patch("llm_werewolf.agent_team.memory.llm_compressor.httpx.post", side_effect=Exception("timeout")),
    ):
        first = compressor.compress(_sample_items())
        second = compressor.compress(_sample_items())

    warning_records = [
        record for record in caplog.records if record.levelno == logging.WARNING
    ]
    assert "做了1个决策" in first
    assert "做了1个决策" in second
    assert len(warning_records) == 1
    assert warning_records[0].exc_info is None
    assert not any(record.exc_info for record in caplog.records)


def test_compress_empty_items() -> None:
    compressor = LLMCompressor(api_key="test-key", base_url="https://api.example.com/v1")
    result = compressor.compress([])
    assert result == "无重要事件"


def test_fallback_compress_only_decisions() -> None:
    compressor = LLMCompressor(api_key="", base_url="")
    items = [
        MemoryItem(content="决定跟票", tag="decision", round_number=1),
        MemoryItem(content="决定换目标", tag="decision", round_number=1),
    ]
    result = compressor.compress(items)
    assert result == "做了2个决策"


def test_group_items_separates_by_tag() -> None:
    items = _sample_items()
    grouped = LLMCompressor._group_items(items)

    assert "【我的决策】" in grouped
    assert "【听到的发言】" in grouped
    assert "【关键事件】" in grouped
    assert "我决定先跟票4号" in grouped
    assert "3号说5号像狼" in grouped
    assert "5号被投票出局" in grouped


def test_working_memory_uses_compressor_on_end_round() -> None:
    from llm_werewolf.agent_team.memory.working_memory import WorkingMemory

    mock_compressor = MagicMock()
    mock_compressor.compress.return_value = "LLM压缩摘要"

    wm = WorkingMemory(compressor=mock_compressor)
    wm.add_dynamic("测试发言", tag="speech", round_number=0)

    summary = wm.end_round()

    assert summary == "第1轮：LLM压缩摘要"
    mock_compressor.compress.assert_called_once()


def test_memory_manager_receives_compressor() -> None:
    from llm_werewolf.agent_team.memory.memory_manager import MemoryManager
    from llm_werewolf.game_runtime.events.events import EventLogger

    mock_compressor = MagicMock()
    manager = MemoryManager(
        EventLogger(),
        role="villager",
        player_id="p1",
        compressor=mock_compressor,
    )

    assert manager.working._compressor is mock_compressor
