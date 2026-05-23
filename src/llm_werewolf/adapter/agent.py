"""AgentScope Agent 适配器，用于 LLMWerewolf 集成。

本模块提供将 AgentScope 的 AgentBase 封装为
与 LLMWerewolf AgentProtocol 接口兼容的适配器。
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
    """AgentScope 集成层的狼人杀玩家 Agent。

    封装 AgentScope 的 AgentBase，与 LLMWerewolf 游戏引擎协作，
    并提供 ReAct 推理与更完善的 prompt 管理。
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
        """初始化狼人杀 Agent。

        Args:
            name: 玩家名称。
            model: 模型名称。
            role: 角色类型（villager、prophet、witch、wolf、wolf_king、guard、hunter）。
            number: 座位号（1-12）。
            plan: 策略计划。
            language: 回复语言。
            agentscope_agent: 预创建的 AgentScope AgentBase 实例。
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
        """根据角色配置初始化系统 prompt。"""
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
        """获取角色配置。"""
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
        """获取角色中文名。"""
        return self._get_role_config()["role_name"]

    @property
    def is_wolf(self) -> bool:
        """判断玩家是否属于狼人阵营。"""
        return self.role in ("wolf", "wolf_king")

    async def get_response(self, message: str) -> str:
        """从 Agent 获取回复。

        将 AgentScope Agent 适配为 LLMWerewolf 接口。

        Args:
            message: 游戏引擎下发的 prompt 消息。

        Returns:
            str: Agent 的回复文本。
        """
        self.chat_history.append({"role": "user", "content": message})

        if self.agentscope_agent is not None:
            return await self._call_agentscope_agent(message)
        else:
            return await self._call_direct_model(message)

    async def _call_agentscope_agent(self, message: str) -> str:
        """调用 AgentScope Agent 获取回复。

        Args:
            message: prompt 消息。

        Returns:
            str: Agent 回复文本。
        """
        # 使用AgentScope原生的Msg类
        input_msg = AgentScopeMsg(name="Moderator", content=message, role="user")

        try:
            print(f"[API调用] {self.name} 正在调用API...")
            response_msg = await self.agentscope_agent(input_msg)
            print(f"[API调用] {self.name} API调用成功")

            # 兼容 Msg 对象与原始响应
            if hasattr(response_msg, 'get_text_content'):
                response_text = response_msg.get_text_content() or ""
            elif hasattr(response_msg, 'content'):
                content = response_msg.content
                if isinstance(content, str):
                    response_text = content
                elif isinstance(content, list):
                    # 从 content 块中提取文本
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
            # API 调用失败时的兜底回复
            print(f"[API失败] {self.name} 调用失败: {e}")
            import traceback
            traceback.print_exc()
            response_text = self._generate_fallback_response(message, str(e))

        self.chat_history.append({"role": "assistant", "content": response_text})

        return response_text

    def _generate_fallback_response(self, message: str, error: str) -> str:
        """Agent 失败时生成兜底回复。

        兜底文本不得暴露阵营或身份（例如不说「我是好人/狼人」）。
        狼队夜间私聊使用队内协调话术，不得伪装村民身份。

        Args:
            message: 原始 prompt 消息。
            error: 错误信息。

        Returns:
            str: 合理的兜底回复。
        """
        import random

        lower = message.lower()

        # 是否为是/否类问题
        if (
            "ONLY 'YES' or 'NO'" in message
            or "respond with ONLY 'YES' or 'NO'" in message
            or "0]]或[[1" in message
        ):
            return random.choice(["[[0]]", "[[1]]", "YES", "NO"])

        # 引擎选目标：仅返回数字
        if "responding with ONLY the number" in message or "select a target" in lower:
            seat = self._pick_seat_from_message(message)
            return str(seat) if seat is not None else "1"

        # [[ ]] 选目标/投票（adapter / 旧版 prompt）
        if "[[]]" in message or "编号" in message:
            seat = self._pick_seat_from_message(message)
            if seat is not None:
                return f"[[{seat}]]"
            return f"[[{random.randint(1, 12)}]]"

        if "投票" in message or "vote" in lower:
            seat = self._pick_seat_from_message(message)
            if seat is not None:
                return f"[[{seat}]]"
            return f"[[{random.randint(1, 12)}]]"

        if self._is_werewolf_private_chat(message):
            return self._werewolf_team_fallback_speech(message)

        return self._public_fallback_speech(message)

    @staticmethod
    def _pick_seat_from_message(message: str) -> int | None:
        """从 prompt 中选取提到的座位号（若有）。"""
        import random

        numbers = re.findall(r"(?:^|\s)(\d+)\s*号", message)
        if not numbers:
            numbers = re.findall(r"^\s*(\d+)\.\s+", message, flags=re.M)
        if numbers:
            return int(random.choice(numbers))
        return None

    @staticmethod
    def _is_werewolf_private_chat(message: str) -> bool:
        """prompt 为狼队夜间协调（非白天公开发言）时返回 True。"""
        lower = message.lower()
        markers = (
            "fellow werewolves",
            "werewolf team discussion",
            "coordinating with these werewolves",
            "working with these werewolves",
            "discuss with your fellow werewolves",
            ", a werewolf.",
            "all werewolves will vote",
            "狼人请睁眼",
            "你的另外三个队友",
        )
        return any(m in lower or m in message for m in markers)

    def _werewolf_team_fallback_speech(self, message: str) -> str:
        """狼队私聊用的简短协调话术；不暴露身份。"""
        import random

        seat = self._pick_seat_from_message(message) or random.randint(1, 12)
        english = sum(1 for c in message if ord(c) < 128) / max(len(message), 1) > 0.6
        if english:
            options = [
                f"I suggest we focus on {seat} tonight — low risk and good pressure.",
                f"Let's align on {seat}; we can revisit if the vote splits.",
                f"{seat} stood out yesterday — worth discussing as our primary option.",
            ]
        else:
            options = [
                f"今晚可以先压一下{seat}号，风险相对可控。",
                f"我和大家想法接近，{seat}号可以当作首选。",
                f"{seat}号昨天发言有点问题，值得我们先对齐。",
            ]
        return random.choice(options)

    def _public_fallback_speech(self, message: str) -> str:
        """白天讨论的中性兜底发言；不声称好人/狼人身份。"""
        import random

        seat = self._pick_seat_from_message(message) or random.randint(1, 12)
        english = sum(1 for c in message if ord(c) < 128) / max(len(message), 1) > 0.6
        if english:
            options = [
                f"Player {seat} felt off to me — worth more attention.",
                "I'll keep tracking who contradicts themselves in later rounds.",
                f"I'm not fully convinced by {seat}'s explanation yet.",
            ]
        else:
            options = [
                f"{seat}号的发言我还需要再听一轮。",
                f"我会多留意{seat}号和其他人的逻辑是否对得上。",
                "今天信息量不少，我先把疑点记一下，下一轮再对齐。",
            ]
        return random.choice(options)

    async def _call_direct_model(self, message: str) -> str:
        """不经过 AgentScope Agent 封装，直接调用模型。

        兼容用的兜底方法。

        Args:
            message: prompt 消息。

        Returns:
            str: Agent 回复文本。
        """
        return f"[[{self.number}]]"

    def add_decision(self, decision: str) -> None:
        """将一条决策记入决策历史。

        Args:
            decision: 决策的安全摘要。
        """
        self.decision_history.append(decision)

    def get_decision_context(self) -> str:
        """获取格式化的决策历史，供上下文使用。

        Returns:
            str: 格式化后的决策历史。
        """
        if not self.decision_history:
            return ""
        return "\n\nYour previous actions:\n" + "\n".join(
            f"- {d}" for d in self.decision_history
        )

    def extract_target(self, text: str) -> Optional[int]:
        """从 [[...]] 模式中解析目标座位号。

        Args:
            text: 回复文本。

        Returns:
            Optional[int]: 解析出的座位号，若无则 None。
        """
        match = re.search(r"\[\[\s*(\d+)\s*\]\]", text)
        if match:
            return int(match.group(1))
        return None

    def extract_content(self, text: str) -> Optional[str]:
        """从 [[...]] 模式中解析内容。

        Args:
            text: 回复文本。

        Returns:
            Optional[str]: 解析出的内容，若无则 None。
        """
        match = re.search(r"\[\[\s*(.+?)\s*\]\]", text, flags=re.S)
        if match:
            return match.group(1).strip()
        return None

    def reset(self) -> None:
        """重置 Agent 状态。"""
        self.decision_history = []
        self.chat_history = []
        self._init_system_prompt()
