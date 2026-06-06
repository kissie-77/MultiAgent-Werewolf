"""告警通知插件基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_werewolf.observability.core.models import AlertEvent


class AlertNotifier(ABC):
    @abstractmethod
    async def notify(self, events: list[AlertEvent]) -> None:
        """推送一批告警。"""
