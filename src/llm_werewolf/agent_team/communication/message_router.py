"""由引擎控制的路由：谁能听到什么在此决定，不由 Agent 自行决定。

Agent 仅产出发言（public_speech / private_thought）或接收消息；
Hub 在 ``MessageRouter`` 按游戏规则解析受众后再投递。
"""

from __future__ import annotations

from llm_werewolf.game_runtime.types import EventType, PlayerProtocol
from llm_werewolf.game_runtime.roles.names import participates_in_wolf_team
from llm_werewolf.game_runtime.events.visibility import (
    RoutedMessage,
    VisibilityChannel,
    event_type_for_channel,
)


class MessageRouter:
    """根据通道与游戏状态解析 MsgHub 参与者及 Event.visible_to。"""

    @staticmethod
    def resolve_audience_players(
        channel: VisibilityChannel,
        alive_players: list[PlayerProtocol],
        *,
        custom_audience: list[PlayerProtocol] | None = None,
        actor: PlayerProtocol | None = None,
    ) -> list[PlayerProtocol]:
        """返回在本通道上应听到下一条公开发言的存活玩家。"""
        if custom_audience is not None:
            return [p for p in custom_audience if p.is_alive()]
        if channel == VisibilityChannel.PRIVATE and actor is not None:
            return [actor] if actor.is_alive() else []
        ids = set(MessageRouter.resolve_audience_player_ids(channel, alive_players))
        return [p for p in alive_players if p.player_id in ids]

    @staticmethod
    def resolve_audience_player_ids(
        channel: VisibilityChannel, alive_players: list[PlayerProtocol]
    ) -> list[str]:
        if channel == VisibilityChannel.PUBLIC:
            return [p.player_id for p in alive_players if p.is_alive()]
        if channel == VisibilityChannel.WOLF_TEAM:
            return [
                p.player_id
                for p in alive_players
                if p.is_alive() and participates_in_wolf_team(p)
            ]
        return []

    @staticmethod
    def event_type_for_channel(channel: VisibilityChannel) -> EventType:
        return event_type_for_channel(channel)

    @staticmethod
    def visible_to_for_routed(
        routed: RoutedMessage, *, wolf_player_ids: list[str]
    ) -> list[str] | None:
        """将已路由的公开发言行映射为 Event.visible_to（None 表示全员可见）。"""
        if routed.channel == VisibilityChannel.PUBLIC:
            return None
        if routed.channel == VisibilityChannel.WOLF_TEAM:
            return list(wolf_player_ids)
        if routed.audience_player_ids:
            return list(routed.audience_player_ids)
        return []

    @staticmethod
    def wolf_player_ids(alive_players: list[PlayerProtocol]) -> list[str]:
        return [p.player_id for p in alive_players if participates_in_wolf_team(p)]
