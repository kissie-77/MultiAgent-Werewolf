"""AgentScope Agent 适配器，用于 LLMWerewolf 集成。

本模块封装 AgentScope 的 AgentBase，
使其符合 LLMWerewolf 的 AgentProtocol 接口。
"""
import re
import asyncio
from typing import Any, Optional, Type

from pydantic import BaseModel, Field
from openai import RateLimitError

# 使用AgentScope原生的Msg类
from agentscope.message import Msg as AgentScopeMsg

from llm_werewolf.agent_team.base import BaseAgent
from llm_werewolf.strategy.decisions import (
    SpeechDecision,
    extract_public_text,
    is_valid_public_speech,
)
from llm_werewolf.agent_team.structured_invoke import unwrap_structured_metadata
from llm_werewolf.agent_team.message import MessageAdapter, Msg
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.agent_team.serial_calls import run_serial_agent_call


class AgentScopeWerewolfAgent(BaseAgent):
    """AgentScope 集成层的狼人杀玩家 Agent。

    封装 AgentScope 的 AgentBase，对接 LLMWerewolf 游戏引擎，
    并提供 ReAct 推理与更完善的 prompt 管理。
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
    show_agent_raw: bool = Field(default=False, exclude=True)
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
        """初始化狼人杀 Agent。

        Args:
            name: 玩家名称。
            model: 模型名称。
            role: 角色类型（villager、prophet、witch、wolf、wolf_king、guard、hunter）。
            number: 座位号（1–12）。
            plan: 策略计划文本（角色分配后由 plan_name 解析）。
            plan_name: 策略键（default、complicated、bold 等）。
            language: 回复语言。
            agentscope_agent: 预创建的 AgentScope ReActAgent（可选）。
            player_config: 角色分配后用于构建 ReActAgent 的 PlayerConfig。
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
        """引擎分配角色后应用角色专属系统 prompt。"""
        from llm_werewolf.agent_team.factory import GAME_ROLE_TO_PROMPT_KEY, build_system_prompt, create_react_agent

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
                show_console_output=self.show_agent_raw,
            )

        self.decision_history = []
        self.chat_history = []
        self._init_system_prompt()


    def bind_role_prompt(
        self,
        role_name: str,
        seat_number: int,
        plan: str | None = None,
    ) -> None:
        """协作者 API：在 ``setup_game`` 之后绑定引擎分配的角色。"""
        plan_text = plan if plan is not None else self.plan
        self.configure_role(
            seat_number=seat_number,
            game_role_name=role_name,
            plan_text=plan_text,
        )

    def _init_system_prompt(self) -> None:
        """根据角色配置初始化本地对话历史镜像。"""
        if self.game_role_name:
            sys_prompt = PromptManager.build_role_strategy_prompt(
                self.number,
                self.game_role_name,
                self.plan,
            )
        else:
            sys_prompt = PromptManager.build_prompt_key_strategy_prompt(
                self.number,
                self.role,
                self.plan,
            )

        self.chat_history = [{"role": "system", "content": sys_prompt}]

    def _get_role_config(self) -> dict:
        """获取角色配置。"""
        return PromptManager.get_role_strategy_config(self.role)

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
            message: 游戏引擎下发的 prompt。

        Returns:
            str: Agent 的回复文本。
        """
        self.chat_history.append({"role": "user", "content": message})

        if self.agentscope_agent is None:
            msg = f"AgentScope backend not initialized for player {self.name}"
            raise RuntimeError(msg)

        return await self._call_agentscope_agent(message)

    async def _call_agentscope_agent(self, message: str) -> str:
        """调用 AgentScope Agent 获取回复（12 名玩家串行调用）。

        Args:
            message: prompt 消息。

        Returns:
            str: Agent 的回复文本。
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
                elif not self._message_expects_seat_only(message):
                    if not is_valid_public_speech(extract_public_text(response_text)):
                        response_text = self._generate_fallback_response(
                            message, "invalid_speech"
                        )
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
        """在后端支持时从 AgentScope 获取结构化类型回复。"""
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
                text = self._extract_agentscope_text(response_msg)
                metadata = unwrap_structured_metadata(
                    getattr(response_msg, "metadata", None)
                )
                if metadata:
                    if structured_model is SpeechDecision:
                        from llm_werewolf.strategy.decisions import (
                            metadata_looks_like_wrong_schema_for_speech,
                        )

                        if metadata_looks_like_wrong_schema_for_speech(metadata):
                            metadata = None
                    if metadata:
                        try:
                            decision = structured_model.model_validate(metadata)
                        except Exception:
                            decision = structured_model.model_construct(**metadata)
                        if structured_model is SpeechDecision:
                            from llm_werewolf.strategy.decisions import normalize_speech_decision

                            decision = normalize_speech_decision(
                                decision,
                                raw_fallback=text or decision.model_dump_json(),
                            )
                            if (
                                not is_valid_public_speech(decision.public_speech)
                                and text.strip()
                            ):
                                from llm_werewolf.agent_team.bridge import (
                                    WerewolfAdapterBridge,
                                )

                                decision = WerewolfAdapterBridge.parse_speech(text)
                        self.chat_history.append(
                            {"role": "assistant", "content": decision.model_dump_json()}
                        )
                        return decision
                if text.strip():
                    self.chat_history.append(
                        {"role": "assistant", "content": text}
                    )
                    if structured_model is SpeechDecision:
                        from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge

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
        """将 AgentScope Msg / 原始响应规范为纯文本。"""
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
        """Agent 失败时生成兜底回复。

        Args:
            message: 原始 prompt。
            error: 错误信息。

        Returns:
            str: 合理的兜底回复。
        """
        import random

        if "YES" in message or "NO" in message or "0]]或[[1" in message or "表示否" in message:
            return random.choice(["[[0]]", "[[1]]"])

        if self._message_expects_seat_only(message):
            seat = self._pick_seat_from_message(message) or random.randint(1, 12)
            lowered = message.lower()
            if "only the number" in lowered or "responding with only the number" in lowered:
                return str(seat)
            return f"[[{seat}]]"

        if self._is_werewolf_private_chat(message):
            return self._werewolf_team_fallback_speech(message)

        speeches = [
            "[[我觉得场上信息还不多，先听大家后面的发言再判断。]]",
            "[[我暂时没明确狼坑，但会重点看发言前后矛盾的人。]]",
            "[[建议大家多盘逻辑，别被带节奏。]]",
            f"[[我会结合票型和发言继续观察，先重点看可疑位置。]]",
            "[[目前我没有铁狼，先观察投票和站队情况。]]",
        ]
        return random.choice(speeches)

    @staticmethod
    def _pick_seat_from_message(message: str) -> int | None:
        """从 prompt 中选择一个出现过的座位号。"""
        import random

        numbers = re.findall(r"(\d+)\s*号", message)
        if not numbers:
            numbers = re.findall(r"^\s*(\d+)\.\s+", message, flags=re.M)
        if numbers:
            return int(random.choice(numbers))
        return None

    @staticmethod
    def _is_werewolf_private_chat(message: str) -> bool:
        """狼队夜间私聊 prompt 返回 True。"""
        lowered = message.lower()
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
        return any(marker in lowered or marker in message for marker in markers)

    def _werewolf_team_fallback_speech(self, message: str) -> str:
        """狼队私聊用的简短协调话术，避免公开身份式表达。"""
        import random

        seat = self._pick_seat_from_message(message) or random.randint(1, 12)
        english = sum(1 for char in message if ord(char) < 128) / max(len(message), 1) > 0.6
        if english:
            options = [
                f"I suggest we focus on {seat} tonight; the pressure looks useful.",
                f"Let's align on {seat} and avoid splitting the vote.",
                f"{seat} stood out earlier, so that can be our primary option.",
            ]
        else:
            options = [
                f"今晚可以先压一下{seat}号，收益比较稳定。",
                f"我建议先对齐{seat}号，避免票型分散。",
                f"{seat}号前面的表现值得优先处理。",
            ]
        return random.choice(options)

    def add_decision(self, decision: str) -> None:
        """将一条决策记入决策历史。

        Args:
            decision: 决策的安全摘要。
        """
        self.decision_history.append(decision)

    def get_decision_context(self) -> str:
        """获取格式化的决策历史作为上下文。

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
            Optional[int]: 解析出的座位号，无则 None。
        """
        match = re.search(r"\[\[\s*(\d+)\s*\]\]", text)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _message_expects_seat_only(message: str) -> bool:
        """prompt 要求座位号/投票而非发言时返回 True。"""
        from llm_werewolf.strategy.phase_outputs import ROUNDTABLE_SPEECH_ONLY_MARKER

        if ROUNDTABLE_SPEECH_ONLY_MARKER in message:
            return False
        if "【本阶段禁止】" in message and "SpeechDecision" in message:
            return False
        lowered = message.lower()
        if "发言" in message or "SPEECH" in message or "discussion" in lowered:
            return False
        if "演说" in message or "公开发言" in message or "public_speech" in lowered:
            return False

        markers = (
            "只回复",
            "只放座位号",
            "座位号",
            "全局座位号",
            "投票意向",
            "VoteIntentionDecision",
            "投票",
            "刀谁",
            "守谁",
            "验",
            "毒谁",
            "选择你要",
            "Vote for",
            "eliminate",
            "select a target",
            "available targets",
            "only the number",
            "protect tonight",
            "check tonight",
            "WOLF_OPEN",
            "GUARD_ACTION",
            "PROPHET_ACTION",
            "WITCH_POISON_TARGET",
        )
        if any(m in message for m in markers):
            return True
        if "vote" in lowered and "speech" not in lowered:
            return True
        return False

    def extract_content(self, text: str) -> Optional[str]:
        """从 [[...]] 提取公开发言（遗留辅助方法）。"""
        extracted = extract_public_text(text)
        if is_valid_public_speech(extracted):
            return extracted
        return None

    def reset(self) -> None:
        """重置 Agent 状态。"""
        self.decision_history = []
        self.chat_history = []
        self._init_system_prompt()
