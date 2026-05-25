"""记忆模块基础协议。"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SemanticBackend(Protocol):
    """语义记忆后端协议。"""

    def store(self, card_id: str, data: dict) -> None:
        """存储一张策略卡片。"""

    def retrieve(self, role: str, limit: int) -> list[dict]:
        """按角色检索策略卡片。"""

    def update_weight(self, card_id: str, delta: float) -> None:
        """更新卡片权重。"""
