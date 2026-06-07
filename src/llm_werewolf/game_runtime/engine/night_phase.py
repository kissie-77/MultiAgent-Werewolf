"""游戏引擎的夜晚阶段逻辑。"""

from collections.abc import Callable

from llm_werewolf.game_runtime.types import EventType, GamePhase, PlayerProtocol
from llm_werewolf.game_runtime.i18n.locale import Locale
from llm_werewolf.game_runtime.roles.names import participates_in_wolf_team
from llm_werewolf.game_runtime.roles.werewolf import BloodMoonApostle
from llm_werewolf.game_runtime.prompts.actions import EngineContexts
from llm_werewolf.strategy.contracts.decisions import SpeechDecision
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.events.visibility import VisibilityChannel, event_type_for_channel
from llm_werewolf.game_runtime.scheduling.night_scheduler import NightSkillScheduler
from llm_werewolf.game_runtime.registries.role_night_plans import offer_blood_moon_transform


class NightPhaseMixin:
    """处理夜晚阶段逻辑的 Mixin。"""

    game_state: GameState | None
    locale: Locale
    _log_event: Callable
    process_actions: Callable
    resolve_deaths: Callable
    build_player_observation: Callable
    build_shared_observation: Callable

    @staticmethod
    def _werewolf_discussion_role_note(werewolf: PlayerProtocol, werewolves: list[PlayerProtocol]) -> str:
        """Give each wolf a small conversational job to reduce repeated night-chat lines."""
        order = [w.player_id for w in werewolves]
        try:
            index = order.index(werewolf.player_id)
        except ValueError:
            index = 0
        roles = [
            "你的夜聊分工：先提出一个明确刀口，并给出 1 个基于当前夜间已知信息的核心理由。",
            "你的夜聊分工：综合前面已发言队友的提案；如果同意，补充一个不同角度的首夜合理性或风险，不要复读原话。",
            "你的夜聊分工：专门检查前面提案的风险，例如女巫救人、守卫保护、刀型暴露；必要时提出备选目标。",
            "你的夜聊分工：收束前面所有队友的共识和分歧，明确支持哪个目标，并说明明天如何解释这刀。",
        ]
        return roles[index % len(roles)]

    @staticmethod
    def _werewolf_discussion_grounding_note(round_number: int) -> str:
        if round_number <= 1:
            return (
                "【首夜信息边界】本局尚未经历白天公开发言和投票，"
                "禁止引用任何白天发言、票型、活跃度、带队表现、站边变化等未发生信息；"
                "只能基于座位、已知狼队友、可选目标、夜间已公开给你的信息和刀口可解释性讨论。"
            )
        return (
            "【夜聊信息边界】只能引用本局已经发生且你可见的信息；"
            "不确定的判断要说成推测，不要编造未发生的发言、票型或行动。"
        )

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
            p for p in self.game_state.get_alive_players() if not participates_in_wolf_team(p)
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
        wolf_panel = ""
        wolf_camp_minds = getattr(self.game_state, "wolf_camp_minds", None)
        if wolf_camp_minds is not None:
            from llm_werewolf.strategy.belief.format import format_wolf_camp_context
            from llm_werewolf.strategy.wolf.camp_mind import get_wolf_camp_mind

            own_panel = get_wolf_camp_mind(wolf_camp_minds, werewolf)
            wolf_panel = format_wolf_camp_context(own_panel)
        body = (
            shared
            + "\n"
            + EngineContexts.werewolf_discussion(
                werewolf.name, self.game_state.round_number, werewolf_names, target_names, ""
            )
        )
        body = body + "\n\n" + self._werewolf_discussion_grounding_note(
            self.game_state.round_number
        )
        body = body + "\n\n" + self._werewolf_discussion_role_note(werewolf, werewolves)
        if wolf_panel:
            body = body + "\n\n" + wolf_panel
        return body

    def _log_werewolf_speech(self, speaker: PlayerProtocol, decision: SpeechDecision) -> None:
        if not self.game_state:
            return
        wolf_ids = [
            p.player_id
            for p in self.game_state.get_alive_players()
            if participates_in_wolf_team(p)
        ]
        from llm_werewolf.game_runtime.support.fallback_log import (
            merge_agent_decision_into_event_data,
        )

        event_data = merge_agent_decision_into_event_data(
            {
                "player_id": speaker.player_id,
                "player_name": speaker.name,
                "speech": decision.public_speech,
                "role": "Werewolf",
            },
            getattr(speaker, "agent", None),
        )
        self._log_event(
            event_type_for_channel(VisibilityChannel.WOLF_TEAM),
            self.locale.get(
                "werewolf_discussion", player=speaker.name, speech=decision.public_speech
            ),
            data=event_data,
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
                    self.locale.get("blood_moon_transformed", player=player.name),
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
            EventType.SUB_PHASE,
            "",
            data={"name": "werewolf_chat"},
        )

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("narrator_werewolves_wake"),
            data={"action": "werewolves_wake"},
        )

        possible_targets = [
            p for p in self.game_state.get_alive_players() if not participates_in_wolf_team(p)
        ]
        if not possible_targets:
            return messages

        target_names = [p.name for p in possible_targets]
        interaction = self.game_state.require_phase_interaction()

        def on_speech(speaker: PlayerProtocol, decision: SpeechDecision, _routed: object) -> None:
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

    async def _resolve_werewolf_votes(self) -> list[str]:
        """结算狼队投票以确定刀口目标；平票时由狼队代表裁定而非随机。"""
        if not self.game_state:
            return []

        messages: list[str] = []

        if not self.game_state.werewolf_votes:
            self._log_event(
                EventType.MESSAGE,
                self.locale.get("werewolf_no_votes", round_number=self.game_state.round_number),
                data={
                    "action": "werewolf_no_votes",
                    "round": self.game_state.round_number,
                    "visibility": "wolf_team",
                },
            )
            return messages

        vote_counts: dict[str, int] = {}
        for target_id in self.game_state.werewolf_votes.values():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

        max_votes = max(vote_counts.values())
        candidates = [pid for pid, count in vote_counts.items() if count == max_votes]

        if not candidates:
            return messages

        if len(candidates) == 1:
            selected_target_id = candidates[0]
        else:
            selected_target_id = await self._break_werewolf_vote_tie(candidates)

        if selected_target_id:
            self.game_state.werewolf_target = selected_target_id
            target = self.game_state.get_player(selected_target_id)
            if target:
                self._log_event(
                    EventType.WEREWOLF_KILLED,
                    self.locale.get("werewolf_target", target=target.name),
                    data={"target_id": selected_target_id, "target_name": target.name},
                )

        return messages

    async def _break_werewolf_vote_tie(self, candidate_ids: list[str]) -> str | None:
        """狼刀平票：由一名存活狼人重新选定刀口（共识），否则按座位号确定性破平。"""
        if not self.game_state:
            return None

        tie_targets = [
            player
            for pid in candidate_ids
            if (player := self.game_state.get_player(pid)) is not None
        ]
        if not tie_targets:
            return sorted(candidate_ids)[0]

        wolves = [
            p
            for p in self.game_state.get_alive_players()
            if participates_in_wolf_team(p) and p.agent
        ]
        breaker = wolves[0] if wolves else None
        if breaker and breaker.agent:
            interaction = self.game_state.require_phase_interaction()
            from llm_werewolf.strategy.registry.role_prompts import GamePrompts
            from llm_werewolf.strategy.contracts.phase_outputs import ActionPhase

            chosen = await interaction.request_seat_choice(
                breaker,
                breaker.agent,
                role_name=breaker.get_role_name(),
                action_description=GamePrompts.WOLF_OPEN,
                possible_targets=tie_targets,
                allow_skip=False,
                additional_context=self.locale.get("werewolf_vote_tie_break", breaker=breaker.name)
                + "\n狼刀平票，请从并列目标中选定最终刀口。",
                fallback_random=False,
                round_number=self.game_state.round_number,
                phase="Night",
                action_phase=ActionPhase.NIGHT_KILL_VOTE,
            )
            if chosen:
                return chosen.player_id

        return sorted(candidate_ids)[0]

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

        scheduler_holder: list[NightSkillScheduler | None] = [None]

        def _log_role_acting(player: PlayerProtocol) -> None:
            role_name = player.get_role_name()
            data: dict[str, str] = {
                "player_id": player.player_id,
                "player_name": player.name,
                "role": role_name,
                "context": "night_skill",
            }
            sched = scheduler_holder[0]
            sub_phase = sched.active_sub_phase if sched is not None else None
            if sub_phase:
                data["sub_phase"] = sub_phase
            self._log_event(
                EventType.ROLE_ACTING,
                self.locale.get("role_acting", role=role_name, player=player.name),
                data=data,
            )

        scheduler = NightSkillScheduler(
            self.game_state,
            log_event=self._log_event,
            locale=self.locale,
            resolve_werewolf_votes=self._resolve_werewolf_votes,
            log_role_acting=_log_role_acting,
        )
        scheduler_holder[0] = scheduler

        # 先执行预狼阶段（梦魇狼在讨论前封锁技能）
        pre_wolf_actions = await scheduler.run_pre_wolf_phase()
        messages.extend(self.process_actions(pre_wolf_actions))

        await self._resolve_blood_moon_transforms()

        # 预狼行动结束后再进行狼队讨论
        discussion_messages = await self._run_werewolf_discussion()
        messages.extend(discussion_messages)

        wolf_vote_actions = await scheduler.run_wolf_vote_phase()
        messages.extend(self.process_actions(wolf_vote_actions))

        werewolf_vote_messages = await self._resolve_werewolf_votes()
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
