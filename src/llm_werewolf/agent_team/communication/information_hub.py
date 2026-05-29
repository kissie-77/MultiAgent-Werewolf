"""基于 MsgHub 的 Agent 交互信息隔离。

每次 LLM 调用在面向正确受众的 MsgHub 作用域内执行：
- PUBLIC：所有存活玩家可听广播（白天讨论、警上发言、旁白）
- WOLF_TEAM：仅狼人
- PRIVATE：仅单个行动者（投票、夜间技能、是/否决策）

事件日志仅用于对话回放/审计（``HUB_DIALOGUE_EVENT_TYPES``）；
LLM 决策 prompt 不包含这些事件，发言从 MsgHub / ReAct 记忆读取。
``Event.visible_to`` 仍为日志过滤的权威依据；MsgHub 控制记忆隔离。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import asyncio
import logging

from agentscope.message import Msg as AgentScopeMsg
from agentscope.pipeline import MsgHub

from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.strategy.decisions import SpeechDecision
from llm_werewolf.strategy.vote_intention import (
    VoteIntentionEntry,
    VoteIntentionAnchor,
    VoteIntentionTracker,
    VoteIntentionSnapshot,
    SpeechVoteIntentionRecord,
)
from llm_werewolf.game_runtime.prompts.actions import EngineContexts
from llm_werewolf.game_runtime.events.visibility import RoutedMessage, VisibilityChannel
from llm_werewolf.agent_team.invocation.serial_calls import allow_parallel_agent_calls
from llm_werewolf.agent_team.communication.message_router import MessageRouter

if TYPE_CHECKING:
    from collections.abc import Callable

    from llm_werewolf.game_runtime.types import AgentProtocol, PlayerProtocol
    from llm_werewolf.strategy.phase_outputs import ActionPhase

logger = logging.getLogger(__name__)


class InformationHub:
    """经 MsgHub 按通道可见性路由全部 Agent 流量。"""

    def __init__(self) -> None:
        self._build_observation: Callable[[PlayerProtocol], str] | None = None
        self._get_alive_players: Callable[[], list[PlayerProtocol]] | None = None
        self._vote_intention_concurrency = 1

    def set_context_provider(
        self,
        *,
        build_observation: Callable[[PlayerProtocol], str],
        get_alive_players: Callable[[], list[PlayerProtocol]],
    ) -> None:
        """接入引擎观测构建器（由 GameEngine.setup_game 调用）。"""
        self._build_observation = build_observation
        self._get_alive_players = get_alive_players

    def configure_vote_intention_concurrency(self, concurrency: int) -> None:
        """Set bounded fan-out for vote-intention collection."""
        self._vote_intention_concurrency = max(1, int(concurrency))

    @staticmethod
    def _react_agent(player: PlayerProtocol) -> Any | None:
        agent = player.agent
        if agent is None:
            return None
        return getattr(agent, "agentscope_agent", None)

    def _resolve_audience(
        self,
        channel: VisibilityChannel,
        *,
        audience: list[PlayerProtocol] | None = None,
        actor: PlayerProtocol | None = None,
    ) -> list[PlayerProtocol]:
        """解析 MsgHub 参与者；受众仅由引擎规则选定。"""
        if self._get_alive_players is None:
            return []
        alive = self._get_alive_players()
        routed = MessageRouter.resolve_audience_players(
            channel, alive, custom_audience=audience, actor=actor
        )
        return [p for p in routed if self._react_agent(p) is not None]

    def _merge_private_context(self, actor: PlayerProtocol, additional_context: str) -> str:
        parts: list[str] = []
        if self._build_observation:
            observation = self._build_observation(actor)
            if observation:
                parts.append(observation)
        if actor.agent:
            decision_context = actor.agent.get_decision_context()
            if decision_context:
                parts.append(decision_context)
            memory_manager = getattr(actor.agent, "memory_manager", None)
            if memory_manager:
                for event in self._recent_visible_events(actor):
                    memory_manager.add_event(event)
                memory_context = memory_manager.get_context_for_decision()
                if memory_context:
                    parts.append(memory_context)
        if additional_context:
            parts.append(additional_context)
        return "\n\n".join(parts)

    def _recent_visible_events(self, actor: PlayerProtocol) -> list[Any]:
        """提取当前玩家最近可见的事件，供记忆模块筛选关键事件。"""
        game_state = getattr(actor, "game_state", None)
        event_logger = getattr(game_state, "event_logger", None) if game_state else None
        if event_logger is None:
            return []
        current_round = getattr(game_state, "round_number", 0)
        since_round = current_round - 1 if current_round > 1 else None
        return event_logger.get_events_for_player(actor.player_id, since_round)

    async def _deliver_private(
        self, react_agent: Any, speaker_name: str, private_thought: str
    ) -> None:
        if not private_thought.strip():
            return
        private_msg = AgentScopeMsg(
            name="Moderator",
            content=f"[内心 · 仅{speaker_name}可见] {private_thought.strip()}",
            role="user",
            metadata={"visibility": VisibilityChannel.PRIVATE.value},
        )
        await react_agent.observe(private_msg)

    async def _broadcast_moderator(
        self,
        hub: MsgHub,
        content: str,
        *,
        channel: VisibilityChannel,
        phase: str = "",
        round_number: int = 0,
    ) -> None:
        if not content.strip():
            return
        msg = AgentScopeMsg(
            name="Moderator",
            content=content.strip(),
            role="user",
            metadata={"visibility": channel.value, "phase": phase, "round": round_number},
        )
        await hub.broadcast(msg)

    async def _broadcast_public(
        self,
        hub: MsgHub,
        speaker: PlayerProtocol,
        public_speech: str,
        channel: VisibilityChannel,
        phase: str,
        round_number: int,
        audience_players: list[PlayerProtocol],
    ) -> RoutedMessage:
        seat = WerewolfAdapterBridge.get_player_seat(speaker) or 0
        audience = MessageRouter.resolve_audience_player_ids(channel, audience_players)
        routed = RoutedMessage(
            speaker_seat=seat,
            speaker_player_id=speaker.player_id,
            speaker_name=speaker.name,
            public_speech=public_speech,
            private_thought=None,
            channel=channel,
            phase=phase,
            round_number=round_number,
            audience_player_ids=audience,
        )
        public_msg = AgentScopeMsg(
            name=speaker.name,
            content=public_speech,
            role="assistant",
            metadata={
                "visibility": channel.value,
                "seat": seat,
                "phase": phase,
                "round": round_number,
            },
        )
        await hub.broadcast(public_msg)
        return routed

    async def announce(
        self,
        content: str,
        *,
        channel: VisibilityChannel = VisibilityChannel.PUBLIC,
        audience: list[PlayerProtocol] | None = None,
        phase: str = "",
        round_number: int = 0,
    ) -> None:
        """经 MsgHub 向某通道广播旁白/上下文。"""
        members = self._resolve_audience(channel, audience=audience)
        react_agents = [a for a in (self._react_agent(p) for p in members) if a is not None]
        if not react_agents:
            return
        async with MsgHub(
            participants=react_agents,
            enable_auto_broadcast=False,
            name=f"announce-{channel.value}-r{round_number}",
        ) as hub:
            await self._broadcast_moderator(
                hub, content, channel=channel, phase=phase, round_number=round_number
            )

    async def _collect_vote_intentions(
        self,
        observers: list[PlayerProtocol],
        *,
        anchor: VoteIntentionAnchor,
        context_builder: Callable[[PlayerProtocol], str],
        phase: str,
        round_number: int,
        last_speaker: PlayerProtocol | None = None,
    ) -> dict[str, VoteIntentionEntry]:
        """每位存活听众须经 LLM 输出投票意向（私密）。"""
        last_name = last_speaker.name if last_speaker else None
        alive = self._get_alive_players() if self._get_alive_players else []
        jobs: list[tuple[PlayerProtocol, list[PlayerProtocol], str]] = []

        for observer in observers:
            if not observer.is_alive() or observer.agent is None:
                continue
            possible_targets = [p for p in alive if p.player_id != observer.player_id]
            extra_parts = [context_builder(observer), EngineContexts.hub_decision_memory_notice()]
            if anchor == VoteIntentionAnchor.INITIAL:
                extra_parts.append("【投票意向】讨论开始前的初始意向。")
            else:
                extra_parts.append(f"【投票意向】请根据刚听完的 {last_name} 的发言更新意向。")
            extra = "\n\n".join(part for part in extra_parts if part)
            jobs.append((observer, possible_targets, extra))

        if not jobs:
            return {}

        semaphore = asyncio.Semaphore(self._vote_intention_concurrency)
        bypass_global_lock = self._vote_intention_concurrency > 1

        async def _collect_one(
            observer: PlayerProtocol, possible_targets: list[PlayerProtocol], extra: str
        ) -> tuple[str, VoteIntentionEntry]:

            async def _call(
                obs: PlayerProtocol = observer,
                targets: list[PlayerProtocol] = possible_targets,
                ctx: str = extra,
            ) -> VoteIntentionEntry:
                return await WerewolfAdapterBridge.request_vote_intention(
                    obs.agent,
                    obs.get_role_name(),
                    obs,
                    targets,
                    ctx,
                    anchor=anchor,
                    last_speaker_name=last_name,
                    round_number=round_number,
                    phase=phase,
                )

            async with semaphore:
                if bypass_global_lock:
                    with allow_parallel_agent_calls():
                        entry = await self._run_private_session(
                            observer, VisibilityChannel.PRIVATE, phase, round_number, extra, _call
                        )
                else:
                    entry = await self._run_private_session(
                        observer, VisibilityChannel.PRIVATE, phase, round_number, extra, _call
                    )
            return observer.player_id, entry

        results = await asyncio.gather(
            *(_collect_one(observer, targets, extra) for observer, targets, extra in jobs),
            return_exceptions=True,
        )
        intentions: dict[str, VoteIntentionEntry] = {}
        for (observer, _targets, _extra), result in zip(jobs, results, strict=False):
            if isinstance(result, BaseException):
                logger.warning(
                    "vote_intention failed player_id=%s player_name=%s: %s",
                    observer.player_id,
                    observer.name,
                    result,
                )
                continue
            player_id, entry = result
            intentions[player_id] = entry
        return intentions

    async def run_roundtable(
        self,
        speakers: list[PlayerProtocol],
        *,
        channel: VisibilityChannel,
        context_builder: Callable[[PlayerProtocol], str],
        instruction: str,
        phase: str,
        round_number: int,
        audience: list[PlayerProtocol] | None = None,
        opening_announcement: str = "",
        on_speech: Callable[[PlayerProtocol, SpeechDecision, RoutedMessage | None], None]
        | None = None,
        vote_intention_tracker: VoteIntentionTracker | None = None,
        on_vote_intention_record: Callable[[SpeechVoteIntentionRecord], None] | None = None,
    ) -> list[RoutedMessage]:
        """顺序讨论；MsgHub 受众仅听到公开发言行。"""
        routed_messages: list[RoutedMessage] = []
        audience_players = self._resolve_audience(channel, audience=audience)
        react_agents = [a for a in (self._react_agent(p) for p in audience_players) if a]

        # 无 ReAct 听众时通常提前返回（如纯 demo 局，行为保持不变）；
        # 但若存在人类发言者（人机局），仍需进入发言轮次让人类发言并被记录到日志，
        # 此时 MsgHub 参与者可能为空——enable_auto_broadcast=False 下空参与者是安全的。
        has_human_speaker = any(
            getattr(s.agent, "model", "") == "human" for s in speakers if s.agent
        )
        if not react_agents and not has_human_speaker:
            return routed_messages

        async with MsgHub(
            participants=react_agents,
            enable_auto_broadcast=False,
            name=f"roundtable-{channel.value}-r{round_number}",
        ) as hub:
            if opening_announcement:
                await self._broadcast_moderator(
                    hub,
                    opening_announcement,
                    channel=channel,
                    phase=phase,
                    round_number=round_number,
                )

            prior_intentions: dict[str, VoteIntentionEntry] = {}
            if vote_intention_tracker is not None:
                prior_intentions = await self._collect_vote_intentions(
                    audience_players,
                    anchor=VoteIntentionAnchor.INITIAL,
                    context_builder=context_builder,
                    phase=phase,
                    round_number=round_number,
                )
                vote_intention_tracker.add_snapshot(
                    VoteIntentionSnapshot(
                        round_number=round_number,
                        phase=phase,
                        channel=channel.value,
                        anchor=VoteIntentionAnchor.INITIAL,
                        speaker_id="",
                        speaker_name="（讨论开始）",
                        intentions=prior_intentions,
                    )
                )
                if on_vote_intention_record:
                    from llm_werewolf.strategy.vote_intention import SpeechVoteIntentionRecord

                    on_vote_intention_record(
                        SpeechVoteIntentionRecord(
                            round_number=round_number,
                            phase=phase,
                            channel=channel.value,
                            speaker_id="",
                            speaker_name="（初始意向）",
                            public_speech="",
                            before={},
                            after=prior_intentions,
                            swings=[],
                        )
                    )

            for speaker in speakers:
                if not speaker.is_alive() or speaker.agent is None:
                    continue

                context = context_builder(speaker)
                context = "\n\n".join([
                    context,
                    EngineContexts.hub_roundtable_memory_notice(channel.value),
                ])
                from llm_werewolf.strategy.phase_outputs import resolve_roundtable_phase

                rt_phase = resolve_roundtable_phase(channel=channel.value, phase=phase)
                decision = await WerewolfAdapterBridge.request_speech(
                    speaker.agent, context, instruction, roundtable_phase=rt_phase
                )

                react_self = self._react_agent(speaker)
                routed: RoutedMessage | None = None

                if react_self and decision.private_thought:
                    await self._deliver_private(react_self, speaker.name, decision.private_thought)

                if decision.public_speech.strip():
                    routed = await self._broadcast_public(
                        hub,
                        speaker,
                        decision.public_speech.strip(),
                        channel,
                        phase,
                        round_number,
                        audience_players,
                    )
                    routed.private_thought = decision.private_thought
                    routed_messages.append(routed)

                if speaker.agent:
                    speaker.agent.add_decision(
                        f"Round {round_number} ({channel.value}): "
                        f"You said: {decision.public_speech}"
                    )

                if on_speech:
                    on_speech(speaker, decision, routed)

                if vote_intention_tracker is not None:
                    speech_text = decision.public_speech.strip()
                    after_intentions = await self._collect_vote_intentions(
                        audience_players,
                        anchor=VoteIntentionAnchor.AFTER_SPEECH,
                        context_builder=context_builder,
                        phase=phase,
                        round_number=round_number,
                        last_speaker=speaker,
                    )
                    vote_intention_tracker.add_snapshot(
                        VoteIntentionSnapshot(
                            round_number=round_number,
                            phase=phase,
                            channel=channel.value,
                            anchor=VoteIntentionAnchor.AFTER_SPEECH,
                            speaker_id=speaker.player_id,
                            speaker_name=speaker.name,
                            intentions=after_intentions,
                        )
                    )
                    record = vote_intention_tracker.record_speech_block(
                        round_number=round_number,
                        phase=phase,
                        channel=channel.value,
                        speaker=speaker,
                        public_speech=speech_text,
                        before=prior_intentions,
                        after=after_intentions,
                    )
                    prior_intentions = after_intentions
                    if on_vote_intention_record:
                        on_vote_intention_record(record)

        return routed_messages

    async def _run_private_session(
        self,
        actor: PlayerProtocol,
        channel: VisibilityChannel,
        phase: str,
        round_number: int,
        context: str,
        action: Callable[[], Any],
    ) -> Any:
        """在仅含一名参与者的 MsgHub 内执行 Agent 调用。"""
        react = self._react_agent(actor)
        if react is None:
            return await action()

        async with MsgHub(
            participants=[react],
            enable_auto_broadcast=False,
            name=f"private-{channel.value}-{actor.player_id}-r{round_number}",
        ) as hub:
            await self._broadcast_moderator(
                hub,
                context,
                channel=VisibilityChannel.PRIVATE,
                phase=phase,
                round_number=round_number,
            )
            return await action()

    async def request_private_seat_choice(
        self,
        actor: PlayerProtocol,
        agent: AgentProtocol,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        allow_skip: bool = False,
        additional_context: str = "",
        fallback_random: bool = True,
        round_number: int | None = None,
        phase: str | None = None,
        action_phase: ActionPhase | None = None,
    ) -> PlayerProtocol | None:
        context = self._merge_private_context(actor, additional_context)

        async def _call() -> PlayerProtocol | None:
            return await WerewolfAdapterBridge.request_seat_choice(
                agent,
                role_name,
                action_description,
                possible_targets,
                allow_skip,
                context,
                fallback_random,
                round_number,
                phase,
                action_phase=action_phase,
            )

        return await self._run_private_session(
            actor, VisibilityChannel.PRIVATE, phase or "", round_number or 0, context, _call
        )

    async def request_private_witch_night(
        self,
        actor: PlayerProtocol,
        agent: AgentProtocol,
        role_name: str,
        *,
        can_see_victim: bool,
        victim_line: str,
        poison_targets: list[PlayerProtocol],
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ):
        from llm_werewolf.strategy.decisions import WitchNightDecision

        context = self._merge_private_context(actor, additional_context)

        async def _call() -> WitchNightDecision:
            return await WerewolfAdapterBridge.request_witch_night_choice(
                agent,
                role_name,
                can_see_victim=can_see_victim,
                victim_line=victim_line,
                poison_targets=poison_targets,
                additional_context=context,
                round_number=round_number,
                phase=phase,
            )

        return await self._run_private_session(
            actor, VisibilityChannel.PRIVATE, phase or "", round_number or 0, context, _call
        )

    async def request_private_yes_no(
        self,
        actor: PlayerProtocol,
        agent: AgentProtocol,
        role_name: str,
        question: str,
        context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> bool:
        full_context = self._merge_private_context(actor, context)

        async def _call() -> bool:
            return await WerewolfAdapterBridge.request_yes_no(
                agent, role_name, question, full_context, round_number, phase
            )

        return await self._run_private_session(
            actor, VisibilityChannel.PRIVATE, phase or "", round_number or 0, full_context, _call
        )

    async def request_private_multi_target(
        self,
        actor: PlayerProtocol,
        agent: AgentProtocol,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        num_targets: int,
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> list[PlayerProtocol] | None:
        context = self._merge_private_context(actor, additional_context)

        async def _call() -> list[PlayerProtocol] | None:
            return await WerewolfAdapterBridge.request_multi_target(
                agent,
                role_name,
                action_description,
                possible_targets,
                num_targets,
                context,
                round_number,
                phase,
            )

        return await self._run_private_session(
            actor, VisibilityChannel.PRIVATE, phase or "", round_number or 0, context, _call
        )

    async def collect_speech(
        self,
        speaker: PlayerProtocol,
        context: str,
        *,
        channel: VisibilityChannel,
        instruction: str = "",
        phase: str = "",
        round_number: int = 0,
        audience: list[PlayerProtocol] | None = None,
    ) -> SpeechDecision:
        """单次发言并经 MsgHub 路由（非圆桌流程时使用）。"""
        audience_players = self._resolve_audience(channel, audience=audience, actor=speaker)
        react_agents = [a for a in (self._react_agent(p) for p in audience_players) if a]

        if speaker.agent is None:
            return SpeechDecision(public_speech="（无公开发言）", private_thought=None)

        from llm_werewolf.strategy.phase_outputs import resolve_roundtable_phase

        rt_phase = resolve_roundtable_phase(channel=channel.value, phase=phase)
        decision = await WerewolfAdapterBridge.request_speech(
            speaker.agent, context, instruction, roundtable_phase=rt_phase
        )
        react_self = self._react_agent(speaker)
        if not react_self or not react_agents:
            return decision

        async with MsgHub(
            participants=react_agents,
            enable_auto_broadcast=False,
            name=f"speech-{channel.value}-r{round_number}",
        ) as hub:
            if decision.private_thought:
                await self._deliver_private(react_self, speaker.name, decision.private_thought)
            if decision.public_speech.strip():
                await self._broadcast_public(
                    hub,
                    speaker,
                    decision.public_speech.strip(),
                    channel,
                    phase,
                    round_number,
                    audience_players,
                )

        return decision
