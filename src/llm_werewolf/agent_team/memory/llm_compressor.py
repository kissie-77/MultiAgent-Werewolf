"""Working-memory LLM compressor with retry and fallback behavior."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
import logging

import httpx

if TYPE_CHECKING:
    from llm_werewolf.agent_team.memory.working_memory import MemoryItem

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 0.5
_WARNING_INTERVAL = 5

_PROMPT_TEMPLATE = (
    "请将以下狼人杀本轮动态记忆压缩为 2-3 句中文摘要。\n"
    "必须保留：\n"
    "1. 谁说了什么关键信息\n"
    "2. 谁投票、被投票、死亡或使用技能\n"
    "3. 我的关键决策和理由\n"
    "4. 不要引入未出现的信息\n\n"
    "{grouped_content}"
)


def fallback_compress(items: list[MemoryItem], separator: str = "；") -> str:
    """Rule-based compression by counting items per tag.

    Shared by LLMCompressor (primary fallback) and WorkingMemory (when no
    compressor is configured).  ``separator` controls the join character so
    callers can match their surrounding formatting conventions.
    """
    decisions = [item for item in items if item.tag == "decision"]
    speeches = [item for item in items if item.tag == "speech"]
    events = [item for item in items if item.tag == "event"]

    parts: list[str] = []
    if decisions:
        parts.append(f"做了{len(decisions)}个决策")
    if speeches:
        parts.append(f"听到{len(speeches)}段发言")
    if events:
        parts.append(f"记录了{len(events)}条事件")
    if not parts:
        parts.append(f"保留了{len(items)}条动态信息")
    return separator.join(parts)


class LLMCompressor:
    """Use an OpenAI-compatible endpoint to compress working memory."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "default",
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._failure_count = 0

    def compress(self, items: list[MemoryItem]) -> str:
        if not items:
            return "无重要事件。"
        if not self._api_key or not self._base_url:
            return fallback_compress(items)
        try:
            compressed = self._call_llm(items)
        except Exception as exc:
            self._failure_count += 1
            if self._failure_count == 1 or self._failure_count % _WARNING_INTERVAL == 0:
                logger.warning(
                    "LLM compression failed %s time(s), using fallback: %s: %s",
                    self._failure_count,
                    type(exc).__name__,
                    exc,
                )
            return fallback_compress(items)
        self._failure_count = 0
        return compressed

    def _call_llm(self, items: list[MemoryItem]) -> str:
        grouped = self._group_items(items)
        prompt = _PROMPT_TEMPLATE.format(grouped_content=grouped)
        return self.call_llm_text(prompt, max_tokens=300)

    def call_llm_text(self, prompt: str, max_tokens: int = 300) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = httpx.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as exc:
                last_error = exc
                if attempt == _MAX_RETRIES - 1:
                    break
                time.sleep(_INITIAL_BACKOFF_SECONDS * (2**attempt))

        assert last_error is not None
        raise last_error

    @staticmethod
    def _group_items(items: list[MemoryItem]) -> str:
        groups: dict[str, list[str]] = {
            "decision": [],
            "speech": [],
            "event": [],
            "other": [],
        }
        for item in items:
            groups.get(item.tag, groups["other"]).append(item.content)

        parts: list[str] = []
        if groups["decision"]:
            parts.append("【我的决策】" + "；".join(groups["decision"]))
        if groups["speech"]:
            parts.append("【听到的发言】" + "；".join(groups["speech"]))
        if groups["event"]:
            parts.append("【关键事件】" + "；".join(groups["event"]))
        if groups["other"]:
            parts.append("【其他信息】" + "；".join(groups["other"]))
        return "\n".join(parts)
