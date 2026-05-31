from random import Random

from typing import Any

from pydantic import Field, PrivateAttr, BaseModel, ConfigDict

from llm_werewolf.game_runtime.config import PlayerConfig
from llm_werewolf.agent_team.agents.mixin import PromptAgentMixin
from llm_werewolf.agent_team.agents.demo_policy import (
    DEFAULT_SPEECH,
    DemoPromptKind,
    build_mind_state,
    classify_prompt,
    fallback_speech,
    respond,
)


class BaseAgent(BaseModel):
    """所有 Agent 的基类。"""

    name: str = Field(...)
    model: str = Field(...)
    belief_state: Any | None = Field(default=None, exclude=True)

    async def get_response(self, message: str) -> str:
        raise NotImplementedError("Subclass must implement get_response()")

    def add_decision(self, decision: str) -> None:
        pass

    def get_decision_context(self) -> str:
        return ""

    def __repr__(self) -> str:
        return f"{self.name} ({self.model})"


class DemoAgent(PromptAgentMixin, BaseAgent):
    """离线 smoke / 评测用 Agent，输出与 Bridge 解析兼容的确定性回复。"""

    model_config = ConfigDict(extra="allow")

    model: str = Field(default="demo")
    mode: str = Field(default="deterministic", description="deterministic 或 random")
    seed: int | None = Field(default=None, description="全局随机种子，便于离线复现")
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    role_definition: object | None = Field(default=None, exclude=True)
    seat_number: int = Field(default=0, exclude=True)
    plan: str = Field(default="自由发挥", exclude=True)
    _decision_log: list[str] = PrivateAttr(default_factory=list)

    def model_post_init(self, __context: object) -> None:
        self._decision_log = []

    @property
    def random_mode(self) -> bool:
        return self.mode.strip().lower() == "random"

    def _rng(self) -> Random:
        base = 0 if self.seed is None else int(self.seed)
        return Random(base * 10007 + max(self.seat_number, 1))

    async def get_response(self, message: str) -> str:
        body = respond(
            message,
            seat_number=self.seat_number,
            rng=self._rng(),
            role_display=self.get_role_display_name(),
            random_mode=self.random_mode,
        )
        self.add_decision(body[:240])
        return body

    async def get_structured_response(self, message: str, model: type) -> object | None:
        if getattr(model, "__name__", "") != "MindStateDecision":
            return None
        is_wolf = False
        role_def = getattr(self, "role_definition", None)
        if role_def is not None:
            from llm_werewolf.game_runtime.types import Camp

            is_wolf = getattr(role_def, "camp", None) == Camp.WEREWOLF
        return build_mind_state(
            message,
            seat_number=self.seat_number,
            rng=self._rng(),
            random_mode=self.random_mode,
            is_wolf=is_wolf,
        )

    def _generate_fallback_response(self, prompt: str, reason: str) -> str:
        _ = prompt, reason
        return fallback_speech(
            seat_number=self.seat_number or 1,
            role_display=self.get_role_display_name(),
        )

    def add_decision(self, decision: str) -> None:
        if not decision:
            return
        self._decision_log.append(decision.strip())
        if len(self._decision_log) > 24:
            self._decision_log = self._decision_log[-24:]

    def get_decision_context(self) -> str:
        if not self._decision_log:
            return ""
        recent = self._decision_log[-3:]
        return "最近离线决策摘要:\n" + "\n".join(f"- {line}" for line in recent)


def create_agent(
    config: PlayerConfig,
    language: str = "zh-CN",
    use_agentscope: bool = True,
    default_plan: str = "default",
    prompt_version: str = "v2",
    *,
    demo_seed: int | None = None,
) -> BaseAgent:
    """根据玩家配置创建 Agent。"""
    model = (config.model or "").lower()

    if model == "human":
        from llm_werewolf.agent_team.agents.human_interactive_agent import HumanInteractiveAgent

        return HumanInteractiveAgent(name=config.name, model="human")

    if model == "demo":
        return DemoAgent(
            name=config.name,
            model="demo",
            plan=config.plan or "自由发挥",
            seed=demo_seed,
        )

    if not use_agentscope:
        msg = "Only AgentScope backend is supported for LLM players."
        raise ValueError(msg)

    from llm_werewolf.agent_team.agents.agentscope_agent import AgentScopeWerewolfAgent

    plan_name = config.plan or default_plan
    return AgentScopeWerewolfAgent(
        name=config.name,
        model=config.model,
        language=language,
        plan_name=plan_name,
        player_config=config,
        prompt_version=prompt_version,
    )


__all__ = [
    "BaseAgent",
    "DemoAgent",
    "create_agent",
    "DEFAULT_SPEECH",
    "DemoPromptKind",
    "classify_prompt",
]
