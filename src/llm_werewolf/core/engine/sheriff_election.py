"""Sheriff election phase logic for the game engine."""

from collections.abc import Callable

from llm_werewolf.adapter.visibility import VisibilityChannel
from llm_werewolf.core.decisions import SpeechDecision
from llm_werewolf.core.types import EventType, PlayerProtocol
from llm_werewolf.core.locale import Locale
from llm_werewolf.core.game_state import GameState


class SheriffElectionMixin:
    """Mixin for handling sheriff election phase logic."""

    game_state: GameState | None
    locale: Locale
    _log_event: Callable
    build_player_observation: Callable[[PlayerProtocol], str]

    async def execute_sheriff_election(self) -> None:
        """Execute the sheriff election phase."""
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
            self._elect_sheriff(candidates[0])
            self.game_state.sheriff_election_done = True
            return

        await self._conduct_campaign_speeches(candidates)
        vote_counts = await self._conduct_sheriff_voting(candidates)
        self._determine_sheriff_winner(vote_counts, candidates)

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
                    "是否参加警长竞选？",
                    context,
                    round_number=self.game_state.round_number,
                    phase="sheriff_election",
                )
                if yes:
                    candidates.append(player)
            except Exception:
                continue

        for candidate in candidates:
            self._log_event(
                EventType.MESSAGE, self.locale.get("player_volunteers", player=candidate.name)
            )

        return candidates

    def _build_campaign_context(self, player: PlayerProtocol) -> str:
        if not self.game_state:
            return ""

        from llm_werewolf.core.prompts.actions import EngineContexts

        return EngineContexts.sheriff_run(
            player.name, player.get_role_name(), self.game_state.round_number
        ) + (
            "\n\n警长拥有 1.5 票投票权，死亡时可转移或撕毁警徽。"
            "请结合你的身份与策略决定是否参选。"
        )

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

        def on_speech(
            speaker: PlayerProtocol,
            decision: SpeechDecision,
            _routed: object,
        ) -> None:
            self._log_event(
                EventType.SHERIFF_CANDIDATE_SPEECH,
                self.locale.get(
                    "candidate_speech",
                    candidate=speaker.name,
                    speech=decision.public_speech,
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
            instruction="请发表竞选发言，说明为何适合担任警长：",
            phase="sheriff_election",
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

        from llm_werewolf.core.prompts.actions import EngineContexts

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
        return f"{obs}\n\n{base}\n其他候选人：{others}"

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
                    "投票选举警长",
                    available,
                    allow_skip=True,
                    additional_context=context,
                    fallback_random=False,
                    round_number=self.game_state.round_number,
                    phase="sheriff_election",
                )
            except Exception:
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
                    EventType.MESSAGE,
                    self.locale.get("sheriff_vote_abstained", voter=voter.name),
                )

        return vote_counts

    def _build_sheriff_voting_context(
        self, player: PlayerProtocol, candidates: list[PlayerProtocol]
    ) -> str:
        if not self.game_state:
            return ""

        candidate_names = [c.name for c in candidates]

        from llm_werewolf.core.prompts.actions import EngineContexts

        return EngineContexts.sheriff_vote_intro(
            player.name,
            player.get_role_name(),
            self.game_state.round_number,
            candidate_names,
        ) + "\n可结合竞选发言、信任度与自身胜利条件投票，也可选择弃权。"

    def _determine_sheriff_winner(
        self, vote_counts: dict[str, int], candidates: list[PlayerProtocol]
    ) -> None:
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

        if len(winners) > 1:
            winner_names = [
                self.game_state.get_player(pid).name
                for pid in winners
                if self.game_state.get_player(pid)
            ]
            self._log_event(
                EventType.SHERIFF_TIE,
                self.locale.get("sheriff_tie", candidates=", ".join(winner_names)),
            )
        else:
            winner_id = winners[0]
            winner = self.game_state.get_player(winner_id)
            if winner:
                self._elect_sheriff(winner)

    def _elect_sheriff(self, player: PlayerProtocol) -> None:
        if not self.game_state:
            return

        self.game_state.set_sheriff(player.player_id)
        self._log_event(
            EventType.SHERIFF_ELECTED,
            self.locale.get("sheriff_elected", player=player.name),
            data={"player_id": player.player_id},
        )
