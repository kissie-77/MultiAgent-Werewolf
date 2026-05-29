"""记忆模块基础协议。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from llm_werewolf.agent_team.memory.working_memory import MemoryItem


@runtime_checkable
class SemanticBackend(Protocol):
    """语义记忆后端协议。"""

    def store(self, card_id: str, data: dict) -> None:
        """存储一张策略卡片。"""

    def retrieve(self, role: str, limit: int) -> list[dict]:
        """按角色检索策略卡片。"""

    def retrieve_all(self, role: str) -> list[dict]:
        """按角色检索全部策略卡片（不受 limit 限制）。"""

    def delete(self, card_id: str) -> None:
        """删除一张策略卡片。"""

    def update_weight(self, card_id: str, delta: float) -> None:
        """更新卡片权重。"""


@runtime_checkable
class CompressorProtocol(Protocol):
    """LLM 压缩器协议，供工作记忆和语义记忆层使用。"""

    def compress(self, items: list[MemoryItem]) -> str:
        """将一组记忆条目压缩为摘要字符串。"""

    def call_llm_text(self, prompt: str, max_tokens: int = 300) -> str:
        """向 LLM 发送原始 prompt 并返回文本响应。"""
