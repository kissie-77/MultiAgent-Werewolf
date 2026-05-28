"""Visibility channels and routed message DTOs used by runtime phases."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from llm_werewolf.game_runtime.types import Camp, EventType, PlayerProtocol


class VisibilityChannel(str, Enum):
    """Audience type for routed in-game messages."""

    PUBLIC = "public"
    WOLF_TEAM = "wolf_team"
    PRIVATE = "private"
    CUSTOM = "custom"


class RoutedMessage(BaseModel):
    """Message split into public speech plus optional private reasoning."""

    speaker_seat: int = Field(..., ge=0, description="Global seat number (1-based when known)")
    speaker_player_id: str = Field(..., description="Engine player_id")
    speaker_name: str = Field(..., description="Display name")
    public_speech: str = Field(..., min_length=1, description="Text visible to channel audience")
    private_thought: str | None = Field(
        default=None,
        description="Inner monologue visible only to the speaker",
    )
    channel: VisibilityChannel = Field(..., description="Visibility channel for public_speech")
    phase: str = Field(default="", description="Game phase when message was produced")
    round_number: int = Field(default=0, description="Round when message was produced")
    audience_player_ids: list[str] = Field(
        default_factory=list,
        description="Resolved audience for CUSTOM or derived channels",
    )


def audience_for_channel(
    channel: VisibilityChannel,
    players: list[PlayerProtocol],
) -> list[str]:
    """Resolve player ids that can hear a channel, considering alive players only."""
    alive = [p for p in players if p.is_alive()]
    if channel == VisibilityChannel.PUBLIC:
        return [p.player_id for p in alive]
    if channel == VisibilityChannel.WOLF_TEAM:
        return [p.player_id for p in alive if p.get_camp() == Camp.WEREWOLF]
    return [p.player_id for p in alive]


def event_type_for_channel(channel: VisibilityChannel) -> EventType:
    """Map a visibility channel to the event type used by runtime logs."""
    if channel == VisibilityChannel.WOLF_TEAM:
        return EventType.PLAYER_DISCUSSION
    return EventType.PLAYER_SPEECH
