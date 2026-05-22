"""Engine-controlled routing: who hears what is decided here, not by agents.

Agents only produce speech (public_speech / private_thought) or receive messages
that the Hub delivers after ``MessageRouter`` resolves the audience from game rules.
"""

from __future__ import annotations

from llm_werewolf.adapter.visibility import RoutedMessage, VisibilityChannel, audience_for_channel
from llm_werewolf.core.types import Camp, EventType, PlayerProtocol


class MessageRouter:
    """Resolve MsgHub participants and Event.visible_to from channel + game state."""

    @staticmethod
    def resolve_audience_players(
        channel: VisibilityChannel,
        alive_players: list[PlayerProtocol],
        *,
        custom_audience: list[PlayerProtocol] | None = None,
        actor: PlayerProtocol | None = None,
    ) -> list[PlayerProtocol]:
        """Return alive players who should hear the next public line on this channel."""
        if custom_audience is not None:
            return [p for p in custom_audience if p.is_alive()]
        if channel == VisibilityChannel.PRIVATE and actor is not None:
            return [actor] if actor.is_alive() else []
        ids = set(
            MessageRouter.resolve_audience_player_ids(channel, alive_players)
        )
        return [p for p in alive_players if p.player_id in ids]

    @staticmethod
    def resolve_audience_player_ids(
        channel: VisibilityChannel,
        alive_players: list[PlayerProtocol],
    ) -> list[str]:
        if channel == VisibilityChannel.PUBLIC:
            return [p.player_id for p in alive_players if p.is_alive()]
        if channel == VisibilityChannel.WOLF_TEAM:
            return [
                p.player_id
                for p in alive_players
                if p.is_alive() and p.get_camp() == Camp.WEREWOLF
            ]
        return [p.player_id for p in alive_players if p.is_alive()]

    @staticmethod
    def event_type_for_channel(channel: VisibilityChannel) -> EventType:
        if channel == VisibilityChannel.WOLF_TEAM:
            return EventType.PLAYER_DISCUSSION
        return EventType.PLAYER_SPEECH

    @staticmethod
    def visible_to_for_routed(
        routed: RoutedMessage,
        *,
        wolf_player_ids: list[str],
    ) -> list[str] | None:
        """Map a routed public line to Event.visible_to (None = everyone)."""
        if routed.channel == VisibilityChannel.PUBLIC:
            return None
        if routed.channel == VisibilityChannel.WOLF_TEAM:
            return list(wolf_player_ids)
        if routed.audience_player_ids:
            return list(routed.audience_player_ids)
        return None

    @staticmethod
    def wolf_player_ids(alive_players: list[PlayerProtocol]) -> list[str]:
        return [
            p.player_id
            for p in alive_players
            if p.is_alive() and p.get_camp() == Camp.WEREWOLF
        ]
