"""游戏引擎的投票阶段逻辑。"""

import asyncio
from collections.abc import Callable

from llm_werewolf.game_runtime.types import EventType, GamePhase, PlayerProtocol
from llm_werewolf.strategy.decisions import SpeechDecision
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.game_runtime.actions import VoteAction
from llm_werewolf.strategy.role_prompts import GamePrompts
from llm_werewolf.strategy.phase_outputs import ActionPhase, action_phase_instruction
from llm_werewolf.game_runtime.roles.names import RoleNames
from llm_werewolf.game_runtime.seat import get_player_seat
from llm_werewolf.game_runtime.actions.base import Action
from llm_werewolf.game_runtime.events.events import EventLogger
from llm_werewolf.game_runtime.prompts.actions import EngineContexts
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.events.visibility import VisibilityChannel
from llm_werewolf.game_runtime.engine.death_messages import elimination_announcement


def _format_runtime_error(exc: Exception) -> str:
    """Return a non-empty error string for runtime event logs."""
    message = str(exc).strip()
    if message:
        return f"{type(exc).__name__}: {message}"
    return type(exc).__name__


class VotingPhaseMixin:
    """处理投票阶段逻辑的 Mixin。"""

    game_state: GameState | None
    event_logger: EventLogger
    locale: Locale
    _log_event: Callable
    _handle_elder_penalty: Callable
    _handle_lover_death: Callable
    _handle_wolf_beauty_charm_death: Callable
    _handle_death_abilities: Callable
    build_player_observation: Callable[[PlayerProtocol], str]

    def _build_voting_context(self, player: PlayerProtocol) -> str:
        """构建投票阶段的上下文。

        Args:
            player: 即将投票的玩家。

        Returns:
            str: 供该玩家 agent 使用的上下文消息。
        """
        if not self.game_state:
            return ""

        context_parts = [EngineContexts.hub_decision_memory_notice()]

        context_parts.extend([
            "",
            GamePrompts.VOTE_BEGIN,
            action_phase_instruction(ActionPhase.DAY_VOTE),
            self.locale.get("vote_instruction"),
        ])

        return "\n".join(context_parts)

    async def _collect_votes(self) -> list[Action]:
        """并发收集所有玩家的投票。

        Returns:
            list[Action]: 投票行动列表。
        """
        if not self.game_state:
            return []

        def _fallback_target_from_vote_intention(
            player: PlayerProtocol, possible_targets: list[PlayerProtocol]
        ) -> PlayerProtocol | None:
            tracker = getattr(self.game_state, "vote_intention_tracker", None)
            if tracker is None:
                return None

            entry = None
            for record in reversed(getattr(tracker, "speech_records", [])):
                entry = getattr(record, "after", {}).get(player.player_id)
                if entry is not None:
                    break
            if entry is None:
                for snapshot in reversed(getattr(tracker, "snapshots", [])):
                    entry = getattr(snapshot, "intentions", {}).get(player.player_id)
                    if entry is not None:
                        break
            if entry is None or getattr(entry, "seat", 0) <= 0:
                return None

            target_id = getattr(entry, "target_id", None)
            if target_id:
                for target in possible_targets:
                    if target.player_id == target_id:
                        return target

            seat = int(getattr(entry, "seat", 0))
            for target in possible_targets:
                if get_player_seat(target) == seat:
                    return target
            return None

        async def _get_vote(player: PlayerProtocol) -> Action | None:
            """获取单个玩家的投票。"""
            possible_targets = self.game_state.get_alive_players(except_ids=[player.player_id])
            if not possible_targets or not player.agent:
                return None

            try:
                context = self._build_voting_context(player)
                interaction = self.game_state.require_phase_interaction()
                target_player = await interaction.request_seat_choice(
                    player,
                    player.agent,
                    player.get_role_name(),
                    self.locale.get("vote_prompt"),
                    possible_targets,
                    allow_skip=True,
                    additional_context=context,
                    fallback_random=True,
                    round_number=self.game_state.round_number,
                    phase="Voting",
                    action_phase=ActionPhase.DAY_VOTE,
                )

                if target_player:
                    player.agent.add_decision(
                        f"Round {self.game_state.round_number}: Voted for {target_player.name}"
                    )
                    return VoteAction(player, target_player, self.game_state)
            except Exception as e:
                fallback_target = _fallback_target_from_vote_intention(player, possible_targets)
                if fallback_target is not None:
                    player.agent.add_decision(
                        "Round "
                        f"{self.game_state.round_number}: Voted for "
                        f"{fallback_target.name} (fallback from vote intention)"
                    )
                    return VoteAction(player, fallback_target, self.game_state)

                error_text = _format_runtime_error(e)
                self._log_event(
                    EventType.ERROR,
                    self.locale.get("vote_failed", player=player.name, error=error_text),
                    data={"player_id": player.player_id, "error": error_text},
                )
            return None

        voters = [p for p in self.game_state.get_alive_players() if p.can_vote()]
        tasks = [_get_vote(voter) for voter in voters]
        results = await asyncio.gather(*tasks)
        return [action for action in results if action is not None]

    def _process_votes(self, vote_actions: list[Action]) -> None:
        """处理并记录投票行动。

        Args:
            vote_actions: 待处理的投票行动列表。
        """
        for action in vote_actions:
            if action.validate():
                action.execute()
                self._log_event(
                    EventType.VOTE_CAST,
                    self.locale.get(
                        "vote_cast", voter=action.actor.name, target=action.target.name
                    ),
                    data={
                        "voter_id": action.actor.player_id,
                        "voter_name": action.actor.name,
                        "target_id": action.target.player_id,
                        "target_name": action.target.name,
                    },
                )

    def _display_vote_results(self, vote_counts: dict[str, float]) -> None:
        """显示投票结果摘要。

        Args:
            vote_counts: player_id 到得票数的映射（float 以支持警长 1.5 票）。
        """
        if not self.game_state:
            return

        self._log_event(
            EventType.VOTE_RESULT,
            self.locale.get("vote_summary"),
            data={"vote_counts": vote_counts},
        )

        for target_id, count in sorted(vote_counts.items(), key=lambda x: x[1], reverse=True):
            target = self.game_state.get_player(target_id)
            if target:
                voters = [
                    self.game_state.get_player(voter_id).name
                    for voter_id, voted_for in self.game_state.votes.items()
                    if voted_for == target_id and self.game_state.get_player(voter_id)
                ]
                voters_str = ", ".join(voters)
                self._log_event(
                    EventType.VOTE_RESULT,
                    self.locale.get(
                        "vote_count", target=target.name, count=count, voters=voters_str
                    ),
                    data={"target_id": target_id, "count": count, "voters": voters},
                )

    def _eliminate_voted_player(self, eliminated: PlayerProtocol) -> None:
        """淘汰得票最多的玩家。

        Args:
            eliminated: 待淘汰的玩家。
        """
        if not self.game_state:
            return

        eliminated_id = eliminated.player_id

        # 特殊情况：白痴翻牌而非死亡
        if (
            eliminated.role.name == RoleNames.IDIOT
            and hasattr(eliminated.role, "revealed")
            and not eliminated.role.revealed
        ):
            eliminated.role.revealed = True
            eliminated.disable_voting()
            self._log_event(
                EventType.ROLE_REVEALED,
                self.locale.get("idiot_revealed", player=eliminated.name),
                data={"player_id": eliminated_id, "role": "Idiot"},
            )
            return

        # 正常淘汰
        eliminated.kill()
        self.game_state.day_deaths.add(eliminated_id)
        self.game_state.death_causes[eliminated_id] = "vote"

        message, data = elimination_announcement(
            self.locale, eliminated, show_role=self.show_role_on_death()
        )
        self._log_event(EventType.PLAYER_ELIMINATED, message, data=data)

        if data.get("role_revealed"):
            self._sync_beliefs_after_public_death(eliminated)

        # 处理长老惩罚
        if eliminated.role.name == RoleNames.ELDER:
            self._handle_elder_penalty()
            self._log_event(
                EventType.ROLE_REVEALED,
                self.locale.get("elder_executed"),
                data={"player_id": eliminated_id},
            )

        # 处理连锁死亡
        self._handle_lover_death(eliminated)
        self._handle_wolf_beauty_charm_death(eliminated)

    async def _handle_vote_tie(self, tie_candidates: list[str], messages: list[str]) -> list[str]:
        """处理投票平票：第一次平票 → PK 发言 + 重新投票；第二次平票 → 无人淘汰。

        Args:
            tie_candidates: 平票候选玩家 ID 列表。
            messages: 消息列表，用于追加 PK 阶段产生的消息。

        Returns:
            list[str]: 平票处理产生的消息。
        """
        if not self.game_state:
            return messages

        tie_count = self.game_state.vote_tie_count

        if tie_count == 0 and not self.game_state.allow_revote:
            self._log_event(
                EventType.VOTE_RESULT,
                self.locale.get(
                    "vote_tie_no_elimination",
                    candidates=", ".join(
                        self.game_state.get_player(cid).name
                        for cid in tie_candidates
                        if self.game_state.get_player(cid)
                    ),
                ),
                data={"tie_candidates": tie_candidates, "revote_disabled": True},
            )
            tie_names = ", ".join(
                self.game_state.get_player(cid).name
                for cid in tie_candidates
                if self.game_state.get_player(cid)
            )
            messages.append(self.locale.get("vote_tie_no_elimination", candidates=tie_names))
            return messages

        if tie_count == 0:
            # 第一次平票：PK 发言 + 重新投票
            self._log_event(
                EventType.VOTE_RESULT,
                self.locale.get(
                    "vote_tie_pk_announce",
                    candidates=", ".join(
                        self.game_state.get_player(cid).name
                        for cid in tie_candidates
                        if self.game_state.get_player(cid)
                    ),
                ),
                data={"tie_candidates": tie_candidates},
            )
            messages.append(
                self.locale.get(
                    "vote_tie_pk_announce",
                    candidates=", ".join(
                        self.game_state.get_player(cid).name
                        for cid in tie_candidates
                        if self.game_state.get_player(cid)
                    ),
                )
            )

            # PK 发言
            pk_candidates = [
                self.game_state.get_player(cid)
                for cid in tie_candidates
                if self.game_state.get_player(cid)
            ]
            await self._conduct_voting_pk_speeches(pk_candidates, messages)

            # 清空投票记录，重新投票
            self.game_state.votes.clear()
            vote_actions = await self._collect_votes()
            self._process_votes(vote_actions)

            vote_counts = self.game_state.get_vote_counts()
            self.game_state.vote_tie_count = 1

            if vote_counts:
                self._display_vote_results(vote_counts)
                max_votes = max(vote_counts.values())
                new_candidates = [pid for pid, count in vote_counts.items() if count == max_votes]

                if len(new_candidates) == 1:
                    eliminated = self.game_state.get_player(new_candidates[0])
                    if eliminated:
                        self._eliminate_voted_player(eliminated)
                else:
                    # 第二次平票
                    await self._handle_vote_tie(new_candidates, messages)
            else:
                self._log_event(EventType.VOTE_RESULT, self.locale.get("no_votes"), data={})
        else:
            # 第二次平票：无人淘汰
            self._log_event(
                EventType.VOTE_RESULT,
                self.locale.get(
                    "vote_tie_no_elimination",
                    candidates=", ".join(
                        self.game_state.get_player(cid).name
                        for cid in tie_candidates
                        if self.game_state.get_player(cid)
                    ),
                ),
                data={"tie_candidates": tie_candidates},
            )
            messages.append(
                self.locale.get(
                    "vote_tie_no_elimination",
                    candidates=", ".join(
                        self.game_state.get_player(cid).name
                        for cid in tie_candidates
                        if self.game_state.get_player(cid)
                    ),
                )
            )

        return messages

    def _build_exile_pk_speech_context(
        self, player: PlayerProtocol, candidates: list[PlayerProtocol]
    ) -> str:
        if not self.game_state:
            return ""

        other_candidates = [c.name for c in candidates if c.player_id != player.player_id]
        from llm_werewolf.game_runtime.prompts.actions import EngineContexts

        base = EngineContexts.exile_pk_speech(
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

    async def _conduct_voting_pk_speeches(
        self, pk_candidates: list[PlayerProtocol], messages: list[str]
    ) -> None:
        """执行 PK 发言阶段（仅 PK 候选人发言，全员旁听）。"""
        if not self.game_state:
            return

        self._log_event(
            EventType.MESSAGE,
            self.locale.get("pk_speech_begin"),
            data={"pk_candidates": [p.name for p in pk_candidates]},
        )

        alive_players = self.game_state.get_alive_players()
        interaction = self.game_state.require_phase_interaction()

        opening = self.locale.get(
            "pk_speech_opening", candidates=", ".join(p.name for p in pk_candidates)
        )

        def context_builder(candidate: PlayerProtocol) -> str:
            return self._build_exile_pk_speech_context(candidate, pk_candidates)

        def on_speech(speaker: PlayerProtocol, decision: SpeechDecision, _routed: object) -> None:
            self._log_public_speech(speaker, decision)
            messages.append(
                self.locale.get(
                    "player_speech", player=speaker.name, speech=decision.public_speech
                )
            )

        await interaction.run_roundtable(
            pk_candidates,
            channel=VisibilityChannel.PUBLIC,
            context_builder=context_builder,
            instruction=self.locale.get("pk_speech_instruction"),
            phase=GamePhase.DAY_VOTING.value,
            round_number=self.game_state.round_number,
            audience=alive_players,
            opening_announcement=opening,
            on_speech=on_speech,
        )

    async def _handle_knight_duel(self) -> list[str]:
        """处理骑士白天决斗（投票前执行）。

        Returns:
            list[str]: 决斗产生的消息。
        """
        if not self.game_state:
            return []

        messages = []
        # 查找存活且未决斗过的骑士
        knights = [
            p
            for p in self.game_state.get_alive_players()
            if p.get_role_name() == "Knight"
            and hasattr(p.role, "has_dueled")
            and not p.role.has_dueled
            and p.role.can_act_today(self.game_state)
        ]

        for knight in knights:
            if not knight.agent:
                continue

            possible_targets = self.game_state.get_alive_players(except_ids=[knight.player_id])
            if not possible_targets:
                continue

            self._log_event(
                EventType.MESSAGE,
                self.locale.get("knight_duel_begin", knight=knight.name),
                data={"player_id": knight.player_id},
            )

            interaction = self.game_state.require_phase_interaction()
            target = await interaction.request_seat_choice(
                knight,
                knight.agent,
                role_name="Knight",
                action_description="选择一名玩家进行决斗（对方是狼则其死，否则你死）",
                possible_targets=possible_targets,
                allow_skip=True,
                additional_context="决斗是整局游戏仅一次的机会；若目标是狼人则其死，否则你死。不确定请跳过。",
                fallback_random=False,
                round_number=self.game_state.round_number,
                phase="Day",
            )

            if target and target.is_alive():
                from llm_werewolf.game_runtime.actions.villager import KnightDuelAction

                action = KnightDuelAction(knight, target, self.game_state)
                if action.validate():
                    action.execute()
                    knight.role.has_dueled = True

                    if target.get_camp().value == "werewolf":
                        self._log_event(
                            EventType.KNIGHT_DUEL,
                            self.locale.get(
                                "knight_duel_wolf", knight=knight.name, target=target.name
                            ),
                            data={
                                "knight_id": knight.player_id,
                                "target_id": target.player_id,
                                "target_is_wolf": True,
                            },
                        )
                        messages.append(
                            self.locale.get(
                                "knight_duel_wolf", knight=knight.name, target=target.name
                            )
                        )
                        # 处理决斗导致的死亡连锁
                        self._handle_lover_death(target)
                        self._handle_wolf_beauty_charm_death(target)
                    else:
                        self._log_event(
                            EventType.KNIGHT_DUEL,
                            self.locale.get(
                                "knight_duel_good", knight=knight.name, target=target.name
                            ),
                            data={
                                "knight_id": knight.player_id,
                                "target_id": target.player_id,
                                "target_is_wolf": False,
                            },
                        )
                        messages.append(
                            self.locale.get(
                                "knight_duel_good", knight=knight.name, target=target.name
                            )
                        )
                        # 处理骑士死亡连锁
                        self._handle_lover_death(knight)
                        self._handle_wolf_beauty_charm_death(knight)
                else:
                    self._log_event(
                        EventType.ERROR,
                        self.locale.get(
                            "knight_duel_failed", knight=knight.name, target=target.name
                        ),
                        data={"player_id": knight.player_id},
                    )

        return messages

    async def run_voting_phase(self) -> list[str]:
        """执行投票阶段。

        Returns:
            list[str]: 投票阶段产生的消息。
        """
        if not self.game_state:
            msg = "Game not initialized"
            raise RuntimeError(msg)

        messages = []
        self.game_state.set_phase(GamePhase.DAY_VOTING)
        self.game_state.vote_tie_count = 0

        self._log_event(
            EventType.PHASE_CHANGED,
            self.locale.get("voting_phase_separator"),
            data={
                "phase": GamePhase.DAY_VOTING.value,
                "round": self.game_state.round_number,
            },
        )

        messages.append(self.locale.get("voting_phase_separator"))

        # 先处理骑士决斗（投票前）
        knight_messages = await self._handle_knight_duel()
        messages.extend(knight_messages)

        # 收集并处理投票
        vote_actions = await self._collect_votes()
        self._process_votes(vote_actions)

        vote_counts = self.game_state.get_vote_counts()

        if vote_counts:
            self._display_vote_results(vote_counts)

            # 确定淘汰对象
            max_votes = max(vote_counts.values())
            candidates = [pid for pid, count in vote_counts.items() if count == max_votes]

            if len(candidates) == 1:
                eliminated = self.game_state.get_player(candidates[0])
                if eliminated:
                    self._eliminate_voted_player(eliminated)
            else:
                await self._handle_vote_tie(candidates, messages)
        else:
            self._log_event(EventType.VOTE_RESULT, self.locale.get("no_votes"), data={})

        death_ability_messages = await self._handle_death_abilities()
        messages.extend(death_ability_messages)

        return messages
