"""Typed decision models for agent-to-engine communication.

Each model maps to AgentScope ReActAgent.reply(structured_model=...) which registers
the ``generate_response`` tool; validated kwargs land in Msg.metadata.
"""

import re

from pydantic import BaseModel, Field

# Minimum length for day discussion / sheriff speech (not seat-only tokens).
_SPEECH_MIN_CHARS = 6

# Pure seat / yes-no tokens inside [[...]] are not public speech.
_SEAT_ONLY_PATTERN = re.compile(r"^\d{1,2}$")

GENERATE_RESPONSE_INSTRUCTION = (
    "【输出方式】你必须调用 generate_response 工具提交 JSON，字段严格遵守上方 Schema。"
    "禁止用 [[数字]] 或自由文本代替结构化字段；reason / private_thought 可写在对应字段里。"
)


class SeatChoiceDecision(BaseModel):
    """Night skill / vote: pick one seat (0 = skip when allowed)."""

    seat: int = Field(
        ...,
        ge=0,
        description="Global seat number of the target player. Use 0 only when skip is allowed.",
    )
    reason: str | None = Field(
        default=None,
        description="Private rationale; not shown to other players.",
    )


class MultiSeatChoiceDecision(BaseModel):
    """Select multiple distinct seats (e.g. thief / cupid)."""

    seats: list[int] = Field(
        ...,
        min_length=1,
        description="List of distinct global seat numbers.",
    )
    reason: str | None = Field(default=None, description="Private rationale.")


class SpeechDecision(BaseModel):
    """Day discussion / sheriff speech / last words."""

    public_speech: str = Field(
        ...,
        min_length=1,
        description=(
            "Full public speech in Chinese (complete sentence, not a seat number). "
            "Must be at least 6 characters; prefer 10+ when using generate_response."
        ),
    )
    private_thought: str | None = Field(
        default=None,
        description="Private reasoning; not broadcast to other players.",
    )


class YesNoDecision(BaseModel):
    """Witch potion yes/no and similar binary choices."""

    choice: bool = Field(..., description="true = yes / use; false = no / skip")
    reason: str | None = Field(default=None, description="Private rationale.")


class BeliefEntry(BaseModel):
    """Single cell in a player belief matrix (future MetaMind integration)."""

    target_seat: int = Field(..., ge=1, description="Observed player seat")
    wolf_probability: float = Field(..., ge=0.0, le=1.0)
    note: str | None = Field(default=None)


class BeliefMatrixDecision(BaseModel):
    """Structured belief update; parsed via WerewolfAdapterBridge when wired."""

    beliefs: list[BeliefEntry] = Field(default_factory=list)


def looks_like_seat_only(text: str) -> bool:
    """True when text is only a seat number / yes-no token, not a speech line."""
    stripped = text.strip()
    if not stripped:
        return True
    if _SEAT_ONLY_PATTERN.fullmatch(stripped):
        return True
    if len(stripped) <= 3 and stripped.isdigit():
        return True
    return False


def is_valid_public_speech(text: str, *, min_chars: int = _SPEECH_MIN_CHARS) -> bool:
    """Whether extracted text is usable as day discussion / public speech."""
    stripped = text.strip()
    if len(stripped) < min_chars:
        return False
    if looks_like_seat_only(stripped):
        return False
    return True


def extract_public_text(response: str) -> str:
    """Extract publishable speech from a model response.

    Picks the longest [[...]] block that is not seat-only; falls back to prose
    outside {{}} / [[...]] when models put the real speech there.
    """
    if not response or not response.strip():
        return "（无公开发言）"

    bracket_blocks = [
        block.strip()
        for block in re.findall(r"\[\[\s*(.+?)\s*\]\]", response, flags=re.S)
        if block.strip()
    ]
    speech_blocks = [b for b in bracket_blocks if not looks_like_seat_only(b)]
    if speech_blocks:
        return max(speech_blocks, key=len)

    without_private = re.sub(r"\{[^{}]*\}", "", response, flags=re.S)
    without_brackets = re.sub(r"\[\[.*?\]\]", "", without_private, flags=re.S)
    cleaned = re.sub(r"\s+", " ", without_brackets).strip()
    if is_valid_public_speech(cleaned):
        return cleaned

    return "（无公开发言）"


def normalize_speech_decision(
    decision: SpeechDecision,
    *,
    raw_fallback: str | None = None,
) -> SpeechDecision:
    """Fix seat-only or empty public_speech using raw model output when needed."""
    raw = raw_fallback or ""
    if is_valid_public_speech(decision.public_speech):
        return decision

    repaired = extract_public_text(raw)
    if is_valid_public_speech(repaired):
        return SpeechDecision(
            public_speech=repaired,
            private_thought=decision.private_thought,
        )

    return SpeechDecision(
        public_speech="（无公开发言）",
        private_thought=decision.private_thought,
    )
