"""WebHumanAgent：浏览器人类玩家在引擎决策点的 Agent 适配。

设计要点（最小侵入，bridge 文本解析路径零改动）：

- 复用 :class:`~llm_werewolf.agent_team.agents.human_interactive_agent.HumanInteractiveAgent`
  的**静态**辅助（``_classify`` / ``_extract_option_seats`` / ``_fallback_after_invalid``）
  识别决策类型并归一化可选目标，**不复制**逻辑，保持单一事实源。
- 与 stdin 人类的唯一差别：把阻塞式 ``input()`` 换成 ``await self.broker.request(...)``；
  broker 经 ``EventBroadcaster`` 推 ``awaiting_input`` 事件，挂起到浏览器 ``POST /input`` 提交。
- 与 :class:`HumanInteractiveAgent` 一样**不**实现 ``get_structured_response``，因此
  ``WerewolfAdapterBridge`` 的所有决策都回落到 ``get_response`` 文本路径，返回的
  归一化文本（座位号串 / ``救`` / ``毒 [[3]]`` / ``1`` / ``0`` / 发言原文）由 bridge 直接解析。
- ``broker is None``（尚未接线）时返回空串，交由引擎跳过 / 兜底逻辑处理，避免死锁。

字段 ``seat`` / ``broker`` 标记 ``exclude=True``：不进入 ``model_dump`` / 落盘 / 事件流，
broker 持有运行期 ``asyncio.Future``，不可序列化也不应外泄。
"""

from __future__ import annotations

from pydantic import Field

from llm_werewolf.agent_team.agents.base import BaseAgent
from llm_werewolf.agent_team.agents.human_interactive_agent import HumanInteractiveAgent

# Per-decision browser wait before broker falls back (phase timeouts are disabled for web-human runs).
WEB_HUMAN_BROKER_DEADLINE_S = 300.0


class WebHumanAgent(BaseAgent):
    """浏览器人类玩家：每个决策点把归一化请求 ``await`` 给 :class:`HumanInputBroker`。"""

    model: str = Field(default="web-human")
    seat: int = Field(default=0, exclude=True)
    broker: object | None = Field(default=None, exclude=True)  # HumanInputBroker

    model_config = {"arbitrary_types_allowed": True}

    async def get_response(self, message: str) -> str:
        if self.broker is None:
            return ""  # 未接 broker（防御）→ 交由引擎兜底，避免死锁
        kind, _n, allow_skip = HumanInteractiveAgent._classify(message)
        option_seats = sorted(HumanInteractiveAgent._extract_option_seats(message))
        fallback = HumanInteractiveAgent._fallback_after_invalid(kind, allow_skip)
        return await self.broker.request(
            kind=kind,
            prompt=message,
            valid_targets=option_seats,
            fallback=fallback,
            deadline=WEB_HUMAN_BROKER_DEADLINE_S,
        )


__all__ = ["WebHumanAgent"]
