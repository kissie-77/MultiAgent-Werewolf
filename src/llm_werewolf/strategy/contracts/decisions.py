"""智能体与引擎通信的类型化决策模型。

每个模型对应 AgentScope ReActAgent.reply(structured_model=...)，
该调用会注册 ``generate_response`` 工具；校验后的 kwargs 写入 Msg.metadata。
"""

import re
from typing import Literal

from pydantic import Field, BaseModel, field_validator

# 圆桌 / 警长 / 遗言等公开发言的最小长度。
SPEECH_PUBLIC_MIN_CHARS = 15
_SPEECH_MIN_CHARS = SPEECH_PUBLIC_MIN_CHARS

# [[...]] 内纯座位号 / 是或否标记不算公开发言。
_SEAT_ONLY_PATTERN = re.compile(r"^\d{1,2}$")

# 解析失败时产生的占位字符串 — 不得视为真实发言。
_EMPTY_SPEECH_MARKERS = ("（无公开发言）", "无公开发言")

_INCOMPLETE_SPEECH_ENDINGS = (
    "，",
    "、",
    "：",
    "；",
    ",",
    ":",
    ";",
    "往",
    "把",
    "将",
    "向",
    "对",
    "给",
    "让",
    "从",
    "和",
    "跟",
    "与",
    "但",
    "但是",
    "如果",
    "所以",
    "而且",
    "并且",
    "同时",
    "比如",
    "例如",
    "然后",
)


def generate_response_instruction(
    schema_name: str,
    *,
    information_isolation: bool = False,
    allow_legacy_scalar: bool = False,
) -> str:
    """返回与具体结构化 Schema 绑定的 generate_response 约束。

    Args:
        allow_legacy_scalar: 为 True 时允许 [[数字]] / YES/NO 等旧格式回退
            （用于 SeatChoiceDecision 等简单标量决策，避免与 agent_base.md 的
            [[座位号]] 指令冲突）。
    """
    parts = [
        (
            "【输出方式】优先调用 generate_response 提交 JSON；"
            "如果当前运行环境没有真实工具调用能力，则直接输出一个 JSON 对象。"
            f"两种方式的字段都必须严格遵守 {schema_name} Schema。"
        ),
    ]
    if allow_legacy_scalar:
        parts.append(
            "也接受 [[数字]] 或 YES/NO 等简写格式，系统会自动解析。"
        )
    else:
        parts.append(
            "禁止用 [[数字]]、[[...]] 或裸文本代替 structured 字段。不要输出解释、Markdown 代码块或额外自然语言。"
        )
    if information_isolation:
        parts.append(
            "【信息隔离】由系统决定谁能听到你的发言，你只需填写 "
            "public_speech / private_thought，不要指定听众或可见范围。"
        )
    return "".join(parts)


GENERATE_RESPONSE_INSTRUCTION = generate_response_instruction(
    "SpeechDecision", information_isolation=True
)


def speech_schema_instruction() -> str:
    """提示块：与 SpeechDecision（generate_response）绑定的输出要求。"""
    return "\n".join([
        "【本任务输出 — 仅 SpeechDecision Schema】",
        "必须调用 generate_response，字段：",
        f"- public_speech (string, 必填): 完整中文公开发言，≥{SPEECH_PUBLIC_MIN_CHARS} 字；",
        "  不得仅为座位号、不得为「无公开发言」类占位。",
        "- private_thought (string, 可选): 仅自己可见的推理，不会广播。",
        "禁止用 [[...]] / {...} 代替上述字段。",
        GENERATE_RESPONSE_INSTRUCTION,
    ])


class VoteIntentionDecision(BaseModel):
    """声明的白天投票意向，用于回放（非正式投票）。"""

    seat: int = Field(
        ...,
        ge=0,
        description=(
            "Global seat of the player you would vote to exile if voting now; "
            "0 = no clear intention / undecided."
        ),
    )
    reason: str | None = Field(
        default=None, description="Private rationale; not broadcast to other players."
    )


class SeatChoiceDecision(BaseModel):
    """夜间技能 / 投票：选择一个座位（允许时可填 0 表示跳过）。"""

    seat: int = Field(
        ...,
        ge=0,
        description="Global seat number of the target player. Use 0 only when skip is allowed.",
    )
    reason: str | None = Field(
        default=None, description="Private rationale; not shown to other players."
    )


class MultiSeatChoiceDecision(BaseModel):
    """选择多个不重复的座位（如盗贼 / 丘比特）。"""

    seats: list[int] = Field(
        ..., min_length=1, description="List of distinct global seat numbers."
    )
    reason: str | None = Field(default=None, description="Private rationale.")


class SpeechDecision(BaseModel):
    """白天讨论 / 警长发言 / 遗言 / 狼人夜间私聊。"""

    public_speech: str = Field(
        ...,
        min_length=SPEECH_PUBLIC_MIN_CHARS,
        description=(
            "Full public speech in Chinese (complete sentences, not a seat number). "
            f"At least {SPEECH_PUBLIC_MIN_CHARS} characters."
        ),
    )
    private_thought: str | None = Field(
        default=None, description="Private reasoning; not broadcast to other players."
    )
    self_explode: bool = Field(
        default=False,
        description="White Wolf only: self-destruct during day speech; skip voting and enter night.",
    )

    @field_validator("public_speech")
    @classmethod
    def validate_public_speech(cls, value: str) -> str:
        cleaned = value.strip()
        if not is_valid_public_speech(cleaned, min_chars=SPEECH_PUBLIC_MIN_CHARS):
            msg = (
                f"public_speech must be a real Chinese speech (≥{SPEECH_PUBLIC_MIN_CHARS} chars), "
                "not a seat number or placeholder."
            )
            raise ValueError(msg)
        return cleaned


class YesNoDecision(BaseModel):
    """女巫药水是/否及类似二元选择。"""

    choice: bool = Field(..., description="true = yes / use; false = no / skip")
    reason: str | None = Field(default=None, description="Private rationale.")


class WitchNightDecision(BaseModel):
    """狼刀结算后女巫的夜间回合（救 / 毒 / 不行动）。"""

    action: Literal["save", "poison", "none"] = Field(
        ..., description="save=use antidote on tonight's wolf victim; poison=use poison; none=skip"
    )
    seat: int = Field(
        default=0,
        ge=0,
        description="Global seat number when action=poison; use 0 for save or none",
    )
    reason: str | None = Field(default=None, description="Private rationale.")


def vote_intention_schema_instruction() -> str:
    """VoteIntentionDecision 的提示块（仅分析，非正式投票）。"""
    return "\n".join([
        "【本任务输出 — 仅 VoteIntentionDecision Schema】",
        "必须调用 generate_response，字段：",
        "- seat (integer, 必填): 若此刻正式投票会放逐的全局座位号；",
        "  尚无明确意向或观望则 seat=0（无投票意向）。",
        "- reason (string): 若 seat 与上一帧不同则必填；否则建议填写简要依据。",
        "这是投票意向采集，不是正式投票；禁止 SpeechDecision、禁止长段公开发言。",
        generate_response_instruction("VoteIntentionDecision"),
    ])


def seat_choice_schema_instruction(*, allow_skip: bool = False, require_reason: bool = False) -> str:
    """SeatChoiceDecision 的提示块（投票 / 夜间目标）。"""
    skip_line = (
        "不行动或弃票时 seat=0。" if allow_skip else "必须选择有效目标，seat 为全局座位号。"
    )
    reason_line = (
        "- reason (string, 必填): 私人推理，说明选该目标或弃票的理由，不广播。"
        if require_reason
        else "- reason (string, 可选): 私人推理，不广播。"
    )
    return "\n".join([
        "【本任务输出 — 仅 SeatChoiceDecision Schema】",
        "必须调用 generate_response，字段：",
        "- seat (integer, 必填): 目标玩家的全局座位号（数字，不是列表序号）；",
        f"  {skip_line}",
        reason_line,
        "禁止 SpeechDecision、禁止 [[...]] 长段发言、禁止 public_speech 字段。",
        generate_response_instruction("SeatChoiceDecision"),
    ])


def witch_night_schema_instruction(*, can_save: bool) -> str:
    """WitchNightDecision 的提示块。"""
    victim_line = (
        "你可以选择：save（救该刀口）、poison（毒杀某人）、none（不行动）。"
        if can_save
        else "你不能选择 save。可选择：poison（毒杀某人）、none（不行动）。"
    )
    return "\n".join([
        "【本任务输出 — 仅 WitchNightDecision Schema】",
        "必须调用 generate_response，字段：",
        "- action (string): save | poison | none；",
        "- seat (integer): action=poison 时填毒药目标全局座位号；save/none 时填 0；",
        f"- {victim_line}",
        "- reason (string, 可选): 私人推理。",
        "禁止 SpeechDecision。",
        generate_response_instruction("WitchNightDecision"),
    ])


class BeliefEntry(BaseModel):
    """玩家信念矩阵中的单个单元格（B1）。"""

    target_seat: int = Field(..., ge=1, description="Observed player seat")
    wolf_probability: float = Field(..., ge=0.0, le=1.0)
    reason: str | None = Field(
        default=None,
        description="Required when submitting a belief update in MindStateDecision.",
    )
    note: str | None = Field(default=None)


class SecondOrderEntry(BaseModel):
    """B2：我认为 observer 怀疑我是狼的概率。"""

    observer_seat: int = Field(..., ge=1, description="Other player seat")
    suspects_me_as_wolf: float = Field(..., ge=0.0, le=1.0)
    reason: str | None = Field(
        default=None,
        description="Required when submitting a B2 update in MindStateDecision.",
    )
    note: str | None = Field(default=None)


class GodRoleDelta(BaseModel):
    target_seat: int = Field(..., ge=1)
    delta: dict[str, float] = Field(default_factory=dict)
    reason: str | None = None


class ExposureRadarDelta(BaseModel):
    wolf_seat: int = Field(..., ge=1)
    observer_seat: int = Field(..., ge=1)
    suspicion: float = Field(..., ge=0.0, le=1.0)
    reason: str | None = Field(
        default=None,
        description="Required when submitting an exposure radar update.",
    )


class WolfCampDelta(BaseModel):
    """狼队共享面板增量（仅狼人填写）。"""

    god_role_intel: list[GodRoleDelta] = Field(default_factory=list)
    exposure_radar: list[ExposureRadarDelta] = Field(default_factory=list)


class MindStateDecision(BaseModel):
    """投票意向 + 一阶/二阶信念 + 可选狼队增量，一次 generate_response 提交。"""

    seat: int = Field(
        ...,
        ge=0,
        description="Vote intention seat; 0 = no clear target.",
    )
    reason: str | None = Field(default=None)
    first_order: list[BeliefEntry] = Field(default_factory=list)
    second_order: list[SecondOrderEntry] = Field(default_factory=list)
    wolf_camp_delta: WolfCampDelta | None = Field(default=None)


class BeliefMatrixDecision(BaseModel):
    """Deprecated: use MindStateDecision.first_order instead."""

    beliefs: list[BeliefEntry] = Field(default_factory=list)


def mind_state_schema_instruction() -> str:
    """MindStateDecision 的提示块（投票意向 + 信念矩阵）。"""
    return "\n".join([
        "【本任务输出 — 仅 MindStateDecision Schema】",
        "必须调用 generate_response，字段：",
        "- seat (integer, 必填): 若此刻正式投票会放逐的全局座位号；无明确意向填 0；",
        "- reason (string): 若 seat 与上一帧不同则必填；否则可选；",
        "- first_order (array): 仅需修改的 B1 条目（无变化则 []），",
        "  每项含 target_seat、wolf_probability(0~1)、reason(必填)；",
        "- second_order (array): 仅需修改的 B2 条目（无变化则 []），",
        "  每项含 observer_seat、suspects_me_as_wolf(0~1)、reason(必填)；",
        "- wolf_camp_delta (object, 可选, 仅狼人): 仅需修改的 god_role_intel / exposure_radar 增量；",
        "  每项增量必须含 reason；",
        "这是投票意向 + 信念增量更新，不是正式投票；禁止 SpeechDecision。",
        generate_response_instruction("MindStateDecision"),
    ])


def _nonempty_reason(value: str | None) -> bool:
    return bool(value and value.strip())


def validate_mind_state_decision(
    decision: MindStateDecision,
    *,
    previous_vote_seat: int | None,
) -> list[str]:
    """Validate partial belief updates and vote-intention change reasons."""
    errors: list[str] = []
    if previous_vote_seat is not None and decision.seat != previous_vote_seat:
        if not _nonempty_reason(decision.reason):
            errors.append("变更投票意向时必须填写顶层 reason")

    for entry in decision.first_order:
        if not _nonempty_reason(entry.reason):
            errors.append(f"first_order 座位 {entry.target_seat} 的修改必须填写 reason")

    for entry in decision.second_order:
        if not _nonempty_reason(entry.reason):
            errors.append(f"second_order 座位 {entry.observer_seat} 的修改必须填写 reason")

    if decision.wolf_camp_delta is not None:
        for delta in decision.wolf_camp_delta.god_role_intel:
            if not _nonempty_reason(delta.reason):
                errors.append(f"wolf_camp_delta.god_role_intel 座位 {delta.target_seat} 必须填写 reason")
        for delta in decision.wolf_camp_delta.exposure_radar:
            if not _nonempty_reason(delta.reason):
                errors.append(
                    "wolf_camp_delta.exposure_radar "
                    f"({delta.wolf_seat}←{delta.observer_seat}) 必须填写 reason"
                )
    return errors


def validate_seat_choice_reason(decision: SeatChoiceDecision) -> list[str]:
    if _nonempty_reason(decision.reason):
        return []
    return ["正式投票必须填写 reason"]


def metadata_looks_like_wrong_schema_for_speech(metadata: dict) -> bool:
    """拒绝被误当作 SpeechDecision 的 SeatChoice / YesNo 载荷。"""
    if not metadata:
        return True
    if metadata.get("public_speech"):
        return False
    return bool("seat" in metadata or "seats" in metadata or "choice" in metadata)


def looks_like_kill_or_vote_format(text: str) -> bool:
    """文本为夜间刀口 / 投票标记而非讨论发言时返回 True。"""
    stripped = text.strip()
    if not stripped:
        return True
    if looks_like_seat_only(stripped):
        return True
    if re.fullmatch(r"\[\[\s*\d+\s*\]\]", stripped):
        return True
    if re.fullmatch(r"刀\s*\d+\s*号?", stripped):
        return True
    return bool(re.fullmatch(r"刀\s*\d+", stripped) and len(stripped) <= 8)


def looks_like_seat_only(text: str) -> bool:
    """文本仅为座位号 / 是或否标记而非发言行时返回 True。"""
    stripped = text.strip()
    if not stripped:
        return True
    if _SEAT_ONLY_PATTERN.fullmatch(stripped):
        return True
    return bool(len(stripped) <= 3 and stripped.isdigit())


def looks_like_truncated_speech(text: str) -> bool:
    """文本停在连接词、方向词或半截标点时，视为被截断的发言。"""
    stripped = re.sub(r"\s+", "", text).strip()
    if not stripped:
        return True
    return stripped.endswith(_INCOMPLETE_SPEECH_ENDINGS)


def is_valid_public_speech(text: str, *, min_chars: int = _SPEECH_MIN_CHARS) -> bool:
    """提取的文本是否可用作白天讨论 / 公开发言。"""
    stripped = text.strip()
    if any(marker in stripped for marker in _EMPTY_SPEECH_MARKERS):
        return False
    if len(stripped) < min_chars:
        return False
    if looks_like_seat_only(stripped):
        return False
    if looks_like_truncated_speech(stripped):
        return False
    return not looks_like_kill_or_vote_format(stripped)


def extract_public_text(response: str) -> str:
    """从模型响应中提取可公开发表的发言。

    选取最长的非纯座位号 [[...]] 块；若模型将真实发言放在 {{}} / [[...]] 外，
    则回退到其中的散文文本。
    """
    if not response or not response.strip():
        return "（无公开发言）"

    bracket_blocks = [
        block.strip()
        for block in re.findall(r"\[\[\s*(.+?)\s*\]\]", response, flags=re.S)
        if block.strip()
    ]
    speech_blocks = [
        b
        for b in bracket_blocks
        if not looks_like_seat_only(b) and not looks_like_kill_or_vote_format(b)
    ]
    if speech_blocks:
        return max(speech_blocks, key=len)

    without_private = re.sub(r"\{[^{}]*\}", "", response, flags=re.S)
    without_brackets = re.sub(r"\[\[.*?\]\]", "", without_private, flags=re.S)
    cleaned = re.sub(r"\s+", " ", without_brackets).strip()
    if is_valid_public_speech(cleaned):
        return cleaned

    return "（无公开发言）"


def normalize_speech_decision(
    decision: SpeechDecision, *, raw_fallback: str | None = None
) -> SpeechDecision:
    """必要时用原始模型输出修复纯座位号或空的 public_speech。"""
    raw = raw_fallback or ""
    if is_valid_public_speech(decision.public_speech):
        return decision

    repaired = extract_public_text(raw)
    if is_valid_public_speech(repaired):
        return SpeechDecision(public_speech=repaired, private_thought=decision.private_thought)

    return SpeechDecision.model_construct(
        public_speech="（无公开发言）", private_thought=decision.private_thought
    )
