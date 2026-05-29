"""AgentScope Agent 适配器，用于 LLMWerewolf 集成。

本模块封装 AgentScope 的 AgentBase，
使其符合 LLMWerewolf 的 AgentProtocol 接口。
"""

import logging

logging.getLogger("agentscope.formatter").setLevel(logging.ERROR)
import re
from typing import Any
import asyncio

from openai import RateLimitError
from pydantic import Field, BaseModel

# 使用AgentScope原生的Msg类
from agentscope.message import Msg as AgentScopeMsg

from llm_werewolf.strategy.decisions import (
    SpeechDecision,
    extract_public_text,
    is_valid_public_speech,
)
from llm_werewolf.agent_team.agents.base import BaseAgent
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.agent_team.invocation.serial_calls import run_serial_agent_call
from llm_werewolf.agent_team.invocation.structured_invoke import (
    parse_structured_from_text,
    unwrap_structured_metadata,
)

logger = logging.getLogger(__name__)


def _structured_tool_choice_unsupported(exc: Exception) -> bool:
    """Return True when a provider rejects forced structured tool choice."""
    text = str(exc).lower()
    return "tool_choice" in text and (
        "does not support" in text or "not support" in text or "unsupported" in text
    )


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
    prompt_version: str = Field(default="v2")
    game_role_name: str = Field(default="")
    language: str = Field(default="zh-TW")
    agentscope_agent: Any = Field(default=None, exclude=True)
    player_config: Any = Field(default=None, exclude=True)
    uses_structured_output: bool = Field(default=True, exclude=True)
    decision_history: list[str] = Field(default=[])
    chat_history: list[dict] = Field(default=[])
    memory_manager: Any = Field(default=None, exclude=True)

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
        prompt_version: str = "v2",
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
        self.prompt_version = prompt_version
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
        *,
        prompt_version: str | None = None,
    ) -> None:
        """引擎分配角色后应用角色专属系统 prompt。"""
        from llm_werewolf.agent_team.agents.factory import (
            GAME_ROLE_TO_PROMPT_KEY,
            create_react_agent,
            build_system_prompt,
        )

        if prompt_version is not None:
            self.prompt_version = prompt_version
        self.number = seat_number
        self.game_role_name = game_role_name
        self.role = GAME_ROLE_TO_PROMPT_KEY.get(game_role_name, "villager")
        self.plan = plan_text

        sys_prompt = build_system_prompt(
            seat_number, game_role_name, plan_text, prompt_version=self.prompt_version
        )
        if self.player_config is not None:
            self.agentscope_agent = create_react_agent(
                self.player_config, agent_name=self.name, sys_prompt=sys_prompt
            )

        self.decision_history = []
        self.chat_history = []
        self._init_system_prompt()

    def bind_role_prompt(
        self,
        role_name: str,
        seat_number: int,
        plan: str | None = None,
        *,
        prompt_version: str | None = None,
    ) -> None:
        """协作者 API：在 ``setup_game`` 之后绑定引擎分配的角色。"""
        plan_text = plan if plan is not None else self.plan
        self.configure_role(
            seat_number=seat_number,
            game_role_name=role_name,
            plan_text=plan_text,
            prompt_version=prompt_version or self.prompt_version,
        )

    def _init_system_prompt(self) -> None:
        """根据角色配置初始化本地对话历史镜像。"""
        from llm_werewolf.agent_team.agents.factory import build_system_prompt

        if self.game_role_name:
            sys_prompt = build_system_prompt(
                self.number, self.game_role_name, self.plan, prompt_version=self.prompt_version
            )
        else:
            sys_prompt = PromptManager.build_prompt_key_strategy_prompt(
                self.number, self.role, self.plan, prompt_version=self.prompt_version
            )
            from llm_werewolf.agent_team.skill_support.skill_loader import load_role_skills_text

            skills = load_role_skills_text(self.role)
            if skills:
                sys_prompt = f"{sys_prompt}\n\n{skills}"

        self.chat_history = [{"role": "system", "content": sys_prompt}]

    def _get_role_config(self) -> dict:
        """获取角色配置。"""
        return PromptManager.get_role_strategy_config(
            self.role, prompt_version=self.prompt_version
        )

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
                response_msg = self._sanitize_agentscope_response_msg(response_msg)
                response_text = self._extract_agentscope_text(response_msg)
                if not response_text:
                    response_text = self._generate_fallback_response(message, "空内容")
                elif not self._message_expects_seat_only(message):
                    if not is_valid_public_speech(extract_public_text(response_text)):
                        response_text = self._generate_fallback_response(message, "invalid_speech")
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
        self, message: str, structured_model: type[BaseModel]
    ) -> BaseModel | None:
        """在后端支持时从 AgentScope 获取结构化类型回复。"""
        self.chat_history.append({"role": "user", "content": message})

        if self.agentscope_agent is None:
            msg = f"AgentScope backend not initialized for player {self.name}"
            raise RuntimeError(msg)

        input_msg = AgentScopeMsg(name="Moderator", content=message, role="user")
        last_error: Exception | None = None

        def parse_text_decision(text: str) -> BaseModel | None:
            if not text.strip():
                return None
            if structured_model is SpeechDecision:
                self.chat_history.append({"role": "assistant", "content": text})
                from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge

                return WerewolfAdapterBridge.parse_speech(text)
            recovered = parse_structured_from_text(text, structured_model)
            if recovered is not None:
                self.chat_history.append({
                    "role": "assistant",
                    "content": recovered.model_dump_json(),
                })
                return recovered
            self.chat_history.append({"role": "assistant", "content": text})
            logger.warning(
                "structured_text_recovery_failed agent=%s model=%s text=%s",
                self.name,
                structured_model.__name__,
                text[:200],
            )
            return None

        for attempt in range(3):
            try:
                response_msg = await run_serial_agent_call(
                    lambda: self.agentscope_agent(input_msg, structured_model=structured_model)
                )
                response_msg = self._sanitize_agentscope_response_msg(response_msg)
                text = self._extract_agentscope_text(response_msg)
                metadata = unwrap_structured_metadata(getattr(response_msg, "metadata", None))
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
                                decision, raw_fallback=text or decision.model_dump_json()
                            )
                            if not is_valid_public_speech(decision.public_speech) and text.strip():
                                from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge

                                decision = WerewolfAdapterBridge.parse_speech(text)
                        self.chat_history.append({
                            "role": "assistant",
                            "content": decision.model_dump_json(),
                        })
                        return decision
                decision = parse_text_decision(text)
                if decision is not None:
                    return decision
                return None
            except RateLimitError as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
            except Exception as exc:
                last_error = exc
                if _structured_tool_choice_unsupported(exc):
                    try:
                        response_msg = await run_serial_agent_call(
                            lambda: self.agentscope_agent(input_msg)
                        )
                        text = self._extract_agentscope_text(response_msg)
                        decision = parse_text_decision(text)
                        if decision is not None:
                            return decision
                        return None
                    except Exception as plain_exc:
                        last_error = plain_exc
                        break
                if "429" in str(exc) and attempt < 2:
                    await asyncio.sleep(2**attempt)
                    continue
                break

        if last_error is not None:
            self.chat_history.append({
                "role": "assistant",
                "content": f"structured_output_failed: {last_error}",
            })
        return None

    @staticmethod
    def _sanitize_agentscope_response_msg(response_msg: Any) -> Any:
        """Strip thinking blocks from AgentScope content before any logging/broadcast reuse."""
        content = getattr(response_msg, "content", None)
        if not isinstance(content, list):
            return response_msg

        sanitized: list[Any] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "thinking":
                continue
            sanitized.append(block)
        response_msg.content = sanitized
        return response_msg

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
                        block_type = block.get("type", "")
                        if block_type == "thinking":
                            continue
                        if block_type == "text":
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
            seat = self._pick_seat_from_message(message)
            if seat is None:
                # 使用当前玩家座位号作为参考
                seat = max(1, min(self.number, 12))
            # 确保座位号在有效范围内
            seat = max(1, min(seat, 12))
            lowered = message.lower()
            if "only the number" in lowered or "responding with only the number" in lowered:
                return str(seat)
            return f"[[{seat}]]"

        # 狼队夜间私聊：用协调话术
        if self._is_werewolf_private_chat(message):
            return self._werewolf_team_fallback_speech(message)

        # 白天讨论发言：按角色生成有博弈性的推理发言
        role_key = self.role
        return self._generate_role_specific_fallback(role_key, message)

    def _generate_role_specific_fallback(self, role_key: str, message: str) -> str:
        """按角色生成有博弈性的白天讨论兜底发言。"""
        import random

        # 不再使用具体座位号，避免引用不存在的玩家
        # 判断游戏阶段（早期/中期）
        is_early = "第 1 轮" in message or "第 2 轮" in message or "round 1" in message.lower()

        fallbacks = {
            "villager": [
                "我觉得目前场上信息还不多，需要多听几轮发言才能判断。先观察大家的投票倾向和站队情况，重点关注那些发言模糊、回避关键问题的人。",
                "我暂时没找到铁狼，但会重点关注发言前后矛盾的人，以及投票时突然改变立场的玩家。建议大家多盘逻辑，别被带节奏。",
                "目前场上还没有明确的狼坑，但我会注意谁在无理由攻击好人，谁在刻意保护某些位置。我会结合票型和发言继续观察。",
                "现在局势还不明朗，我不急着站队。先听后面的发言，再根据投票结果做判断。我倾向于从发言最模糊的人开始排查。",
                "我会仔细听每个人的发言，看谁的逻辑站不住脚，谁的投票和发言不一致。好人要团结，别被狼人分化。",
            ],
            "prophet": [
                "我昨晚验了一个人，信息对我很重要，暂时不急着跳。但我会根据发言和投票来引导好人阵营的方向，建议大家多关注那些带节奏的人。",
                "我觉得场上需要有人站出来带队，我会重点关注那些发言有影响力的人。建议大家多盘逻辑，别被表面现象迷惑。",
                "我暂时不暴露身份，但我会通过逻辑分析来推动好人阵营的判断。重点关注那些回避查验话题、或者急于跳身份的人。",
                "我认为现在最重要的是找出狼人的刀法和策略。我会从发言逻辑和投票倾向入手，建议大家不要急于站队，多听几轮再做判断。",
            ],
            "witch": [
                "我手里有药，但不会轻易使用。首夜的情况需要谨慎判断，我会重点关注那些可能是自刀的狼人，以及发言明显有问题的人。",
                "我的解药和毒药都很关键，不能浪费。我会根据场上的死亡情况和发言来判断用药时机。建议大家多提供有用信息，帮助我做出正确决策。",
                "我觉得女巫的用药时机很关键，不能盲目。我会重点关注那些可能是狼刀目标的人，以及发言中暴露狼人身份的人。毒药会留给高置信目标。",
                "现在局势还不明朗，我的药要留给最关键的时刻。我会仔细分析每个玩家的发言和投票，确保用药收益最大化。",
            ],
            "wolf": [
                "我觉得前面有人的发言有些问题，逻辑上站不住脚。建议大家重点关注这个位置，我也怀疑他可能是狼人。",
                "目前场上信息不多，但我感觉有几个人的发言方向很奇怪。我会继续观察，重点关注那些带节奏和回避问题的人。",
                "我认为现在需要有人站出来分析局势，不能被动等待。我会从发言逻辑入手，找出那些可能是狼人的人。建议大家多盘逻辑。",
                "我觉得场上的局势有些混乱，需要理清思路。我会重点关注那些发言前后不一致的人，以及投票时突然改变立场的玩家。",
            ],
            "wolf_king": [
                "我觉得前面有人的表现值得关注，发言中有不少漏洞。建议大家多分析这个位置，我也怀疑他可能是关键角色。",
                "现在局势还不明朗，但我会主动出击，找出那些可能是狼人的人。重点关注发言模糊和投票异常的玩家。",
                "我认为需要有人带头分析局势，不能被动等待。我会从发言和投票两个维度入手，找出狼人的蛛丝马迹。",
                "我觉得场上有几个位置很可疑，但需要更多证据。我会继续观察，重点关注那些带节奏和回避关键问题的人。",
            ],
            "guard": [
                "我觉得需要保护那些发言有影响力的人，可能是神职位置。我会根据发言和投票来判断守护目标，确保好人阵营的关键角色存活。",
                "现在局势还不明朗，但我会重点关注那些可能是狼人刀口目标的人。建议大家多提供有用信息，帮助我做出正确判断。",
                "我认为守护的时机很关键，不能盲目。我会从发言逻辑和投票倾向入手，找出那些可能是好人阵营核心的人物。",
                "我会仔细分析每个玩家的发言，判断谁可能是神职、谁可能是狼人。守护选择要服务于好人阵营的整体利益。",
            ],
            "hunter": [
                "我暂时不暴露身份，但我会重点关注那些可能是狼人的位置。如果我被击杀，我会带走可疑的玩家。",
                "现在局势还不明朗，但我会保持警惕。重点关注那些发言有问题、投票异常的人，确保我临死时能带走真正的狼人。",
                "我认为猎人要隐藏好身份，同时积极分析局势。我会从发言和投票两个维度入手，找出狼人的蛛丝马迹，确保技能收益最大化。",
                "我觉得场上有几个位置很可疑，但需要更多证据。我会继续观察，确保临死开枪时能准确带走狼人，不带走好人。",
            ],
        }

        speeches = fallbacks.get(role_key, fallbacks["villager"])
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
        # 只匹配明确的狼人夜间行动关键词，避免误判白天讨论
        werewolf_action_markers = (
            "狼人请睁眼",
            "今晚你要刀谁",
            "选择击杀目标",
            "werewolf team discussion",
            "coordinating with these werewolves",
            "working with these werewolves",
            "discuss with your fellow werewolves",
            "all werewolves will vote",
        )
        return any(marker in lowered or marker in message for marker in werewolf_action_markers)

    def _werewolf_team_fallback_speech(self, message: str) -> str:
        """狼队私聊用的简短协调话术，避免公开身份式表达。"""
        import random

        # 从消息中获取座位号，限制在合理范围内（1-12）
        seat = self._pick_seat_from_message(message)
        if seat is None:
            # 使用当前玩家座位号作为参考，避免引用不存在的玩家
            seat = max(1, min(self.number, 12))
        # 确保座位号在有效范围内
        seat = max(1, min(seat, 12))

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
        if self.memory_manager:
            self.memory_manager.add_decision(decision)

    def get_decision_context(self) -> str:
        """获取格式化的决策历史作为上下文。

        Returns:
            str: 格式化后的决策历史。
        """
        if not self.decision_history:
            return ""
        return "\n\nYour previous actions:\n" + "\n".join(f"- {d}" for d in self.decision_history)

    def extract_target(self, text: str) -> int | None:
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
        """Prompt 要求座位号/投票而非发言时返回 True。"""
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
        return bool("vote" in lowered and "speech" not in lowered)

    def extract_content(self, text: str) -> str | None:
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
