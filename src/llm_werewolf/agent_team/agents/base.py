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
    extract_seats,
    pick_seat,
    fallback_speech,
    respond,
)
from llm_werewolf.strategy.contracts.decisions import (
    MindStateDecision,
    MultiSeatChoiceDecision,
    SeatChoiceDecision,
    SpeechDecision,
    VoteIntentionDecision,
    WitchNightDecision,
    YesNoDecision,
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
        model_name = getattr(model, "__name__", "")

        if model_name == "SeatChoiceDecision":
            seats = extract_seats(message)
            allow_skip = "座位 0" in message or "跳过" in message or "观望" in message
            seat = pick_seat(
                seats,
                self.seat_number or 1,
                allow_skip=allow_skip,
                rng=self._rng(),
                random_mode=self.random_mode,
            )
            return SeatChoiceDecision(seat=seat, reason="离线座位选择")

        if model_name == "VoteIntentionDecision":
            seats = extract_seats(message)
            seat = pick_seat(
                seats,
                self.seat_number or 1,
                allow_skip=True,
                rng=self._rng(),
                random_mode=self.random_mode,
            )
            return VoteIntentionDecision(seat=seat, reason="离线投票意向")

        if model_name == "YesNoDecision":
            return YesNoDecision(
                choice=(self.seat_number or 1) % 2 == 1,
                reason="离线是否选择",
            )

        if model_name == "WitchNightDecision":
            seats = [seat for seat in extract_seats(message) if seat > 0]
            if "刀口" in message or "被狼人击杀" in message or "击杀" in message:
                action = "save" if (self.seat_number or 1) % 2 == 1 else "none"
                return WitchNightDecision(
                    action=action,
                    seat=0,
                    reason="离线女巫选择",
                )
            if seats and (self.seat_number or 1) % 4 == 0:
                seat = pick_seat(
                    seats,
                    self.seat_number or 1,
                    allow_skip=False,
                    rng=self._rng(),
                    random_mode=self.random_mode,
                )
                return WitchNightDecision(
                    action="poison",
                    seat=seat,
                    reason="离线女巫用毒",
                )
            return WitchNightDecision(action="none", seat=0, reason="离线女巫不行动")

        if model_name == "MultiSeatChoiceDecision":
            seats = [seat for seat in extract_seats(message) if seat > 0]
            if self.random_mode:
                rng = self._rng()
                rng.shuffle(seats)
            picks = seats[:2] if len(seats) >= 2 else seats[:1]
            return MultiSeatChoiceDecision(seats=picks, reason="离线多目标选择")

        if model_name == "SpeechDecision":
            raw = fallback_speech(
                seat_number=self.seat_number or 1,
                role_display=self.get_role_display_name(),
            )
            public = raw.removeprefix("[[").removesuffix("]]")
            return SpeechDecision(public_speech=public, private_thought="离线发言")

        if model_name != "MindStateDecision":
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
    prompt_version: str = "v1",
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
