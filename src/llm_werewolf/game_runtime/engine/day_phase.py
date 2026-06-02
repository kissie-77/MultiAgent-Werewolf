"""游戏引擎的白天阶段逻辑。"""

from collections import Counter
from collections.abc import Callable

from llm_werewolf.game_runtime.types import EventType, GamePhase, PlayerProtocol
from llm_werewolf.strategy.decisions import SpeechDecision
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.events.visibility import VisibilityChannel, event_type_for_channel


def _format_runtime_error(exc: Exception) -> str:
    """Return a non-empty error string for runtime event logs."""
    message = str(exc).strip()
    if message:
        return f"{type(exc).__name__}: {message}"
    return type(exc).__name__


def _is_human_player(player: PlayerProtocol) -> bool:
    return getattr(getattr(player, "agent", None), "model", "") == "human"


def _role_counts(players: list[PlayerProtocol]) -> dict[str, int]:
    counts = Counter(player.get_role_name() for player in players)
    return dict(sorted(counts.items()))


class DayPhaseMixin:
    """处理白天阶段逻辑的 Mixin。"""

    game_state: GameState | None
    locale: Locale
    _log_event: Callable
    build_player_observation: Callable[[PlayerProtocol], str]

    def _build_discussion_context(self, player: PlayerProtocol) -> str:
        """构建白天讨论的静态上下文；回合内发言使用 MsgHub 记忆。"""
        if not self.game_state:
            return ""

        context_parts = [
            self.build_player_observation(
                player,
                include_visible_events=True,
                include_private_notes=True,
                for_agent_decision=True,
            )
        ]

        if player.agent:
            decision_context = player.agent.get_decision_context()
            if decision_context:
                context_parts.append(decision_context)

        context_parts.append("")
        from llm_werewolf.game_runtime.prompts.actions import EngineContexts

        context_parts.append(EngineContexts.role_pool_note(_role_counts(self.game_state.players)))
        context_parts.append(EngineContexts.public_speech_information_boundary())
        context_parts.append(EngineContexts.day_discussion_prompt())

        if self.game_state.belief_log is not None and not _is_human_player(player):
            from llm_werewolf.strategy.belief_format import append_working_memory_context

            append_working_memory_context(context_parts, player, include_belief=True)

        return "\n".join(context_parts)

    def _log_public_speech(self, speaker: PlayerProtocol, decision: SpeechDecision) -> None:
        """记录白天发言；可见性为 PUBLIC（由引擎决定，而非 agent）。"""
        if not self.game_state:
            return
        self._log_event(
            event_type_for_channel(VisibilityChannel.PUBLIC),
            self.locale.get("player_speech", player=speaker.name, speech=decision.public_speech),
            data={
                "player_id": speaker.player_id,
                "player_name": speaker.name,
                "speech": decision.public_speech,
            },
            visible_to=None,
        )

    async def run_day_phase(self) -> list[str]:
        """通过 InformationHub 执行白天讨论阶段。"""
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
            data={"phase": GamePhase.DAY_DISCUSSION.value, "round": self.game_state.round_number},
        )

        messages.append("")

        if self.game_state.night_deaths:
            death_lines = "; ".join(
                self.locale.get("night_death_line", player=self.game_state.get_player(pid).name)
                for pid in self.game_state.night_deaths
                if self.game_state.get_player(pid)
            )
            opening_announcement = self.locale.get(
                "daybreak_announcement", death_lines=death_lines
            )
        else:
            opening_announcement = self.locale.get("peaceful_night_announcement")

        messages.append(opening_announcement)
        messages.append(self.locale.get("discussion_phase_separator"))

        alive_players = self.game_state.get_alive_players()
        interaction = self.game_state.require_phase_interaction()

        def on_speech(speaker: PlayerProtocol, decision: SpeechDecision, _routed: object) -> None:
            self._log_public_speech(speaker, decision)
            if speaker.agent and getattr(speaker.agent, "memory_manager", None):
                speaker.agent.memory_manager.add_public_speech(
                    speaker.name, decision.public_speech, self.game_state.round_number
                )
            messages.append(
                self.locale.get(
                    "player_speech", player=speaker.name, speech=decision.public_speech
                )
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
                instruction=self.locale.get("day_discussion_instruction"),
                phase=GamePhase.DAY_DISCUSSION.value,
                round_number=self.game_state.round_number,
                opening_announcement=opening_announcement,
                on_speech=on_speech,
                vote_intention_tracker=tracker,
                on_vote_intention_record=on_intention,
            )
        except Exception as exc:
            error_text = _format_runtime_error(exc)
            self._log_event(
                EventType.ERROR,
                self.locale.get("speech_failed", player="*", error=error_text),
                data={"error": error_text, "error_type": type(exc).__name__},
            )

        return messages
