from __future__ import annotations

from typing import TYPE_CHECKING

from llm_werewolf.game_runtime.types import Camp, Event, GamePhase, GameStateInfo, PlayerProtocol

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction


class GameState:
    """管理狼人杀游戏的当前状态。"""

    def __init__(self, players: list[PlayerProtocol]) -> None:
        """初始化游戏状态。

        Args:
            players: 游戏中所有玩家的列表。
        """
        self.players = players
        self.player_dict = {p.player_id: p for p in players}

        self.phase = GamePhase.SETUP
        self.round_number = 0

        self.event_history: list[Event] = []
        self.night_deaths: set[str] = set()
        self.day_deaths: set[str] = set()
        self.death_abilities_used: set[str] = set()
        self.death_causes: dict[str, str] = {}

        self.werewolf_target: str | None = None
        self.werewolf_votes: dict[str, str] = {}
        self.witch_save_used = False
        self.witch_poison_used = False
        self.witch_saved_target: str | None = None
        self.witch_poison_target: str | None = None
        self.guard_protected: str | None = None
        self.guardian_wolf_protected: str | None = None
        self.nightmare_blocked: str | None = None
        self.seer_checked: dict[int, str] = {}
        self.graveyard_checked: dict[int, str] = {}
        self.wolf_beauty_charmed: str | None = None  # 狼美人魅惑目标

        self.votes: dict[str, str] = {}
        self.raven_marked: str | None = None

        self.enable_sheriff = False
        self.sheriff_id: str | None = None
        self.sheriff_election_done = False
        self.sheriff_votes: dict[str, str] = {}
        self.sheriff_tie_count = 0  # 记录平票重投次数（0=首次选举，1=首次平票重投）
        self.vote_tie_count = 0  # 记录投票平票重投次数（0=首次投票，1=首次平票重投）

        self.winner: str | None = None

        self.information_hub: object | None = None
        self.phase_interaction: PhaseInteraction | None = None
        self.track_vote_intentions = False
        self.vote_intention_tracker = None

        self.night_timeout: int | None = None
        self.day_timeout: int | None = None
        self.vote_timeout: int | None = None
        self.allow_revote = False
        self.show_role_on_death = True

    def get_alive_witch_player_ids(self) -> list[str]:
        """返回存活女巫的玩家 ID 列表（用于刀口等仅女巫可见的事件）。"""
        return [p.player_id for p in self.get_alive_players() if p.get_role_name() == "Witch"]

    def require_phase_interaction(self) -> PhaseInteraction:
        """返回为本局游戏注入的阶段交互 API。"""
        if self.phase_interaction is None:
            msg = "PhaseInteraction is not initialized on GameState"
            raise RuntimeError(msg)
        return self.phase_interaction

    def reset_deaths(self) -> None:
        """重置新一轮游戏的死亡记录。"""
        self.night_deaths.clear()
        self.day_deaths.clear()
        self.death_abilities_used.clear()
        self.death_causes.clear()

    def get_phase(self) -> GamePhase:
        """获取当前游戏阶段。

        Returns:
            GamePhase: 当前阶段。
        """
        return self.phase

    def set_phase(self, phase: GamePhase) -> None:
        """设置游戏阶段。

        Args:
            phase: 要设置的新阶段。
        """
        if phase == GamePhase.NIGHT and self.round_number == 0:
            self.round_number = 1
        self.phase = phase

    def next_phase(self) -> GamePhase:
        """推进到下一个游戏阶段。

        Returns:
            GamePhase: 新阶段。
        """
        if self.phase == GamePhase.SETUP:
            self.phase = GamePhase.NIGHT
            self.round_number = 1
        elif self.phase == GamePhase.NIGHT:
            # 首夜结束后，若开启警长且尚未完成选举则进入警长竞选
            if self.round_number == 1 and self.enable_sheriff and not self.sheriff_election_done:
                self.phase = GamePhase.SHERIFF_ELECTION
            else:
                self.phase = GamePhase.DAY_DISCUSSION
        elif self.phase == GamePhase.SHERIFF_ELECTION:
            self.phase = GamePhase.DAY_DISCUSSION
        elif self.phase == GamePhase.DAY_DISCUSSION:
            self.phase = GamePhase.DAY_VOTING
            self.vote_tie_count = 0
        elif self.phase == GamePhase.DAY_VOTING:
            self.phase = GamePhase.NIGHT
            self.round_number += 1
            self.night_deaths.clear()
            self.day_deaths.clear()
            self.votes.clear()
            self.werewolf_target = None
            self.werewolf_votes.clear()
            self.witch_saved_target = None
            self.witch_poison_target = None
            self.guard_protected = None
            self.guardian_wolf_protected = None
            self.nightmare_blocked = None
            self.raven_marked = None

        return self.phase

    def get_alive_players(self, except_ids: list[str] | None = None) -> list[PlayerProtocol]:
        """获取所有存活玩家。

        Args:
            except_ids: 可选，要排除的玩家 ID 列表。

        Returns:
            list[Player]: 存活玩家列表。
        """
        alive = [p for p in self.players if p.is_alive()]
        if except_ids:
            alive = [p for p in alive if p.player_id not in except_ids]
        return alive

    def get_dead_players(self) -> list[PlayerProtocol]:
        """获取所有已死亡玩家。

        Returns:
            list[Player]: 已死亡玩家列表。
        """
        return [p for p in self.players if not p.is_alive()]

    def get_players_with_night_actions(self) -> list[PlayerProtocol]:
        """获取所有拥有夜间技能的存活玩家。"""
        return [p for p in self.get_alive_players() if p.role.has_night_action(self)]

    def get_player(self, player_id: str) -> PlayerProtocol | None:
        """按 ID 获取玩家。

        Args:
            player_id: 玩家 ID。

        Returns:
            Player | None: 玩家对象，未找到则返回 None。
        """
        return self.player_dict.get(player_id)

    def get_players_by_camp(self, camp: Camp) -> list[PlayerProtocol]:
        """获取指定阵营的所有玩家。

        Args:
            camp: 阵营枚举。

        Returns:
            list[Player]: 该阵营的玩家列表。
        """
        return [p for p in self.players if p.get_camp() == camp]

    def count_alive_by_camp(self, camp: Camp) -> int:
        """统计指定阵营的存活玩家数量。

        Args:
            camp: 阵营枚举。

        Returns:
            int: 该阵营存活玩家数。
        """
        return sum(1 for p in self.get_alive_players() if p.get_camp() == camp)

    def record_event(self, event: Event) -> None:
        """将游戏事件记录到历史中。

        Args:
            event: 要记录的事件。
        """
        self.event_history.append(event)

    def get_recent_events(self, count: int = 10) -> list[Event]:
        """获取最近的事件。

        Args:
            count: 要获取的事件数量。

        Returns:
            list[Event]: 最近的事件列表。
        """
        return self.event_history[-count:]

    def add_vote(self, voter_id: str, target_id: str) -> None:
        """记录一次投票。

        Args:
            voter_id: 投票玩家的 ID。
            target_id: 被投票玩家的 ID。
        """
        self.votes[voter_id] = target_id

    def get_vote_counts(self) -> dict[str, float]:
        """获取每位玩家的得票数。

        Returns:
            dict[str, float]: 玩家 ID 到得票数的映射（浮点数以支持警长 1.5 票）。
        """
        vote_counts: dict[str, float] = {}
        for voter_id, target_id in self.votes.items():
            voter = self.get_player(voter_id)
            if not voter or not voter.is_alive() or not voter.can_vote():
                continue
            vote_weight = voter.get_vote_weight()
            vote_counts[target_id] = vote_counts.get(target_id, 0.0) + vote_weight

        # 加上渡鸦标记（额外 1 票）
        if self.raven_marked and self.raven_marked in vote_counts:
            vote_counts[self.raven_marked] += 1
        elif self.raven_marked:
            vote_counts[self.raven_marked] = 1.0

        return vote_counts

    def has_sheriff(self) -> bool:
        """检查是否存在警长。

        Returns:
            bool: 若存在警长则为 True。
        """
        return self.sheriff_id is not None

    def get_sheriff(self) -> PlayerProtocol | None:
        """获取当前警长。

        Returns:
            PlayerProtocol | None: 警长玩家，若无警长则返回 None。
        """
        if self.sheriff_id:
            return self.get_player(self.sheriff_id)
        return None

    def set_sheriff(self, player_id: str) -> None:
        """将某玩家设为警长。

        Args:
            player_id: 要设为警长的玩家 ID。
        """
        # 若已有警长，先移除其警长身份
        if self.sheriff_id:
            prev_sheriff = self.get_player(self.sheriff_id)
            if prev_sheriff:
                prev_sheriff.remove_sheriff()

        # 设置新警长
        self.sheriff_id = player_id
        player = self.get_player(player_id)
        if player:
            player.make_sheriff()

    def remove_sheriff(self) -> None:
        """移除当前警长（例如撕毁警徽时）。"""
        if self.sheriff_id:
            sheriff = self.get_player(self.sheriff_id)
            if sheriff:
                sheriff.remove_sheriff()
            self.sheriff_id = None

    def get_public_info(self) -> GameStateInfo:
        """获取游戏状态的公开信息。

        Returns:
            GameStateInfo: 公开的游戏状态信息。
        """
        alive = self.get_alive_players()
        return GameStateInfo(
            phase=self.phase,
            round_number=self.round_number,
            total_players=len(self.players),
            alive_players=len(alive),
            werewolves_alive=self.count_alive_by_camp(Camp.WEREWOLF),
            villagers_alive=self.count_alive_by_camp(Camp.VILLAGER),
        )

    def __repr__(self) -> str:
        """游戏状态的字符串表示。

        Returns:
            str: 游戏状态表示。
        """
        return (
            f"GameState(phase={self.phase.value}, round={self.round_number}, "
            f"alive={len(self.get_alive_players())}/{len(self.players)})"
        )
