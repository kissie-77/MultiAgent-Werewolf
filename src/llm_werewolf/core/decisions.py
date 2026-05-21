"""Typed decision models for agent-to-engine communication."""

import re

from pydantic import BaseModel, Field


class SeatChoiceDecision(BaseModel):
    """A target choice expressed as a player seat number."""

    seat: int = Field(..., ge=0, description="Player seat number; 0 means skip when allowed")
    reason: str | None = Field(default=None, description="Optional private rationale")
    raw_response: str | None = Field(default=None, description="Original model response, if available")


class SpeechDecision(BaseModel):
    """Separated public speech and private thought."""

    public_speech: str = Field(..., min_length=1, description="Speech visible to other players")
    private_thought: str | None = Field(default=None, description="Private reasoning, not public")
    raw_response: str | None = Field(default=None, description="Original model response, if available")


class YesNoDecision(BaseModel):
    """A boolean decision from an agent."""

    choice: bool = Field(..., description="True for yes, False for no")
    reason: str | None = Field(default=None, description="Optional private rationale")
    raw_response: str | None = Field(default=None, description="Original model response, if available")


class BeliefEntry(BaseModel):
    """Single cell in a player belief matrix (future MetaMind integration)."""

    target_seat: int = Field(..., ge=1, description="Observed player seat")
    wolf_probability: float = Field(..., ge=0.0, le=1.0)
    note: str | None = Field(default=None)


class BeliefMatrixDecision(BaseModel):
    """Structured belief update; parsed via WerewolfAdapterBridge when wired."""

    beliefs: list[BeliefEntry] = Field(default_factory=list)
    raw_response: str | None = Field(default=None)


def extract_public_text(response: str) -> str:
    """Extract text that is safe to publish from a model response."""
    bracketed = re.search(r"\[\[\s*(.+?)\s*\]\]", response, flags=re.S)
    if bracketed:
        return bracketed.group(1).strip()

    without_private = re.sub(r"\{.*?\}", "", response, flags=re.S).strip()
    return without_private or "（无公开发言）"
