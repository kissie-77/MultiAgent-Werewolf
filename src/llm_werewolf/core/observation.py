from __future__ import annotations

from pydantic import BaseModel, Field

from llm_werewolf.core.types import Event, GameStateInfo, PlayerInfo, PlayerProtocol


class PlayerObservation(BaseModel):
    """Filtered game context visible to a single player."""

    self_player: PlayerInfo = Field(..., description="Public identity and status of the acting player")
    game_state: GameStateInfo = Field(..., description="Public game-state summary")
    visible_players: list[PlayerInfo] = Field(
        default_factory=list,
        description="Publicly visible player information for all players",
    )
    visible_events: list[Event] = Field(
        default_factory=list,
        description="Events this player is allowed to observe",
    )
    private_notes: list[str] = Field(
        default_factory=list,
        description="Role-specific private facts only this player may know",
    )


class ObservationBuilder:
    """Builds player-specific views under strict information isolation."""

    def build(
        self,
        player: PlayerProtocol,
        game_state: GameStateInfo,
        all_players: list[PlayerProtocol],
        visible_events: list[Event],
        private_notes: list[str] | None = None,
    ) -> PlayerObservation:
        return PlayerObservation(
            self_player=player.get_public_info(),
            game_state=game_state,
            visible_players=[other.get_public_info() for other in all_players],
            visible_events=visible_events,
            private_notes=private_notes or [],
        )

    def format_for_prompt(
        self,
        observation: PlayerObservation,
        include_visible_events: bool = True,
        include_private_notes: bool = True,
    ) -> str:
        lines = [
            f"You are {observation.self_player.name}.",
            f"Current phase: {observation.game_state.phase.value}",
            f"Current round: {observation.game_state.round_number}",
            (
                "Alive summary: "
                f"{observation.game_state.alive_players}/{observation.game_state.total_players} alive, "
                f"werewolves alive: {observation.game_state.werewolves_alive}, "
                f"villagers alive: {observation.game_state.villagers_alive}"
            ),
            "",
            "Visible players:",
        ]

        for info in observation.visible_players:
            status = "alive" if info.is_alive else "dead"
            lines.append(f"- {info.name} ({info.player_id}): {status}")

        if include_visible_events and observation.visible_events:
            lines.extend(["", "Visible event history:"])
            for event in observation.visible_events:
                lines.append(f"- [{event.phase} R{event.round_number}] {event.message}")

        if include_private_notes and observation.private_notes:
            lines.extend(["", "Private notes:"])
            for note in observation.private_notes:
                lines.append(f"- {note}")

        return "\n".join(lines)
