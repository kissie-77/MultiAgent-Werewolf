import random
from typing import TYPE_CHECKING, Any
from pathlib import Path

from rich.console import Console

from llm_werewolf.game_runtime.types import (
    Event,
    EventType,
    GamePhase,
    RoleProtocol,
    AgentProtocol,
    PlayerProtocol,
)
from llm_werewolf.game_runtime.config import GameConfig
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.game_runtime.victory import VictoryChecker
from llm_werewolf.game_runtime.observation import ObservationBuilder
from llm_werewolf.game_runtime.roles.names import participates_in_wolf_team
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.events.events import EventLogger
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction, PhaseInteractionHub
from llm_werewolf.game_runtime.state.serialization import (
    load_game_state,
    save_game_state,
    restore_event_logger,
)
from llm_werewolf.game_runtime.events.event_formatter import EventFormatter
from llm_werewolf.game_runtime.events.event_visibility import (
    HUB_DIALOGUE_EVENT_TYPES,
    resolve_visible_to,
)

if TYPE_CHECKING:
    from collections.abc import Callable

console = Console()


class GameEngineBase:
    """游戏引擎基类，提供核心功能。"""

    def __init__(
        self,
        config: GameConfig | None = None,
        language: str = "en-US",
        information_hub: PhaseInteractionHub | None = None,
    ) -> None:
        """初始化游戏引擎。

        Args:
            config: 游戏配置。
            language: 本地化语言代码（en-US、zh-TW、zh-CN）。
            information_hub: 运行时交互 Hub，由装配层负责注入具体实现。
        """
        self.config = config
        self.game_state: GameState | None = None
        self.event_logger = EventLogger()
        self.victory_checker: VictoryChecker | None = None
        self.locale = Locale(language)
        self.observation_builder = ObservationBuilder()
        self._last_phase: GamePhase | None = None  # 跟踪阶段变化以输出分隔符

        self.information_hub = information_hub
        self.phase_interaction = PhaseInteraction(self.information_hub)

        self.on_event: Callable[[Event], None] = self._default_print_event

    def _default_print_event(self, event: Event) -> None:
        """默认事件处理器，将事件打印到控制台。

        可被 TUI 或其他界面覆盖。

        Args:
            event: 要显示的游戏事件。
        """
        # 阶段变化时打印阶段分隔符
        if event.phase != self._last_phase and event.event_type == EventType.PHASE_CHANGED:
            phase_value = event.phase.value
            if "night" in phase_value:
                console.print(f"\n{self.locale.get('night_separator')}")
            elif "sheriff" in phase_value:
                console.print("\n" + "=" * 60)
                console.print("        🎖️  SHERIFF ELECTION PHASE  🎖️")
                console.print("=" * 60 + "\n")
            elif "day" in phase_value:
                console.print(f"\n{self.locale.get('day_separator')}")
            self._last_phase = event.phase

        # 使用集中式事件格式化器（CLI 不包含时间戳）
        formatted_text = EventFormatter.format_event(event, include_timestamp=False)
        console.print(formatted_text)

    def _wire_game_state(self) -> None:
        """将 GameState 与 Hub / PhaseInteraction / 胜利判定等运行时依赖绑定。"""
        if not self.game_state:
            return

        self.game_state.information_hub = self.information_hub
        self.game_state.phase_interaction = self.phase_interaction
        self.game_state.event_logger = self.event_logger

        track_intentions = True if self.config is None else self.config.track_vote_intentions
        vote_intention_concurrency = (
            1 if self.config is None else self.config.vote_intention_concurrency
        )
        if self.information_hub is not None:
            self.information_hub.configure_vote_intention_concurrency(vote_intention_concurrency)
        if self.config is not None or not getattr(self.game_state, "track_vote_intentions", False):
            self.game_state.track_vote_intentions = track_intentions

        if not self.game_state.enable_sheriff and not self.game_state.sheriff_election_done:
            self.game_state.sheriff_election_done = True

        if (
            self.game_state.track_vote_intentions
            and self.game_state.vote_intention_tracker is None
        ):
            from llm_werewolf.strategy.vote_intention import VoteIntentionTracker

            self.game_state.vote_intention_tracker = VoteIntentionTracker()

        if self.game_state.track_vote_intentions and self.game_state.belief_log is None:
            from llm_werewolf.strategy.belief_state import BeliefLog
            from llm_werewolf.strategy.belief_updater import ensure_agent_belief_state
            from llm_werewolf.strategy.wolf_camp_mind import init_wolf_camp_mind

            self.game_state.belief_log = BeliefLog()
            wolves = [p for p in self.game_state.players if participates_in_wolf_team(p)]
            self.game_state.wolf_camp_mind = init_wolf_camp_mind(wolves)
            alive = self.game_state.get_alive_players()
            for player in alive:
                if player.agent is not None:
                    ensure_agent_belief_state(player, alive)
            from llm_werewolf.strategy.belief_format import sync_all_belief_memories

            sync_all_belief_memories(
                alive,
                alive=alive,
                wolf_camp_mind=self.game_state.wolf_camp_mind,
            )
            if self.information_hub is not None:
                self.information_hub.configure_belief_tracking(
                    self.game_state.belief_log,
                    self.game_state.wolf_camp_mind,
                    on_belief_batch=self._log_belief_batch,
                )

        if self.config is not None:
            self.game_state.night_timeout = self.config.night_timeout
            self.game_state.day_timeout = self.config.day_timeout
            self.game_state.vote_timeout = self.config.vote_timeout
            self.game_state.allow_revote = self.config.allow_revote
            self.game_state.show_role_on_death = self.config.show_role_on_death
            self.phase_interaction.configure_timeouts(
                night_timeout=self.config.night_timeout,
                day_timeout=self.config.day_timeout,
                vote_timeout=self.config.vote_timeout,
            )

        self.victory_checker = VictoryChecker(self.game_state)
        if self.information_hub is not None:
            self.information_hub.set_context_provider(
                build_observation=lambda player: self.build_player_observation(
                    player, for_agent_decision=True
                ),
                get_alive_players=lambda: (
                    self.game_state.get_alive_players() if self.game_state else []
                ),
            )

    @staticmethod
    def _attach_agent_to_player(
        player: Player, agent: AgentProtocol, seat_number: int, role_class: type | None = None
    ) -> None:
        """为玩家绑定 agent 并同步角色信息。"""
        player.agent = agent
        if hasattr(agent, "bind_role"):
            bind_target = role_class if role_class is not None else type(player.role)
            agent.bind_role(bind_target, seat_number=seat_number)  # type: ignore[attr-defined]

    def setup_game(self, players: list[AgentProtocol], roles: list[RoleProtocol]) -> None:
        """使用玩家和角色初始化游戏。

        Args:
            players: 具有 name 和 model 属性的 agent 实例列表。
            roles: 要分配的角色实例列表。
        """
        if len(players) != len(roles):
            msg = f"Number of players ({len(players)}) must match number of roles ({len(roles)})"
            raise ValueError(msg)

        shuffled_roles = roles.copy()
        random.shuffle(shuffled_roles)

        player_objects = []
        for idx, (agent, role_class) in enumerate(
            zip(players, shuffled_roles, strict=False), start=1
        ):
            player_id = f"player_{idx}"
            name = agent.name
            ai_model = agent.model
            player = Player(
                player_id=player_id, name=name, role=role_class, agent=agent, ai_model=ai_model
            )
            self._attach_agent_to_player(player, agent, idx, role_class)
            player_objects.append(player)

        self.game_state = GameState(player_objects)
        enable_sheriff = False if self.config is None else self.config.enable_sheriff
        self.game_state.enable_sheriff = enable_sheriff
        if not enable_sheriff:
            self.game_state.sheriff_election_done = True
        self._wire_game_state()

        self._log_event(
            EventType.GAME_STARTED,
            self.locale.get("game_started", player_count=len(player_objects)),
            data={"player_count": len(player_objects)},
        )

    def assign_roles(self) -> dict[str, str]:
        """为玩家分配角色（已在 setup_game 中完成）。

        Returns:
            dict[str, str]: player_id 到 role_name 的映射。
        """
        if not self.game_state:
            msg = "Game not initialized"
            raise RuntimeError(msg)

        return {p.player_id: p.get_role_name() for p in self.game_state.players}

    def show_role_on_death(self) -> bool:
        """是否在对局公开信息中公布出局者身份。"""
        if self.game_state is not None:
            return bool(self.game_state.show_role_on_death)
        if self.config is not None:
            return self.config.show_role_on_death
        return True

    def check_victory(self) -> bool:
        """检查是否满足任一胜利条件。

        Returns:
            bool: 若游戏已结束则为 True。
        """
        if not self.victory_checker:
            return False

        result = self.victory_checker.check_victory()

        if result.has_winner:
            if self.game_state:
                self.game_state.set_phase(GamePhase.ENDED)
                self.game_state.winner = result.winner_camp
                winning_ids = set(result.winner_ids)
                for player in self.game_state.players:
                    agent = player.agent
                    memory_manager = getattr(agent, "memory_manager", None) if agent else None
                    if memory_manager:
                        memory_manager.on_game_end(player.player_id in winning_ids)

            self._log_event(
                EventType.GAME_ENDED,
                self.locale.get("game_ended", winner=result.winner_camp, reason=result.reason),
                data={
                    "winner_camp": result.winner_camp,
                    "winner_ids": result.winner_ids,
                    "reason": result.reason,
                },
            )

            return True

        return False

    def _log_vote_intention_record(self, record: object) -> None:
        """记录与发言关联的投票意向变化，供回放分析。"""
        from llm_werewolf.strategy.vote_intention import (
            SpeechVoteIntentionRecord,
            format_intentions_line,
        )

        if not isinstance(record, SpeechVoteIntentionRecord):
            return
        before_line = format_intentions_line(record.before) if record.before else "—"
        after_line = format_intentions_line(record.after)
        if not record.public_speech and not record.before:
            message = f"【初始意向】[{after_line}]"
        else:
            message = (
                f"听完 {record.speaker_name} 发言后意向："
                f"[{before_line}] → [{after_line}]；{len(record.swings)} 人改意向"
            )
        self._log_event(EventType.VOTE_INTENTION_SNAPSHOT, message, data=record.to_dict())

    def _log_belief_batch(
        self,
        records: list[object],
        *,
        anchor: object,
        phase: str,
        round_number: int,
        speaker: PlayerProtocol | None,
    ) -> None:
        """记录一批心智状态快照，供控制台 / game_log 展示信念矩阵。"""
        from llm_werewolf.strategy.belief_format import format_belief_batch_log
        from llm_werewolf.strategy.belief_state import BeliefSnapshotRecord

        from llm_werewolf.strategy.vote_intention import VoteIntentionAnchor

        if not isinstance(anchor, VoteIntentionAnchor):
            return
        if not self.game_state or not records:
            return
        typed = [record for record in records if isinstance(record, BeliefSnapshotRecord)]
        if not typed:
            return
        player_names = {player.player_id: player.name for player in self.game_state.players}
        message = format_belief_batch_log(
            typed,
            round_number=round_number,
            phase=phase,
            anchor=anchor.value,
            speaker_name=speaker.name if speaker else None,
            player_names=player_names,
        )
        self._log_event(
            EventType.BELIEF_SNAPSHOT,
            message,
            data={
                "round": round_number,
                "phase": phase,
                "anchor": anchor.value,
                "speaker_id": speaker.player_id if speaker else "",
                "speaker_name": speaker.name if speaker else "",
                "snapshots": [record.to_dict() for record in typed],
            },
        )

    def _sync_beliefs_after_public_death(self, player: PlayerProtocol) -> None:
        """公开身份出局后，所有 Agent 信念矩阵塌缩该列。"""
        if not self.game_state or self.game_state.belief_log is None:
            return
        from llm_werewolf.game_runtime.seat import get_player_seat
        from llm_werewolf.strategy.belief_updater import apply_public_elimination_to_all_agents

        seat = get_player_seat(player)
        if seat is None:
            return
        apply_public_elimination_to_all_agents(
            self.game_state.players,
            eliminated_seat=seat,
            is_werewolf=participates_in_wolf_team(player),
        )
        from llm_werewolf.strategy.belief_format import sync_all_belief_memories

        sync_all_belief_memories(
            self.game_state.players,
            alive=self.game_state.get_alive_players(),
            wolf_camp_mind=self.game_state.wolf_camp_mind,
        )

    def _on_round_end(self, round_number: int) -> None:
        """在白天投票结束并进入下一夜前沉淀各 Agent 的工作记忆。"""
        if not self.game_state:
            return

        for player in self.game_state.players:
            agent = player.agent
            memory_manager = getattr(agent, "memory_manager", None) if agent else None
            if memory_manager:
                memory_manager.on_round_end(round_number)

    def _log_event(
        self,
        event_type: EventType,
        message: str,
        data: dict | None = None,
        visible_to: list[str] | None = None,
    ) -> None:
        """记录事件并通知监听者。

        Args:
            event_type: 事件类型。
            message: 事件消息。
            data: 附加事件数据。
            visible_to: 可查看此事件的玩家 ID 列表。
        """
        if not self.game_state:
            return

        if visible_to is None:
            wolf_ids = [
                p.player_id
                for p in self.game_state.get_alive_players()
                if participates_in_wolf_team(p)
            ]
            witch_ids = self.game_state.get_alive_witch_player_ids()
            visible_to = resolve_visible_to(
                event_type, data, wolf_player_ids=wolf_ids, witch_player_ids=witch_ids
            )

        event = self.event_logger.create_event(
            event_type=event_type,
            round_number=self.game_state.round_number,
            phase=self.game_state.phase,
            message=message,
            data=data,
            visible_to=visible_to,
        )

        self.on_event(event)

    def build_player_observation(
        self,
        player: Player,
        include_visible_events: bool = True,
        include_private_notes: bool = True,
        exclude_event_types: frozenset | None = None,
        *,
        for_agent_decision: bool = False,
    ) -> str:
        """为单个玩家构建过滤后的提示上下文。

        当 ``for_agent_decision`` 为 True 时，对话事件会从事件块中省略；
        发言内容应通过 MsgHub / ReAct 记忆提供。
        """
        if not self.game_state:
            return ""

        merged_exclude = exclude_event_types
        if for_agent_decision:
            merged_exclude = (merged_exclude or frozenset()) | HUB_DIALOGUE_EVENT_TYPES

        public_state = self.game_state.get_public_info()
        visible_events = self.event_logger.get_events_for_player(player.player_id)
        if merged_exclude:
            visible_events = [
                event for event in visible_events if event.event_type not in merged_exclude
            ]
        private_notes = player.get_private_notes(self.game_state)
        observation = self.observation_builder.build(
            player=player,
            game_state=public_state,
            all_players=self.game_state.players,
            visible_events=visible_events,
            private_notes=private_notes,
        )
        return self.observation_builder.format_for_prompt(
            observation,
            include_visible_events=include_visible_events,
            include_private_notes=include_private_notes,
        )

    def build_shared_observation(
        self,
        players: list[Player],
        additional_notes: list[str] | None = None,
        include_visible_events: bool = True,
        exclude_event_types: frozenset | None = None,
        *,
        for_agent_decision: bool = False,
    ) -> str:
        """构建可在玩家组间安全共享的过滤上下文。"""
        if not self.game_state or not players:
            return ""

        shared_events = self.event_logger.get_events_for_players([
            player.player_id for player in players
        ])
        merged_exclude = exclude_event_types
        if for_agent_decision:
            merged_exclude = (merged_exclude or frozenset()) | HUB_DIALOGUE_EVENT_TYPES
        if merged_exclude:
            shared_events = [
                event for event in shared_events if event.event_type not in merged_exclude
            ]
        from llm_werewolf.game_runtime.observation import flatten_private_notes

        private_notes = flatten_private_notes(list(additional_notes or []))
        observation = self.observation_builder.build(
            player=players[0],
            game_state=self.game_state.get_public_info(),
            all_players=self.game_state.players,
            visible_events=shared_events,
            private_notes=private_notes,
        )
        return self.observation_builder.format_for_prompt(
            observation,
            include_visible_events=include_visible_events,
            include_private_notes=bool(private_notes),
        )

    def get_game_state(self) -> GameState | None:
        """获取当前游戏状态。

        Returns:
            GameState | None: 游戏状态。
        """
        return self.game_state

    def get_events(self) -> list[Event]:
        """获取所有游戏事件。

        Returns:
            list[Event]: 事件列表。
        """
        return self.event_logger.events

    async def play_game(self) -> str:
        """运行主游戏循环。

        Returns:
            str: 最终游戏结果。
        """
        if not self.game_state:
            return "Game not initialized"

        while not self.check_victory():
            self.game_state.reset_deaths()

            await self.run_night_phase()

            if self.check_victory():
                break

            # 警长选举（仅第一天且 enable_sheriff）
            if (
                self.game_state.round_number == 1
                and self.game_state.enable_sheriff
                and not self.game_state.sheriff_election_done
            ):
                self.game_state.next_phase()  # 进入 SHERIFF_ELECTION
                await self.execute_sheriff_election()

            if self.check_victory():
                break

            self.game_state.next_phase()  # 进入 DAY_DISCUSSION
            await self.run_day_phase()

            self.game_state.next_phase()  # 进入 DAY_VOTING
            await self.run_voting_phase()

            if self.check_victory():
                break

            self._on_round_end(self.game_state.round_number)
            self.game_state.next_phase()  # 进入下一 NIGHT

        if self.game_state.winner:
            return self.locale.get("game_over", winner=self.game_state.winner)

        return self.locale.get("game_ended", winner="unknown", reason="")

    async def step(self) -> list[str]:
        """执行游戏的一步（一个阶段）。"""
        if not self.game_state:
            return ["Game not initialized"]

        if self.check_victory():
            return [f"Game Over! {self.game_state.winner} camp wins!"]

        phase_messages = []
        current_phase = self.game_state.get_phase()

        if current_phase == GamePhase.SETUP:
            self.game_state.next_phase()
            phase_messages = [
                "Game initialized! Press 'n' to start the first night phase.",
                f"Round {self.game_state.round_number} begins.",
            ]
        elif current_phase == GamePhase.NIGHT:
            phase_messages = await self.run_night_phase()
            if not self.check_victory():
                self.game_state.next_phase()
                if self.game_state.get_phase() == GamePhase.SHERIFF_ELECTION:
                    await self.execute_sheriff_election()
                    self.game_state.next_phase()
                    phase_messages.append("Sheriff election completed.")
        elif current_phase == GamePhase.SHERIFF_ELECTION:
            await self.execute_sheriff_election()
            self.game_state.next_phase()
            phase_messages = ["Sheriff election completed."]
        elif current_phase == GamePhase.DAY_DISCUSSION:
            phase_messages = await self.run_day_phase()
            self.game_state.next_phase()
        elif current_phase == GamePhase.DAY_VOTING:
            phase_messages = await self.run_voting_phase()
            if not self.check_victory():
                self._on_round_end(self.game_state.round_number)
                self.game_state.next_phase()

        return phase_messages

    def save_game(self, file_path: str | Path) -> None:
        """将当前游戏状态保存到文件。

        Args:
            file_path: 保存游戏状态的路径。

        Raises:
            RuntimeError: 游戏未初始化时抛出。
        """
        if not self.game_state:
            msg = "Game not initialized"
            raise RuntimeError(msg)

        save_game_state(self.game_state, file_path, event_logger=self.event_logger)

    def load_game(
        self, file_path: str | Path, agent_factory: dict[str, Any] | None = None
    ) -> None:
        """从文件加载游戏状态。

        Args:
            file_path: 加载游戏状态的路径。
            agent_factory: 可选字典，将 player_id 映射到 agent 实例。
                          若未提供，玩家将没有 agent。

        Note:
            Agent 无法序列化，需手动重新创建。
            传入 player_id 到 agent 实例的映射字典以恢复 agent。
        """
        from llm_werewolf.game_runtime.state.serialization import load_game_state_snapshot

        snapshot = load_game_state_snapshot(file_path)
        self.game_state = load_game_state(file_path, agent_factory)
        if agent_factory:
            for idx, player in enumerate(self.game_state.players, start=1):
                agent = agent_factory.get(player.player_id)
                if agent is not None:
                    self._attach_agent_to_player(player, agent, idx)
        self._wire_game_state()
        if snapshot.events:
            self.event_logger = restore_event_logger(snapshot.events)
        else:
            self.event_logger.clear_events()
