"""游戏引擎的白天阶段逻辑。"""

from collections import Counter
from collections.abc import Callable

from llm_werewolf.game_runtime.types import EventType, GamePhase, PlayerProtocol
from llm_werewolf.game_runtime.i18n.locale import Locale
from llm_werewolf.game_runtime.roles.names import RoleNames
from llm_werewolf.strategy.contracts.decisions import SpeechDecision
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
            from llm_werewolf.strategy.belief.format import append_working_memory_context

            append_working_memory_context(context_parts, player, include_belief=True)

        return "\n".join(context_parts)

    async def _handle_white_wolf_self_explosion(self, player: PlayerProtocol) -> None:
        """白狼王白天发言自爆：出局、可选带走一人，跳过投票直入黑夜。"""
        if not self.game_state or not player.is_alive():
            return

        player.kill()
        self.game_state.day_deaths.add(player.player_id)
        self.game_state.death_causes[player.player_id] = "self_explosion"

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("white_wolf_self_explodes", player=player.name),
            data={"player_id": player.player_id, "action": "self_explosion"},
        )

        self.game_state.death_abilities_used.add(player.player_id)
        await self._process_hunter_or_alpha_death(player)
        self.game_state.skip_day_voting = True

    def _log_public_speech(self, speaker: PlayerProtocol, decision: SpeechDecision) -> None:
        """记录白天发言；可见性为 PUBLIC（由引擎决定，而非 agent）。"""
        if not self.game_state:
            return
        from llm_werewolf.game_runtime.support.fallback_log import (
            merge_agent_decision_into_event_data,
        )

        event_data = merge_agent_decision_into_event_data(
            {
                "player_id": speaker.player_id,
                "player_name": speaker.name,
                "speech": decision.public_speech,
            },
            getattr(speaker, "agent", None),
        )
        self._log_event(
            event_type_for_channel(VisibilityChannel.PUBLIC),
            self.locale.get("player_speech", player=speaker.name, speech=decision.public_speech),
            data=event_data,
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
            self._log_event(
                EventType.MESSAGE,
                self.locale.get("peaceful_night"),
                data={"action": "night_result", "result": "peaceful_night"},
            )

        messages.append(opening_announcement)
        messages.append(self.locale.get("discussion_phase_separator"))

        alive_players = self.game_state.get_alive_players()
        interaction = self.game_state.require_phase_interaction()
        pending_self_explosion: dict[str, str | None] = {"player_id": None}

        def on_speech(speaker: PlayerProtocol, decision: SpeechDecision, _routed: object) -> None:
            self._log_public_speech(speaker, decision)
            if (
                speaker.get_role_name() == RoleNames.WHITE_WOLF
                and getattr(decision, "self_explode", False)
            ):
                pending_self_explosion["player_id"] = speaker.player_id
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

        exploded_id = pending_self_explosion.get("player_id")
        if exploded_id and self.game_state:
            exploded = self.game_state.get_player(exploded_id)
            if exploded is not None:
                await self._handle_white_wolf_self_explosion(exploded)

        return messages
