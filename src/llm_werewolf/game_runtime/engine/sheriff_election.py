"""游戏引擎的警长选举阶段逻辑。"""

from collections.abc import Callable

from llm_werewolf.game_runtime.types import EventType, GamePhase, PlayerProtocol
from llm_werewolf.strategy.contracts.decisions import SpeechDecision
from llm_werewolf.strategy.contracts.phase_outputs import ActionPhase
from llm_werewolf.game_runtime.i18n.locale import Locale
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.events.visibility import VisibilityChannel


class SheriffElectionMixin:
    """处理警长选举阶段逻辑的 Mixin。"""

    game_state: GameState | None
    locale: Locale
    _log_event: Callable
    build_player_observation: Callable[[PlayerProtocol], str]

    async def execute_sheriff_election(self) -> None:
        """执行警长选举阶段。"""
        if not self.game_state:
            return

        self._log_event(
            EventType.SHERIFF_CAMPAIGN_STARTED, self.locale.get("sheriff_campaign_started")
        )

        candidates = await self._collect_sheriff_candidates()

        if not candidates:
            self._log_event(EventType.MESSAGE, self.locale.get("no_candidates"))
            self.game_state.sheriff_election_done = True
            return

        if len(candidates) == 1:
            self._log_event(
                EventType.MESSAGE,
                self.locale.get("sheriff_single_candidate", player=candidates[0].name),
            )
            self._elect_sheriff(candidates[0])
            self.game_state.sheriff_election_done = True
            return

        await self._conduct_campaign_speeches(candidates)
        vote_counts = await self._conduct_sheriff_voting(candidates)
        await self._resolve_sheriff_result(vote_counts, candidates)

        self.game_state.sheriff_election_done = True

    async def _collect_sheriff_candidates(self) -> list[PlayerProtocol]:
        if not self.game_state:
            return []

        interaction = self.game_state.require_phase_interaction()
        alive_players = self.game_state.get_alive_players()
        candidates: list[PlayerProtocol] = []

        for player in alive_players:
            if not player.agent:
                continue
            context = self._build_campaign_context(player)
            try:
                yes = await interaction.request_yes_no(
                    player,
                    player.agent,
                    player.get_role_name(),
                    self.locale.get("sheriff_ask_run"),
                    context,
                    round_number=self.game_state.round_number,
                    phase=GamePhase.SHERIFF_ELECTION.value,
                )
                if yes:
                    candidates.append(player)
            except Exception as exc:
                self._log_event(
                    EventType.ERROR,
                    self.locale.get("sheriff_candidate_error", player=player.name, error=str(exc)),
                    data={
                        "player_id": player.player_id,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )

        for candidate in candidates:
            self._log_event(
                EventType.MESSAGE, self.locale.get("player_volunteers", player=candidate.name)
            )

        return candidates

    def _build_campaign_context(self, player: PlayerProtocol) -> str:
        if not self.game_state:
            return ""

        from llm_werewolf.game_runtime.prompts.actions import EngineContexts

        return EngineContexts.sheriff_run(
            player.name, player.get_role_name(), self.game_state.round_number
        ) + self.locale.get("sheriff_campaign_note")

    async def _conduct_campaign_speeches(self, candidates: list[PlayerProtocol]) -> None:
        if not self.game_state:
            return

        self._log_event(
            EventType.MESSAGE, self.locale.get("campaign_speeches_start", count=len(candidates))
        )

        interaction = self.game_state.require_phase_interaction()
        alive = self.game_state.get_alive_players()

        def context_builder(candidate: PlayerProtocol) -> str:
            return self._build_speech_context(candidate, candidates)

        def on_speech(speaker: PlayerProtocol, decision: SpeechDecision, _routed: object) -> None:
            self._log_event(
                EventType.SHERIFF_CANDIDATE_SPEECH,
                self.locale.get(
                    "candidate_speech", candidate=speaker.name, speech=decision.public_speech
                ),
                data={"player_id": speaker.player_id, "speech": decision.public_speech},
                visible_to=None,
            )

        tracker = (
            self.game_state.vote_intention_tracker
            if self.game_state.track_vote_intentions
            else None
        )
        on_intention = self._log_vote_intention_record if tracker else None

        await interaction.run_roundtable(
            candidates,
            channel=VisibilityChannel.PUBLIC,
            context_builder=context_builder,
            instruction=self.locale.get("sheriff_speech_instruction"),
            phase=GamePhase.SHERIFF_ELECTION.value,
            round_number=self.game_state.round_number,
            audience=alive,
            on_speech=on_speech,
            vote_intention_tracker=tracker,
            on_vote_intention_record=on_intention,
        )

    def _build_speech_context(
        self, player: PlayerProtocol, candidates: list[PlayerProtocol]
    ) -> str:
        if not self.game_state:
            return ""

        other_candidates = [c.name for c in candidates if c.player_id != player.player_id]

        from llm_werewolf.game_runtime.prompts.actions import EngineContexts

        base = EngineContexts.sheriff_speech(
            player.name, player.get_role_name(), self.game_state.round_number, len(candidates)
        )
        others = ", ".join(other_candidates) if other_candidates else "无"
        obs = self.build_player_observation(
            player,
            include_visible_events=True,
            include_private_notes=True,
            for_agent_decision=True,
        )
        return f"{obs}\n\n{base}\n{self.locale.get('sheriff_other_candidates', others=others)}"

    async def _conduct_sheriff_voting(self, candidates: list[PlayerProtocol]) -> dict[str, int]:
        if not self.game_state:
            return {}

        alive_players = self.game_state.get_alive_players()
        voters = [v for v in alive_players if v.agent]

        if not voters:
            self._log_event(EventType.MESSAGE, self.locale.get("no_voters"))
            return {c.player_id: 0 for c in candidates}

        self._log_event(
            EventType.MESSAGE, self.locale.get("sheriff_voting_start", count=len(voters))
        )

        interaction = self.game_state.require_phase_interaction()
        vote_counts: dict[str, int] = {c.player_id: 0 for c in candidates}

        for voter in voters:
            available = [c for c in candidates if c.player_id != voter.player_id]
            if not available:
                continue

            try:
                context = self._build_sheriff_voting_context(voter, available)
                vote_target = await interaction.request_seat_choice(
                    voter,
                    voter.agent,
                    voter.get_role_name(),
                    self.locale.get("sheriff_vote_action"),
                    available,
                    allow_skip=True,
                    additional_context=context,
                    fallback_random=False,
                    round_number=self.game_state.round_number,
                    phase=GamePhase.SHERIFF_ELECTION.value,
                    action_phase=ActionPhase.SHERIFF_VOTE,
                )
            except Exception as exc:
                self._log_event(
                    EventType.ERROR,
                    self.locale.get("sheriff_vote_error", voter=voter.name, error=str(exc)),
                    data={
                        "voter_id": voter.player_id,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
                vote_target = None

            if vote_target:
                vote_counts[vote_target.player_id] += 1
                self._log_event(
                    EventType.SHERIFF_VOTE_CAST,
                    self.locale.get(
                        "sheriff_vote_cast", voter=voter.name, candidate=vote_target.name
                    ),
                    data={"voter_id": voter.player_id, "target_id": vote_target.player_id},
                )
            else:
                self._log_event(
                    EventType.MESSAGE, self.locale.get("sheriff_vote_abstained", voter=voter.name)
                )

        return vote_counts

    def _build_sheriff_voting_context(
        self, player: PlayerProtocol, candidates: list[PlayerProtocol]
    ) -> str:
        if not self.game_state:
            return ""

        candidate_names = [c.name for c in candidates]

        from llm_werewolf.game_runtime.prompts.actions import EngineContexts

        return EngineContexts.sheriff_vote_intro(
            player.name, player.get_role_name(), self.game_state.round_number, candidate_names
        ) + self.locale.get("sheriff_vote_note")

    async def _resolve_sheriff_result(
        self, vote_counts: dict[str, int], candidates: list[PlayerProtocol]
    ) -> None:
        """结算警长选举结果，含平票处理。"""
        if not self.game_state or not vote_counts:
            return

        max_votes = max(vote_counts.values())
        winners = [pid for pid, count in vote_counts.items() if count == max_votes]

        for candidate in candidates:
            votes = vote_counts.get(candidate.player_id, 0)
            self._log_event(
                EventType.MESSAGE,
                self.locale.get("sheriff_vote_result", candidate=candidate.name, votes=votes),
            )

        if len(winners) == 1:
            winner_id = winners[0]
            winner = self.game_state.get_player(winner_id)
            if winner:
                self._elect_sheriff(winner)
        else:
            await self._handle_sheriff_tie(winners, candidates)

    async def _handle_sheriff_tie(
        self, winner_ids: list[str], all_candidates: list[PlayerProtocol]
    ) -> None:
        """处理平票：首次平票 → PK 发言 + 重投；再次平票 → 警徽流失。"""
        if not self.game_state:
            return

        tie_count = self.game_state.sheriff_tie_count
        winner_names = [
            self.game_state.get_player(pid).name
            for pid in winner_ids
            if self.game_state.get_player(pid)
        ]

        if tie_count == 0:
            # 首次平票：PK 发言 + 重投
            self._log_event(
                EventType.SHERIFF_TIE,
                self.locale.get("sheriff_tie_pk", candidates=", ".join(winner_names)),
            )

            pk_candidates = [c for c in all_candidates if c.player_id in winner_ids]

            if len(pk_candidates) >= 2:
                await self._conduct_pk_speeches(pk_candidates)
                vote_counts = await self._conduct_sheriff_voting(pk_candidates)
                self.game_state.sheriff_tie_count = 1
                await self._resolve_sheriff_result(vote_counts, pk_candidates)
            else:
                # 仅 1 名 PK 候选人时的兜底（不应发生）
                self._log_event(EventType.MESSAGE, self.locale.get("sheriff_tie_fallback"))
        else:
            # 再次平票：警徽流失
            self._log_event(
                EventType.SHERIFF_TIE,
                self.locale.get("sheriff_badge_lost", candidates=", ".join(winner_names)),
            )
            # 未选出警长

    async def _conduct_pk_speeches(self, candidates: list[PlayerProtocol]) -> None:
        """平票候选人的 PK 发言。"""
        if not self.game_state:
            return

        self._log_event(
            EventType.MESSAGE, self.locale.get("pk_speeches_start", count=len(candidates))
        )

        interaction = self.game_state.require_phase_interaction()
        alive = self.game_state.get_alive_players()

        def context_builder(candidate: PlayerProtocol) -> str:
            return self._build_pk_speech_context(candidate, candidates)

        def on_speech(speaker: PlayerProtocol, decision: SpeechDecision, _routed: object) -> None:
            self._log_event(
                EventType.SHERIFF_CANDIDATE_SPEECH,
                self.locale.get(
                    "pk_candidate_speech", candidate=speaker.name, speech=decision.public_speech
                ),
                data={"player_id": speaker.player_id, "speech": decision.public_speech},
                visible_to=None,
            )

        await interaction.run_roundtable(
            candidates,
            channel=VisibilityChannel.PUBLIC,
            context_builder=context_builder,
            instruction=self.locale.get("pk_speech_instruction"),
            phase=GamePhase.SHERIFF_ELECTION.value,
            round_number=self.game_state.round_number,
            audience=alive,
            on_speech=on_speech,
        )

    def _build_pk_speech_context(
        self, player: PlayerProtocol, candidates: list[PlayerProtocol]
    ) -> str:
        if not self.game_state:
            return ""

        other_candidates = [c.name for c in candidates if c.player_id != player.player_id]

        from llm_werewolf.game_runtime.prompts.actions import EngineContexts

        base = EngineContexts.sheriff_speech(
            player.name, player.get_role_name(), self.game_state.round_number, len(candidates)
        )
        others = ", ".join(other_candidates) if other_candidates else "无"
        obs = self.build_player_observation(
            player,
            include_visible_events=True,
            include_private_notes=True,
            for_agent_decision=True,
        )
        return f"{obs}\n\n{base}\n{self.locale.get('pk_opponents', opponents=others)}"

    def _elect_sheriff(self, player: PlayerProtocol) -> None:
        if not self.game_state:
            return

        self.game_state.set_sheriff(player.player_id)
        self._log_event(
            EventType.SHERIFF_ELECTED,
            self.locale.get("sheriff_elected", player=player.name),
            data={"player_id": player.player_id},
        )
