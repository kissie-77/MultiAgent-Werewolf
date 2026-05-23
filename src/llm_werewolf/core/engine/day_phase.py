"""Day phase logic for the game engine."""

from collections.abc import Callable

from llm_werewolf.adapter.message_router import MessageRouter
from llm_werewolf.adapter.visibility import VisibilityChannel
from llm_werewolf.core.decisions import SpeechDecision
from llm_werewolf.core.types import EventType, GamePhase, PlayerProtocol
from llm_werewolf.core.locale import Locale
from llm_werewolf.core.game_state import GameState


class DayPhaseMixin:
    """Mixin for handling day phase logic."""

    game_state: GameState | None
    locale: Locale
    _log_event: Callable
    build_player_observation: Callable[[PlayerProtocol], str]

    def _build_discussion_context(self, player: PlayerProtocol) -> str:
        """Build static context for day discussion; in-round speech uses MsgHub memory."""
        if not self.game_state:
            return ""

        context_parts = [
            self.build_player_observation(
                player,
                include_visible_events=True,
                include_private_notes=True,
                for_agent_decision=True,
            ),
        ]

        if player.agent:
            decision_context = player.agent.get_decision_context()
            if decision_context:
                context_parts.append(decision_context)

        context_parts.append("")
        from llm_werewolf.core.prompts.actions import EngineContexts

        context_parts.append(EngineContexts.day_discussion_prompt())
        return "\n".join(context_parts)

    def _log_public_speech(
        self,
        speaker: PlayerProtocol,
        decision: SpeechDecision,
    ) -> None:
        """Log day speech; visibility is PUBLIC (engine decides, not the agent)."""
        if not self.game_state:
            return
        self._log_event(
            MessageRouter.event_type_for_channel(VisibilityChannel.PUBLIC),
            self.locale.get("player_speech", player=speaker.name, speech=decision.public_speech),
            data={
                "player_id": speaker.player_id,
                "player_name": speaker.name,
                "speech": decision.public_speech,
            },
            visible_to=None,
        )

    async def run_day_phase(self) -> list[str]:
        """Execute the day discussion phase via InformationHub."""
        if not self.game_state:
            msg = "Game not initialized"
            raise RuntimeError(msg)

        messages: list[str] = []
        self.game_state.set_phase(GamePhase.DAY_DISCUSSION)

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

        messages.append("\n--- 讨论阶段 ---")
        alive_players = self.game_state.get_alive_players()
        interaction = self.game_state.require_phase_interaction()

        if self.game_state.night_deaths:
            death_lines = [
                f"{self.game_state.get_player(pid).name} 昨夜死亡"
                for pid in self.game_state.night_deaths
                if self.game_state.get_player(pid)
            ]
            opening_announcement = "天亮了。" + "；".join(death_lines) + "。请依次发表白天讨论发言。"
        else:
            opening_announcement = "天亮了，昨夜平安夜。请依次发表白天讨论发言。"

        def on_speech(
            speaker: PlayerProtocol,
            decision: SpeechDecision,
            _routed: object,
        ) -> None:
            self._log_public_speech(speaker, decision)
            messages.append(
                self.locale.get("player_speech", player=speaker.name, speech=decision.public_speech)
            )

        tracker = (
            self.game_state.vote_intention_tracker
            if self.game_state.track_vote_intentions
            else None
        )
        on_intention = self._log_vote_intention_record if tracker else None

        try:
            await interaction.run_roundtable(
                alive_players,
                channel=VisibilityChannel.PUBLIC,
                context_builder=self._build_discussion_context,
                instruction="",
                phase=GamePhase.DAY_DISCUSSION.value,
                round_number=self.game_state.round_number,
                opening_announcement=opening_announcement,
                on_speech=on_speech,
                vote_intention_tracker=tracker,
                on_vote_intention_record=on_intention,
            )
        except Exception as exc:
            self._log_event(
                EventType.ERROR,
                self.locale.get("speech_failed", player="*", error=str(exc)),
                data={"error": str(exc)},
            )

        return messages
