"""工作记忆 LLM 语义压缩器。

用 OpenAI 兼容端点将本轮动态记忆压缩为 2-3 句摘要。
不依赖 ReMe，不处理语义记忆。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import logging

import httpx

if TYPE_CHECKING:
    from llm_werewolf.agent_team.memory.working_memory import MemoryItem

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = (
    "请将以下狼人杀本轮动态记忆压缩为 2-3 句中文摘要。\n"
    "必须保留：\n"
    "1. 谁说了什么关键判断\n"
    "2. 谁投票/被投票/死亡/使用技能\n"
    "3. 我的关键决策和理由\n"
    "4. 不要引入未出现的信息\n\n"
    "{grouped_content}"
)


class LLMCompressor:
    """用 LLM API 压缩工作记忆动态区。"""

    def __init__(
        self, api_key: str, base_url: str, model: str = "default", timeout: float = 30.0
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._warned_failure = False

    def compress(self, items: list[MemoryItem]) -> str:
        if not items:
            return "无重要事件"
        if not self._api_key or not self._base_url:
            return self._fallback_compress(items)
        try:
            return self._call_llm(items)
        except Exception as exc:
            if not self._warned_failure:
                logger.warning(
                    "LLM compression failed, using fallback: %s: %s", type(exc).__name__, exc
                )
                self._warned_failure = True
            return self._fallback_compress(items)

    def _call_llm(self, items: list[MemoryItem]) -> str:
        grouped = self._group_items(items)
        prompt = _PROMPT_TEMPLATE.format(grouped_content=grouped)
        return self._call_llm_text(prompt, max_tokens=300)

    def _call_llm_text(self, prompt: str, max_tokens: int = 300) -> str:
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        resp = httpx.post(
            f"{self._base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    @staticmethod
    def _group_items(items: list[MemoryItem]) -> str:
        groups: dict[str, list[str]] = {"decision": [], "speech": [], "event": [], "other": []}
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

    @staticmethod
    def _fallback_compress(items: list[MemoryItem]) -> str:
        decisions = [i for i in items if i.tag == "decision"]
        speeches = [i for i in items if i.tag == "speech"]
        events = [i for i in items if i.tag == "event"]
        parts: list[str] = []
        if decisions:
            parts.append(f"做了{len(decisions)}个决策")
        if speeches:
            parts.append(f"听到{len(speeches)}段发言")
        if events:
            parts.append(f"记录了{len(events)}条事件")
        return "，".join(parts) if parts else f"保留了{len(items)}条动态信息"
