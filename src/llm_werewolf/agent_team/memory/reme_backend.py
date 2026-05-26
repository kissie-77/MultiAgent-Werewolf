"""基于 ReMe 的语义记忆后端 + LLM 语义压缩器。

使用 ReMe（AgentScope 官方记忆库）实现：
1. ReMeSemanticBackend —— 跨局策略卡片的向量存储与检索
2. LLMCompressor —— 工作记忆动态区的 LLM 语义压缩
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from llm_werewolf.agent_team.memory.base import SemanticBackend
from llm_werewolf.game_runtime.config.memory_config import MemoryConfig

logger = logging.getLogger(__name__)


class ReMeSemanticBackend(SemanticBackend):
    """用 ReMe 向量存储实现策略卡片持久化。"""

    def __init__(self, config: MemoryConfig) -> None:
        self._config = config
        self._reme: Any = None
        self._init_lock = asyncio.Lock()

    async def _ensure_reme(self) -> Any:
        if self._reme is not None:
            return self._reme
        async with self._init_lock:
            if self._reme is not None:
                return self._reme
            try:
                from reme import ReMe
            except ImportError as exc:
                raise ImportError(
                    "reme-ai is required for ReMe backend. "
                    "Install with: pip install reme-ai"
                ) from exc

            self._reme = ReMe(
                llm_api_key=self._config.reme_llm_api_key,
                llm_base_url=self._config.reme_llm_base_url,
                embedding_api_key=self._config.reme_embedding_api_key,
                embedding_base_url=self._config.reme_embedding_base_url,
                default_embedding_model_config={
                    "model_name": self._config.reme_embedding_model,
                },
                working_dir=self._config.reme_working_dir,
                enable_logo=False,
                log_to_console=False,
                log_to_file=False,
                enable_profile=False,
            )
            await self._reme.start()
            return self._reme

    async def aclose(self) -> None:
        if self._reme is not None:
            try:
                await self._reme.close()
            except Exception:
                logger.debug("Error closing ReMe instance", exc_info=True)
            finally:
                self._reme = None

    def store(self, card_id: str, data: dict) -> None:
        role = data.get("role", "unknown")
        content = data.get("content", "")
        asyncio.run(self._store_async(card_id, role, content))

    async def _store_async(self, card_id: str, role: str, content: str) -> None:
        reme = await self._ensure_reme()
        message_content = (
            f"[策略卡片] 角色：{role}\n"
            f"内容：{content}\n"
            f"card_id：{card_id}"
        )
        await reme.add_memory(
            memory_content=message_content,
            task_name=f"werewolf_{role}",
        )

    def retrieve(self, role: str, limit: int) -> list[dict]:
        return asyncio.run(self._retrieve_async(role, limit))

    async def _retrieve_async(self, role: str, limit: int) -> list[dict]:
        reme = await self._ensure_reme()
        result = await reme.list_memory(
            task_name=f"werewolf_{role}",
            limit=limit,
        )
        if not result:
            return []
        cards: list[dict] = []
        for item in result:
            memory_content = item.get("memory_content", "")
            card = self._parse_card(memory_content, role)
            if card:
                cards.append(card)
        return cards

    def update_weight(self, card_id: str, delta: float) -> None:
        asyncio.run(self._update_weight_async(card_id, delta))

    async def _update_weight_async(self, card_id: str, delta: float) -> None:
        reme = await self._ensure_reme()
        try:
            existing = await reme.get_memory(card_id)
            if existing is None:
                return
            current_score = existing.get("score", 1.0)
            new_score = current_score + delta
            await reme.update_memory(
                memory_id=card_id,
                score=max(0.0, new_score),
            )
        except Exception:
            logger.warning("Failed to update weight for card %s", card_id, exc_info=True)

    @staticmethod
    def _parse_card(memory_content: str, role: str) -> dict | None:
        """从 ReMe memory_content 解析出策略卡片字段。"""
        content = memory_content
        card_id = ""
        for line in memory_content.split("\n"):
            if line.startswith("内容："):
                content = line[len("内容："):]
            elif line.startswith("card_id："):
                card_id = line[len("card_id："):]
        if not content or content == memory_content:
            content = memory_content
        return {
            "id": card_id or memory_content[:8],
            "role": role,
            "content": content,
            "weight": 1.0,
            "win_count": 0,
            "use_count": 0,
        }


class LLMCompressor:
    """用 ReMe 的 LLM 做工作记忆语义压缩。"""

    def __init__(
        self,
        config: MemoryConfig,
        reme_instance: Any | None = None,
    ) -> None:
        self._config = config
        self._reme = reme_instance

    def compress(self, items: list) -> str:
        return asyncio.run(self._compress_async(items))

    async def _compress_async(self, items: list) -> str:
        if not items:
            return "无重要事件"

        grouped: dict[str, list[str]] = {"decision": [], "speech": [], "event": [], "other": []}
        for item in items:
            tag = getattr(item, "tag", "other")
            content = getattr(item, "content", str(item))
            grouped.get(tag, grouped["other"]).append(content)

        prompt_parts = ["请将以下本轮游戏信息压缩为 2-3 句话的摘要。"]
        prompt_parts.append("要求：保留关键信息（谁说了什么、谁被投出、关键推理线索），去掉无关细节。\n")
        if grouped["decision"]:
            prompt_parts.append("【我的决策】" + "；".join(grouped["decision"]))
        if grouped["speech"]:
            prompt_parts.append("【听到的发言】" + "；".join(grouped["speech"]))
        if grouped["event"]:
            prompt_parts.append("【关键事件】" + "；".join(grouped["event"]))
        if grouped["other"]:
            prompt_parts.append("【其他信息】" + "；".join(grouped["other"]))

        prompt = "\n".join(prompt_parts)

        try:
            response = await self._call_llm(prompt)
            return response if response else self._fallback_compress(items)
        except Exception:
            logger.warning("LLM compression failed, using fallback", exc_info=True)
            return self._fallback_compress(items)

    async def _call_llm(self, prompt: str) -> str:
        if self._reme is not None:
            return await self._call_via_reme(prompt)
        return await self._call_direct(prompt)

    async def _call_via_reme(self, prompt: str) -> str:
        try:
            messages = [{"role": "user", "content": prompt}]
            result = await self._reme.summarize_memory(
                messages=messages,
                description="compress_working_memory",
            )
            return str(result) if result else ""
        except Exception:
            logger.debug("ReMe summarize_memory failed, falling back to direct call", exc_info=True)
            return await self._call_direct(prompt)

    async def _call_direct(self, prompt: str) -> str:
        import httpx

        base_url = self._config.reme_llm_base_url
        api_key = self._config.reme_llm_api_key
        if not base_url or not api_key:
            return self._fallback_compress([])

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "default",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    @staticmethod
    def _fallback_compress(items: list) -> str:
        decisions = sum(1 for i in items if getattr(i, "tag", "") == "decision")
        speeches = sum(1 for i in items if getattr(i, "tag", "") == "speech")
        events = sum(1 for i in items if getattr(i, "tag", "") == "event")
        parts: list[str] = []
        if decisions:
            parts.append(f"做了{decisions}个决策")
        if speeches:
            parts.append(f"听到{speeches}段发言")
        if events:
            parts.append(f"记录了{events}条事件")
        return "，".join(parts) if parts else f"保留了{len(items)}条动态信息"
