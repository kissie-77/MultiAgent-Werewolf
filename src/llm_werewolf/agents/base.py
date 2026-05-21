import os
import re
import random
import asyncio
from functools import cached_property

import dotenv
from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError
from pydantic import Field, BaseModel, ConfigDict, computed_field
from rich.console import Console
from openai.types.shared import ReasoningEffort

from llm_werewolf.core.config import PlayerConfig
from llm_werewolf.agents.mixin import PromptAgentMixin

dotenv.load_dotenv()


console = Console()


class BaseAgent(BaseModel):
    """Base class for all agents."""

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
    """Demo agent with unified Chinese prompts and [[n]] responses."""

    model: str = Field(default="demo")
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    role_definition: object | None = Field(default=None, exclude=True)
    seat_number: int = Field(default=0, exclude=True)
    plan: str = Field(default="自由发挥", exclude=True)

    async def get_response(self, message: str) -> str:
        if "[[1]]" in message and "[[0]]" in message:
            return random.choice(["[[1]]", "[[0]]"])  # noqa: S311

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


class LLMAgent(PromptAgentMixin, BaseAgent):
    """LLM agent using OpenAI-compatible API and unified Chinese prompts."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    api_key: str
    base_url: str
    reasoning_effort: ReasoningEffort | None = Field(default=None)
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    decision_history: list[str] = Field(default_factory=list)
    role_definition: object | None = Field(default=None, exclude=True)
    seat_number: int = Field(default=0, exclude=True)
    plan: str = Field(default="自由发挥", exclude=True)

    @computed_field
    @cached_property
    def client(self) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def get_response(self, message: str, max_retries: int = 3, timeout: float = 30.0) -> str:
        self.chat_history.append({"role": "user", "content": message})

        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                kwargs: dict = {
                    "model": self.model,
                    "messages": self.chat_history,
                    "stream": False,
                }
                if self.reasoning_effort:
                    kwargs["reasoning_effort"] = self.reasoning_effort
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**kwargs),
                    timeout=timeout,
                )
                full_response = response.choices[0].message.content or ""
                self.chat_history.append({"role": "assistant", "content": full_response})
                return full_response

            except RateLimitError as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
            except (APITimeoutError, APIError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception:
                raise

        raise last_error  # type: ignore[misc]

    def add_decision(self, decision: str) -> None:
        self.decision_history.append(decision)

    def get_decision_context(self) -> str:
        if not self.decision_history:
            return ""
        return "\n\n你此前的决策记录：\n" + "\n".join(f"- {d}" for d in self.decision_history)


def create_agent(
    config: PlayerConfig,
    language: str = "zh-CN",
    use_agentscope: bool = True,
    default_plan: str = "default",
) -> DemoAgent | HumanAgent | LLMAgent:
    """Create an agent from player configuration."""
    model = config.model.lower()

    if model == "human":
        return HumanAgent(name=config.name, model="human")

    if model == "demo":
        return DemoAgent(name=config.name, model="demo")

    if use_agentscope:
        from llm_werewolf.integration.agentscope import AgentScopeWerewolfAgent

        plan_name = config.plan or default_plan
        return AgentScopeWerewolfAgent(
            name=config.name,
            model=config.model,
            language=language,
            plan_name=plan_name,
            player_config=config,
        )

    api_key = None
    if config.api_key_env:
        api_key = os.getenv(config.api_key_env)
    if not api_key:
        raise ValueError(
            f"API key not found in environment variable '{config.api_key_env}' "
            f"for player '{config.name}'"
        )

    return LLMAgent(
        name=config.name,
        model=config.model,
        api_key=api_key,
        base_url=config.base_url or "",
    )
