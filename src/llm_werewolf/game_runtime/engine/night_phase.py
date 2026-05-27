"""游戏引擎的夜晚阶段逻辑。"""

import random
from typing import TYPE_CHECKING
from collections.abc import Callable

from llm_werewolf.game_runtime.events.visibility import VisibilityChannel, event_type_for_channel
from llm_werewolf.strategy.decisions import SpeechDecision
from llm_werewolf.game_runtime.types import Camp, EventType, GamePhase, PlayerProtocol
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.night_scheduler import NightSkillScheduler
from llm_werewolf.game_runtime.prompts.actions import EngineContexts
from llm_werewolf.game_runtime.roles.names import participates_in_wolf_team
from llm_werewolf.game_runtime.registries.role_night_plans import offer_blood_moon_transform
from llm_werewolf.game_runtime.roles.werewolf import BloodMoonApostle

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.actions.base import Action


class NightPhaseMixin:
    """处理夜晚阶段逻辑的 Mixin。"""

    game_state: GameState | None
    locale: Locale
    _log_event: Callable
    process_actions: Callable
    resolve_deaths: Callable
    build_player_observation: Callable
    build_shared_observation: Callable

    def _build_werewolf_discussion_context(self, werewolf: PlayerProtocol) -> str:
        """静态狼队上下文；局内狼队频道讨论使用 MsgHub 记忆。"""
        if not self.game_state:
            return ""

        werewolves = [
            p for p in self.game_state.get_alive_players() if participates_in_wolf_team(p)
        ]
        werewolves_for_obs = [werewolf] + [
            w for w in werewolves if w.player_id != werewolf.player_id
        ]
        possible_targets = [
            p for p in self.game_state.get_alive_players() if p.get_camp() != Camp.WEREWOLF
        ]
        werewolf_names = [w.name for w in werewolves]
        target_names = [p.name for p in possible_targets]

        shared = self.build_shared_observation(
            werewolves_for_obs,
            additional_notes=EngineContexts.werewolf_coordination_note(
                werewolf_names, target_names
            ),
            include_visible_events=True,
            for_agent_decision=True,
        )
        return shared + "\n" + EngineContexts.werewolf_discussion(
            werewolf.name,
            self.game_state.round_number,
            werewolf_names,
            target_names,
            "",
        )

    def _log_werewolf_speech(
        self,
        speaker: PlayerProtocol,
        decision: SpeechDecision,
    ) -> None:
        if not self.game_state:
            return
        wolf_ids = [
            p.player_id
            for p in self.game_state.get_alive_players()
            if participates_in_wolf_team(p)
        ]
        self._log_event(
            event_type_for_channel(VisibilityChannel.WOLF_TEAM),
            self.locale.get(
                "werewolf_discussion", player=speaker.name, speech=decision.public_speech
            ),
            data={
                "player_id": speaker.player_id,
                "player_name": speaker.name,
                "speech": decision.public_speech,
                "role": "Werewolf",
            },
            visible_to=wolf_ids,
        )

    async def _resolve_blood_moon_transforms(self) -> None:
        """其余狼人全灭时，询问未变身血月使徒是否变身（仅其本人可见）。"""
        if not self.game_state:
            return
        interaction = self.game_state.require_phase_interaction()
        for player in self.game_state.get_alive_players():
            if not isinstance(player.role, BloodMoonApostle):
                continue
            if player.role.transformed:
                continue
            transformed = await offer_blood_moon_transform(
                player.role, self.game_state, interaction
            )
            if transformed:
                self._log_event(
                    EventType.MESSAGE,
                    self.locale.get(
                        "blood_moon_transformed",
                        player=player.name,
                    ),
                    data={"player_id": player.player_id, "action": "blood_moon_transform"},
                    visible_to=[player.player_id],
                )

    async def _run_werewolf_discussion(self) -> list[str]:
        """经 Hub 进行狼队讨论；仅狼人可听（引擎路由）。"""
        if not self.game_state:
            return []

        messages: list[str] = []
        werewolves = [
            p for p in self.game_state.get_alive_players() if participates_in_wolf_team(p)
        ]

        if len(werewolves) <= 1:
            return messages

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_wake"),
            data={"action": "werewolves_wake"},
        )

        possible_targets = [
            p for p in self.game_state.get_alive_players() if p.get_camp() != Camp.WEREWOLF
        ]
        if not possible_targets:
            return messages

        target_names = [p.name for p in possible_targets]
        interaction = self.game_state.require_phase_interaction()

        def on_speech(
            speaker: PlayerProtocol,
            decision: SpeechDecision,
            _routed: object,
        ) -> None:
            self._log_werewolf_speech(speaker, decision)
            messages.append(f"🐺 {speaker.name}: {decision.public_speech}")

        try:
            await interaction.run_roundtable(
                werewolves,
                channel=VisibilityChannel.WOLF_TEAM,
                context_builder=self._build_werewolf_discussion_context,
                instruction="",
                phase=GamePhase.NIGHT.value,
                round_number=self.game_state.round_number,
                audience=werewolves,
                opening_announcement=self.locale.get(
                    "werewolf_wake_opening", targets=", ".join(target_names)
                ),
                on_speech=on_speech,
            )
        except Exception as exc:
            self._log_event(
                EventType.ERROR,
                self.locale.get("discussion_failed", player="*", error=str(exc)),
                data={"error": str(exc)},
            )

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_vote"),
            data={"action": "werewolves_vote"},
        )

        return messages

    def _resolve_werewolf_votes(self) -> list[str]:
        """结算狼队投票以确定刀口目标。"""
        if not self.game_state:
            return []

        messages: list[str] = []

        if not self.game_state.werewolf_votes:
            self._log_event(
                EventType.MESSAGE,
                self.locale.get("werewolf_no_votes", round_number=self.game_state.round_number),
                data={"action": "werewolf_no_votes", "round": self.game_state.round_number},
            )
            return messages

        vote_counts: dict[str, int] = {}
        for target_id in self.game_state.werewolf_votes.values():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

        max_votes = max(vote_counts.values())
        candidates = [pid for pid, count in vote_counts.items() if count == max_votes]

        if candidates:
            selected_target_id = random.choice(candidates)  # noqa: S311
            self.game_state.werewolf_target = selected_target_id

            target = self.game_state.get_player(selected_target_id)
            if target:
                self._log_event(
                    EventType.WEREWOLF_KILLED,
                    self.locale.get("werewolf_target", target=target.name),
                    data={"target_id": selected_target_id, "target_name": target.name},
                )

        return messages

    async def run_night_phase(self) -> list[str]:
        """执行夜晚阶段，各角色依次行动。"""
        if not self.game_state:
            msg = "Game not initialized"
            raise RuntimeError(msg)

        messages: list[str] = []
        self.game_state.set_phase(GamePhase.NIGHT)

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_night_falls"),
            data={"action": "night_falls"},
        )

        self._log_event(
            EventType.PHASE_CHANGED,
            self.locale.get("night_begins", round_number=self.game_state.round_number),
            data={"phase": GamePhase.NIGHT.value, "round": self.game_state.round_number},
        )

        messages.append("")

        def _log_role_acting(player: PlayerProtocol) -> None:
            role_name = player.get_role_name()
            self._log_event(
                EventType.ROLE_ACTING,
                self.locale.get("role_acting", role=role_name, player=player.name),
                data={"player_id": player.player_id, "role": role_name},
            )

        scheduler = NightSkillScheduler(
            self.game_state,
            log_event=self._log_event,
            locale=self.locale,
            resolve_werewolf_votes=self._resolve_werewolf_votes,
            log_role_acting=_log_role_acting,
        )

        # 先执行预狼阶段（梦魇狼在讨论前封锁技能）
        pre_wolf_actions = await scheduler.run_pre_wolf_phase()
        messages.extend(self.process_actions(pre_wolf_actions))

        await self._resolve_blood_moon_transforms()

        # 预狼行动结束后再进行狼队讨论
        discussion_messages = await self._run_werewolf_discussion()
        messages.extend(discussion_messages)

        wolf_vote_actions = await scheduler.run_wolf_vote_phase()
        messages.extend(self.process_actions(wolf_vote_actions))

        werewolf_vote_messages = self._resolve_werewolf_votes()
        messages.extend(werewolf_vote_messages)

        post_wolf_actions = await scheduler.run_post_wolf_resolution()
        messages.extend(self.process_actions(post_wolf_actions))

        death_messages = await self.resolve_deaths()
        messages.extend(death_messages)

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_sleep"),
            data={"action": "werewolves_sleep"},
        )

        return messages
