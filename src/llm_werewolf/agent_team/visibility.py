"""各游戏阶段信息隔离用的可见性通道。"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.player import Player


class VisibilityChannel(str, Enum):
    """可接收已路由 Agent 消息的受众类型。"""

    PUBLIC = "public"
    WOLF_TEAM = "wolf_team"
    PRIVATE = "private"
    CUSTOM = "custom"


class RoutedMessage(BaseModel):
    """拆分为公开发言与可选私人推理的消息。"""

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
    players: list[Player],
) -> list[str]:
    """解析可收听某通道的 player_id（仅存活玩家，不按 Agent 过滤）。"""
    from llm_werewolf.game_runtime.types import Camp

    alive = [p for p in players if p.is_alive()]
    if channel == VisibilityChannel.PUBLIC:
        return [p.player_id for p in alive]
    if channel == VisibilityChannel.WOLF_TEAM:
        return [p.player_id for p in alive if p.get_camp() == Camp.WEREWOLF]
    return [p.player_id for p in alive]
