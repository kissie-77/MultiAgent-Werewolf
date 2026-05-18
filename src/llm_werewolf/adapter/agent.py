"""AgentScope Agent adapter for LLMWerewolf integration.

This module provides an adapter that wraps AgentScope's AgentBase
to be compatible with LLMWerewolf's AgentProtocol interface.
"""
import re
import asyncio
from typing import Any, Optional

from pydantic import Field

# 使用AgentScope原生的Msg类
from agentscope.message import Msg as AgentScopeMsg

from llm_werewolf.core.agent import BaseAgent
from llm_werewolf.adapter.message import MessageAdapter, Msg
from llm_werewolf.adapter.prompts import RolePrompts, PlanStrategies


class AgentScopeWerewolfAgent(BaseAgent):
    """Werewolf player agent adapted from werewolf_kills_agentscope project.

    This agent wraps AgentScope's AgentBase to work with LLMWerewolf's
    game engine while providing ReAct reasoning and better prompt management.
    """

    model: str = Field(default="agentscope")
    role: str = Field(default="villager")
    number: int = Field(default=1)
    plan: str = Field(default="自由发挥")
    language: str = Field(default="zh-TW")
    agentscope_agent: Any = Field(default=None, exclude=True)
    decision_history: list[str] = Field(default=[])
    chat_history: list[dict] = Field(default=[])

    def __init__(
        self,
        name: str,
        model: str = "agentscope",
        role: str = "villager",
        number: int = 1,
        plan: str = "自由发挥",
        language: str = "zh-TW",
        agentscope_agent: Any = None,
    ):
        """Initialize the werewolf agent.

        Args:
            name: Player name.
            model: Model name.
            role: Role type (villager, prophet, witch, wolf, wolf_king, guard, hunter).
            number: Seat number (1-12).
            plan: Strategy plan.
            language: Response language.
            agentscope_agent: Pre-created AgentScope AgentBase instance.
        """
        super().__init__(name=name, model=model)
        self.role = role
        self.number = number
        self.plan = plan
        self.language = language
        self.agentscope_agent = agentscope_agent
        self.decision_history = []
        self.chat_history = []
        self._init_system_prompt()

    def _init_system_prompt(self) -> None:
        """Initialize system prompt from role configuration."""
        role_config = self._get_role_config()

        sys_prompt = RolePrompts.BASE_PROMPT.format(
            number=self.number,
            role_name=role_config["role_name"],
            role_instruction=role_config["role_instruction"],
            suggestion=role_config["suggestion"],
            plan=self.plan,
        )

        self.chat_history.append({"role": "system", "content": sys_prompt})

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

        if self.agentscope_agent is not None:
            return await self._call_agentscope_agent(message)
        else:
            return await self._call_direct_model(message)

    async def _call_agentscope_agent(self, message: str) -> str:
        """Call AgentScope agent for response.

        Args:
            message: The prompt message.

        Returns:
            str: The agent's response text.
        """
        # 使用AgentScope原生的Msg类
        input_msg = AgentScopeMsg(name="Moderator", content=message, role="user")

        try:
            print(f"[API调用] {self.name} 正在调用API...")
            response_msg = await self.agentscope_agent(input_msg)
            print(f"[API调用] {self.name} API调用成功")

            # Handle both Msg objects and raw responses
            if hasattr(response_msg, 'get_text_content'):
                response_text = response_msg.get_text_content() or ""
            elif hasattr(response_msg, 'content'):
                content = response_msg.content
                if isinstance(content, str):
                    response_text = content
                elif isinstance(content, list):
                    # Extract text from content blocks
                    texts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                texts.append(block.get("text", ""))
                            elif "text" in block:
                                texts.append(block["text"])
                        elif isinstance(block, str):
                            texts.append(block)
                    response_text = "\n".join(texts)
                else:
                    response_text = str(content)
            else:
                response_text = str(response_msg)

            if not response_text:
                print(f"[API警告] {self.name} API返回空内容，使用fallback")
                response_text = self._generate_fallback_response(message, "空内容")

            # 调用完成后等待3秒，避免触发速率限制
            print(f"[API等待] {self.name} 等待3秒...")
            await asyncio.sleep(3)

        except Exception as e:
            # Fallback response when API call fails
            print(f"[API失败] {self.name} 调用失败: {e}")
            import traceback
            traceback.print_exc()
            response_text = self._generate_fallback_response(message, str(e))

        self.chat_history.append({"role": "assistant", "content": response_text})

        return response_text

    def _generate_fallback_response(self, message: str, error: str) -> str:
        """Generate a fallback response when the agent fails.

        Args:
            message: The original prompt message.
            error: The error message.

        Returns:
            str: A reasonable fallback response.
        """
        import random

        # Check if it's a yes/no question
        if "YES" in message or "NO" in message or "0]]或[[1" in message:
            return random.choice(["[[0]]", "[[1]]"])

        # Check if it's a target selection
        if "[[]]" in message or "编号" in message or "select" in message.lower():
            # Extract available numbers from message
            numbers = re.findall(r'(\d+)\s*号', message)
            if numbers:
                return f"[[{random.choice(numbers)}]]"
            return f"[[{random.randint(1, 12)}]]"

        # Check if it's a vote
        if "投票" in message or "vote" in message.lower():
            return f"[[{random.randint(0, 12)}]]"

        # Default speech response
        speeches = [
            f"我认为{random.randint(1, 12)}号玩家很可疑",
            f"我觉得我是好人，我会好好分析局势",
            f"我建议大家多关注一下发言不自然的玩家",
            f"我是{self.role_name}，我会尽力帮助大家",
            f"我觉得我们应该团结起来找出狼人",
        ]
        return random.choice(speeches)

    async def _call_direct_model(self, message: str) -> str:
        """Call model directly without AgentScope agent wrapper.

        This is a fallback method for compatibility.

        Args:
            message: The prompt message.

        Returns:
            str: The agent's response text.
        """
        return f"[[{self.number}]]"

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

    def extract_content(self, text: str) -> Optional[str]:
        """Extract content from [[...]] pattern.

        Args:
            text: The response text.

        Returns:
            Optional[str]: The extracted content, or None.
        """
        match = re.search(r"\[\[\s*(.+?)\s*\]\]", text, flags=re.S)
        if match:
            return match.group(1).strip()
        return None

    def reset(self) -> None:
        """Reset agent state."""
        self.decision_history = []
        self.chat_history = []
        self._init_system_prompt()
