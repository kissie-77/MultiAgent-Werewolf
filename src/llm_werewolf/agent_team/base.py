import random
import re

from pydantic import BaseModel, Field
from rich.console import Console

from llm_werewolf.agent_team.mixin import PromptAgentMixin
from llm_werewolf.game_runtime.config import PlayerConfig


console = Console()


class BaseAgent(BaseModel):
    """所有 Agent 的基类。"""

    name: str = Field(...)
    model: str = Field(...)

    async def get_response(self, message: str) -> str:
        raise NotImplementedError("Subclass must implement get_response()")

    def add_decision(self, decision: str) -> None:
        pass

    def get_decision_context(self) -> str:
        return ""

    def __repr__(self) -> str:
        return f"{self.name} ({self.model})"


class DemoAgent(PromptAgentMixin, BaseAgent):
    """使用统一中文 prompt 与 [[n]] 回复的 Demo Agent。"""

    model: str = Field(default="demo")
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    role_definition: object | None = Field(default=None, exclude=True)
    seat_number: int = Field(default=0, exclude=True)
    plan: str = Field(default="自由发挥", exclude=True)

    async def get_response(self, message: str) -> str:
        if "[[1]]" in message and "[[0]]" in message:
            return random.choice(["[[1]]", "[[0]]"])  # noqa: S311

        if "投票意向" in message or "VoteIntentionDecision" in message:
            if "可选放逐目标" in message or "可选目标" in message:
                lines = message.split("\n")
                max_number = 0
                for line in lines:
                    match = re.match(r"^\s*-\s*座位\s*(\d+)", line)
                    if match:
                        max_number = max(max_number, int(match.group(1)))
                if max_number > 0 and random.random() < 0.3:  # noqa: S311
                    return "[[0]]"
                if max_number > 0:
                    return f"[[{random.randint(1, max_number)}]]"  # noqa: S311
            return "[[0]]"

        if "可选目标" in message or "请仅回复" in message or "编号" in message:
            lines = message.split("\n")
            max_number = 0
            for line in lines:
                match = re.match(r"^\s*(\d+)\.\s+", line)
                if match:
                    max_number = max(max_number, int(match.group(1)))
            if max_number > 0:
                return f"[[{random.randint(1, max_number)}]]"  # noqa: S311

        if "警长" in message or "竞选" in message:
            speeches = [
                "[[我相信我能带好队]]",
                "[[请投我，我会保护好人]]",
                "[[我会根据发言找出狼人]]",
            ]
            return random.choice(speeches)  # noqa: S311

        responses = [
            "[[我同意]]",
            "[[我还需要再观察]]",
            "[[这个观点值得讨论]]",
        ]
        return random.choice(responses)  # noqa: S311


class HumanAgent(BaseAgent):
    model: str = Field(default="human")

    async def get_response(self, message: str) -> str:
        console.print(f"\n{message}")
        return input("请输入: ")


def create_agent(
    config: PlayerConfig,
    language: str = "zh-CN",
    use_agentscope: bool = True,
    default_plan: str = "default",
    prompt_version: str = "v2",
) -> BaseAgent:
    """根据玩家配置创建 Agent。"""
    model = config.model.lower()

    if model == "human":
        return HumanAgent(name=config.name, model="human")

    if model == "demo":
        return DemoAgent(name=config.name, model="demo")

    if not use_agentscope:
        msg = "Only AgentScope backend is supported for LLM players."
        raise ValueError(msg)

    from llm_werewolf.agent_team.agentscope_agent import AgentScopeWerewolfAgent

    plan_name = config.plan or default_plan
    return AgentScopeWerewolfAgent(
        name=config.name,
        model=config.model,
        language=language,
        plan_name=plan_name,
        player_config=config,
        prompt_version=prompt_version,
    )
