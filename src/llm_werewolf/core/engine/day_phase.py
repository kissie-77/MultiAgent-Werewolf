"""Day phase logic for the game engine."""

from collections.abc import Callable

from llm_werewolf.adapter.prompts import GamePrompts
from llm_werewolf.core.types import EventType, GamePhase, PlayerProtocol
from llm_werewolf.core.locale import Locale
from llm_werewolf.core.game_state import GameState
from llm_werewolf.adapter.visibility import VisibilityChannel


class DayPhaseMixin:
    """Mixin for handling day phase logic."""

    game_state: GameState | None
    locale: Locale
    _log_event: Callable
    build_player_observation: Callable[[PlayerProtocol], str]
    information_hub: object

    def _build_discussion_context(self, player: PlayerProtocol) -> str:
        """Build context for day discussion.

        Args:
            player: The player who will speak.

        Returns:
            str: Context message for the player's agent.
        """
        if not self.game_state:
            return ""

        context_parts = [
            self.build_player_observation(player, include_visible_events=True, include_private_notes=True),
        ]

        # Include player's decision history (safe, no sensitive info)
        if player.agent:
            decision_context = player.agent.get_decision_context()
            if decision_context:
                context_parts.append(decision_context)

        context_parts.append("")
        context_parts.append(GamePrompts.SPEECH_PROMPT)
        context_parts.append("请用 1–3 句话发言，遵守系统提示中的输出格式。")

        return "\n".join(context_parts)

    async def run_day_phase(self) -> list[str]:
        """Execute the day discussion phase.

        Returns:
            list[str]: Messages from the day phase.
        """
        if not self.game_state:
            msg = "Game not initialized"
            raise RuntimeError(msg)

        messages = []
        self.game_state.set_phase(GamePhase.DAY_DISCUSSION)

        # Narrator: Daybreak
        self._log_event(
            EventType.MESSAGE, self.locale.get("narrator_daybreak"), data={"action": "daybreak"}
        )

        self._log_event(
            EventType.PHASE_CHANGED,
            self.locale.get("day_begins", round_number=self.game_state.round_number),
            data={"phase": "day", "round": self.game_state.round_number},
        )

        messages.append("")

        if self.game_state.night_deaths:
            for player_id in self.game_state.night_deaths:
                player = self.game_state.get_player(player_id)
                if player:
                    messages.append(f"{player.name} was killed last night.")
        else:
            messages.append("No one died last night.")

        messages.append("\n--- Discussion Phase ---")
        alive_players = self.game_state.get_alive_players()

        await self.information_hub.announce(
            self.locale.get("day_begins", round_number=self.game_state.round_number),
            channel=VisibilityChannel.PUBLIC,
            audience=alive_players,
            phase="day",
            round_number=self.game_state.round_number,
        )

        def _on_day_speech(speaker, decision, _routed) -> None:
            speech = decision.public_speech.strip()
            self._log_event(
                EventType.PLAYER_SPEECH,
                self.locale.get("player_speech", player=speaker.name, speech=speech),
                data={
                    "player_id": speaker.player_id,
                    "player_name": speaker.name,
                    "speech": speech,
                    "private_thought": decision.private_thought,
                },
            )
            messages.append(self.locale.get("player_speech", player=speaker.name, speech=speech))

        try:
            await self.information_hub.run_roundtable(
                alive_players,
                channel=VisibilityChannel.PUBLIC,
                audience=alive_players,
                context_builder=self._build_discussion_context,
                instruction="发表 1–3 句完整中文发言，写在 [[...]] 中，不要只写座位号。",
                phase="day",
                round_number=self.game_state.round_number,
                opening_announcement="--- Discussion Phase ---",
                on_speech=_on_day_speech,
            )
        except Exception as e:
            self._log_event(
                EventType.ERROR,
                self.locale.get("speech_failed", player="all", error=str(e)),
                data={"error": str(e)},
            )
            messages.append(self.locale.get("speech_failed", player="all", error=str(e)))

        return messages
