"""AgentScope Agent adapter for LLMWerewolf integration.

This module provides an adapter that wraps AgentScope's AgentBase
to be compatible with LLMWerewolf's AgentProtocol interface.
"""
import re
import asyncio
from typing import Any, Optional, Type

from pydantic import BaseModel, Field
from openai import RateLimitError

# 使用AgentScope原生的Msg类
from agentscope.message import Msg as AgentScopeMsg

from llm_werewolf.agents.base import BaseAgent
from llm_werewolf.core.decisions import (
    SpeechDecision,
    extract_public_text,
    is_valid_public_speech,
)
from llm_werewolf.adapter.structured_invoke import unwrap_structured_metadata
from llm_werewolf.adapter.message import MessageAdapter, Msg
from llm_werewolf.adapter.prompts import RolePrompts, PlanStrategies
from llm_werewolf.adapter.serial_calls import run_serial_agent_call


class AgentScopeWerewolfAgent(BaseAgent):
    """Werewolf player agent for the AgentScope integration layer.

    This agent wraps AgentScope's AgentBase to work with LLMWerewolf's
    game engine while providing ReAct reasoning and better prompt management.
    """

    model: str = Field(default="agentscope")
    role: str = Field(default="villager")
    number: int = Field(default=1)
    plan: str = Field(default="自由发挥")
    plan_name: str = Field(default="default")
    game_role_name: str = Field(default="")
    language: str = Field(default="zh-TW")
    agentscope_agent: Any = Field(default=None, exclude=True)
    player_config: Any = Field(default=None, exclude=True)
    uses_structured_output: bool = Field(default=True, exclude=True)
    decision_history: list[str] = Field(default=[])
    chat_history: list[dict] = Field(default=[])

    def __init__(
        self,
        name: str,
        model: str = "agentscope",
        role: str = "villager",
        number: int = 1,
        plan: str = "自由发挥",
        plan_name: str = "default",
        language: str = "zh-TW",
        agentscope_agent: Any = None,
        player_config: Any = None,
    ):
        """Initialize the werewolf agent.

        Args:
            name: Player name.
            model: Model name.
            role: Role type (villager, prophet, witch, wolf, wolf_king, guard, hunter).
            number: Seat number (1-12).
            plan: Strategy plan text (resolved from plan_name after role assignment).
            plan_name: Plan strategy key (default, complicated, bold, ...).
            language: Response language.
            agentscope_agent: Pre-created AgentScope ReActAgent instance (optional).
            player_config: PlayerConfig used to build the ReActAgent after role assignment.
        """
        super().__init__(name=name, model=model)
        self.role = role
        self.number = number
        self.plan = plan
        self.plan_name = plan_name
        self.game_role_name = ""
        self.language = language
        self.player_config = player_config
        self.agentscope_agent = agentscope_agent
        self.decision_history = []
        self.chat_history = []
        if agentscope_agent is not None:
            self._init_system_prompt()

    def configure_role(
        self,
        seat_number: int,
        game_role_name: str,
        plan_text: str,
    ) -> None:
        """Apply role-specific system prompt after the engine assigns roles."""
        from llm_werewolf.adapter.factory import GAME_ROLE_TO_PROMPT_KEY, build_system_prompt, create_react_agent

        self.number = seat_number
        self.game_role_name = game_role_name
        self.role = GAME_ROLE_TO_PROMPT_KEY.get(game_role_name, "villager")
        self.plan = plan_text

        sys_prompt = build_system_prompt(seat_number, game_role_name, plan_text)
        if self.player_config is not None:
            self.agentscope_agent = create_react_agent(
                self.player_config,
                agent_name=self.name,
                sys_prompt=sys_prompt,
            )

        self.decision_history = []
        self.chat_history = []
        self._init_system_prompt()

    def _init_system_prompt(self) -> None:
        """Initialize local chat history mirror from role configuration."""
        if self.game_role_name:
            from llm_werewolf.adapter.factory import build_system_prompt

            sys_prompt = build_system_prompt(self.number, self.game_role_name, self.plan)
        else:
            role_config = self._get_role_config()
            sys_prompt = RolePrompts.BASE_PROMPT.format(
                number=self.number,
                role_name=role_config["role_name"],
                role_instruction=role_config["role_instruction"],
                suggestion=role_config["suggestion"],
                plan=self.plan,
            )

        self.chat_history = [{"role": "system", "content": sys_prompt}]

    def _get_role_config(self) -> dict:
        """Get role configuration."""
        role_map = {
            "villager": RolePrompts.VILLAGER,
            "prophet": RolePrompts.PROPHET,
            "witch": RolePrompts.WITCH,
            "wolf": RolePrompts.WOLF,
            "wolf_king": RolePrompts.WOLF_KING,
            "guard": RolePrompts.GUARD,
            "hunter": RolePrompts.HUNTER,
        }
        return role_map.get(self.role, RolePrompts.VILLAGER)

    @property
    def role_name(self) -> str:
        """Get role Chinese name."""
        return self._get_role_config()["role_name"]

    @property
    def is_wolf(self) -> bool:
        """Check if player is on werewolf team."""
        return self.role in ("wolf", "wolf_king")

    async def get_response(self, message: str) -> str:
        """Get response from the agent.

        This method adapts the AgentScope agent to LLMWerewolf's interface.

        Args:
            message: The prompt message from game engine.

        Returns:
            str: The agent's response.
        """
        self.chat_history.append({"role": "user", "content": message})

        if self.agentscope_agent is None:
            msg = f"AgentScope backend not initialized for player {self.name}"
            raise RuntimeError(msg)

        return await self._call_agentscope_agent(message)

    async def _call_agentscope_agent(self, message: str) -> str:
        """Call AgentScope agent for response (serialized across all 12 players).

        Args:
            message: The prompt message.

        Returns:
            str: The agent's response text.
        """
        input_msg = AgentScopeMsg(name="Moderator", content=message, role="user")
        response_text = ""
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                response_msg = await run_serial_agent_call(
                    lambda: self.agentscope_agent(input_msg)
                )
                response_text = self._extract_agentscope_text(response_msg)
                if not response_text:
                    response_text = self._generate_fallback_response(message, "空内容")
                last_error = None
                break
            except RateLimitError as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
            except Exception as exc:
                last_error = exc
                if "429" in str(exc) and attempt < 2:
                    await asyncio.sleep(2**attempt)
                    continue
                break

        if last_error is not None:
            response_text = self._generate_fallback_response(message, str(last_error))

        self.chat_history.append({"role": "assistant", "content": response_text})

        if self._message_expects_seat_only(message):
            extracted = self.extract_target(response_text)
            if extracted is not None:
                return f"[[{extracted}]]"
            match = re.search(r"\[\[\s*(\d+)\s*\]\]", response_text)
            if match:
                return f"[[{match.group(1)}]]"

        if "发言" in message or "SPEECH" in message or "演说" in message:
            return response_text.strip() or extract_public_text(response_text)
        return extract_public_text(response_text)

    async def get_structured_response(
        self,
        message: str,
        structured_model: Type[BaseModel],
    ) -> BaseModel | None:
        """Get a typed response from AgentScope when the backend supports it."""
        self.chat_history.append({"role": "user", "content": message})

        if self.agentscope_agent is None:
            msg = f"AgentScope backend not initialized for player {self.name}"
            raise RuntimeError(msg)

        input_msg = AgentScopeMsg(name="Moderator", content=message, role="user")
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                response_msg = await run_serial_agent_call(
                    lambda: self.agentscope_agent(
                        input_msg,
                        structured_model=structured_model,
                    )
                )
                metadata = unwrap_structured_metadata(
                    getattr(response_msg, "metadata", None)
                )
                if metadata:
                    try:
                        decision = structured_model.model_validate(metadata)
                    except Exception:
                        decision = structured_model.model_construct(**metadata)
                    self.chat_history.append(
                        {"role": "assistant", "content": decision.model_dump_json()}
                    )
                    return decision
                text = self._extract_agentscope_text(response_msg)
                if text.strip():
                    self.chat_history.append(
                        {"role": "assistant", "content": text}
                    )
                    if structured_model is SpeechDecision:
                        from llm_werewolf.adapter.bridge import WerewolfAdapterBridge

                        return WerewolfAdapterBridge.parse_speech(text)
                return None
            except RateLimitError as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
            except Exception as exc:
                last_error = exc
                if "429" in str(exc) and attempt < 2:
                    await asyncio.sleep(2**attempt)
                    continue
                break

        if last_error is not None:
            self.chat_history.append(
                {"role": "assistant", "content": f"structured_output_failed: {last_error}"}
            )
        return None

    @staticmethod
    def _extract_agentscope_text(response_msg: Any) -> str:
        """Normalize AgentScope Msg / raw response to plain text."""
        if hasattr(response_msg, "get_text_content"):
            return response_msg.get_text_content() or ""
        if hasattr(response_msg, "content"):
            content = response_msg.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                texts: list[str] = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            texts.append(block.get("text", ""))
                        elif "text" in block:
                            texts.append(block["text"])
                    elif isinstance(block, str):
                        texts.append(block)
                return "\n".join(texts)
            return str(content)
        return str(response_msg)

    def _generate_fallback_response(self, message: str, error: str) -> str:
        """Generate a fallback response when the agent fails.

        Args:
            message: The original prompt message.
            error: The error message.

        Returns:
            str: A reasonable fallback response.
        """
        import random

        if "YES" in message or "NO" in message or "0]]或[[1" in message or "表示否" in message:
            return random.choice(["[[0]]", "[[1]]"])

        if self._message_expects_seat_only(message):
            numbers = re.findall(r"(\d+)\s*号", message)
            seat = random.choice(numbers) if numbers else str(random.randint(1, 12))
            return f"[[{seat}]]"

        speeches = [
            "[[我觉得场上信息还不多，先听大家后面的发言再判断。]]",
            "[[我暂时没明确狼坑，但会重点看发言前后矛盾的人。]]",
            "[[我是好人，建议大家多盘逻辑，别被带节奏。]]",
            f"[[我是{self.role_name}，这局我会尽量帮好人理清局势。]]",
            "[[目前我没有铁狼，先观察投票和站队情况。]]",
        ]
        return random.choice(speeches)

    def add_decision(self, decision: str) -> None:
        """Add a decision to the decision history.

        Args:
            decision: A safe summary of the decision.
        """
        self.decision_history.append(decision)

    def get_decision_context(self) -> str:
        """Get formatted decision history for context.

        Returns:
            str: Formatted decision history.
        """
        if not self.decision_history:
            return ""
        return "\n\nYour previous actions:\n" + "\n".join(
            f"- {d}" for d in self.decision_history
        )

    def extract_target(self, text: str) -> Optional[int]:
        """Extract target number from [[...]] pattern.

        Args:
            text: The response text.

        Returns:
            Optional[int]: The extracted target number, or None.
        """
        match = re.search(r"\[\[\s*(\d+)\s*\]\]", text)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _message_expects_seat_only(message: str) -> bool:
        """True when the prompt asks for a seat number / vote, not a speech line."""
        markers = (
            "只回复",
            "只放座位号",
            "座位号",
            "全局座位号",
            "投票",
            "刀谁",
            "守谁",
            "验",
            "毒谁",
            "选择你要",
            "Vote for",
            "eliminate",
            "protect tonight",
            "check tonight",
            "WOLF_OPEN",
            "GUARD_ACTION",
            "PROPHET_ACTION",
            "WITCH_POISON_TARGET",
        )
        lowered = message.lower()
        if any(m in message for m in markers):
            return True
        if "vote" in lowered and "speech" not in lowered:
            return True
        if "发言" in message or "SPEECH" in message or "discussion" in lowered:
            return False
        return False

    def extract_content(self, text: str) -> Optional[str]:
        """Extract public speech from [[...]] (legacy helper)."""
        extracted = extract_public_text(text)
        if is_valid_public_speech(extracted):
            return extracted
        return None

    def reset(self) -> None:
        """Reset agent state."""
        self.decision_history = []
        self.chat_history = []
        self._init_system_prompt()
