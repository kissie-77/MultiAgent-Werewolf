"""LLM 狼人杀游戏的协议定义。

本模块定义结构化类型协议，以避免循环导入。
协议描述对象接口，无需实际导入具体类型。

注意：本文件使用 ``from __future__ import annotations``，因为 Protocol 类
存在相互引用（RoleProtocol 引用 PlayerProtocol，反之亦然）。
这是延迟求值类型注解的合理场景，此处仅为纯类型定义，不含实现逻辑。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types.enums import (
        Camp,
        GamePhase,
        ActionType,
        PlayerStatus,
        ActionPriority,
    )
    from llm_werewolf.game_runtime.types.models import PlayerInfo, RoleConfig


@runtime_checkable
class AgentProtocol(Protocol):
    """智能体对象的协议。"""

    name: str
    model: str

    async def get_response(self, message: str) -> str:
        """从智能体获取响应。

        Args:
            message: 提示消息。

        Returns:
            str: 智能体的响应。
        """
        ...

    def add_decision(self, decision: str) -> None:
        """记录决策的安全摘要。"""
        ...

    def get_decision_context(self) -> str:
        """返回用于提示的安全决策历史。"""
        ...


@runtime_checkable
class RoleProtocol(Protocol):
    """角色对象的协议。"""

    player: PlayerProtocol
    ability_uses: int
    config: RoleConfig
    disabled: bool

    @property
    def name(self) -> str:
        """获取角色名称。"""
        ...

    @property
    def camp(self) -> Camp:
        """获取角色阵营。"""
        ...

    @property
    def description(self) -> str:
        """获取角色描述。"""
        ...

    @property
    def priority(self) -> ActionPriority | None:
        """获取行动优先级。"""
        ...

    def get_config(self) -> RoleConfig:
        """获取该角色的配置。"""
        ...

    def can_act_tonight(self, player: PlayerProtocol, round_number: int) -> bool:
        """检查该角色今晚是否可以行动。"""
        ...

    def can_act_today(self, player: PlayerProtocol) -> bool:
        """检查该角色今天是否可以行动。"""
        ...

    def get_night_actions(self, game_state: GameStateProtocol) -> list[ActionProtocol]:
        """获取该角色的夜间行动列表。"""
        ...


@runtime_checkable
class PlayerProtocol(Protocol):
    """玩家对象的协议。"""

    player_id: str
    name: str
    role: RoleProtocol
    agent: AgentProtocol | None
    ai_model: str
    statuses: set[PlayerStatus]
    lover_partner_id: str | None
    can_vote_flag: bool

    def is_alive(self) -> bool:
        """检查玩家是否存活。"""
        ...

    def kill(self) -> None:
        """将玩家标记为死亡。"""
        ...

    def revive(self) -> None:
        """复活玩家。"""
        ...

    def add_status(self, status: PlayerStatus) -> None:
        """为玩家添加状态。"""
        ...

    def remove_status(self, status: PlayerStatus) -> None:
        """移除玩家的状态。"""
        ...

    def has_status(self, status: PlayerStatus) -> bool:
        """检查玩家是否具有指定状态。"""
        ...

    def can_vote(self) -> bool:
        """检查玩家是否可以投票。"""
        ...

    def disable_voting(self) -> None:
        """禁用玩家的投票权。"""
        ...

    def set_lover(self, partner_id: str) -> None:
        """将该玩家与另一玩家设为情侣。"""
        ...

    def is_lover(self) -> bool:
        """检查玩家是否为情侣。"""
        ...

    def get_public_info(self) -> PlayerInfo:
        """获取玩家的公开信息。"""
        ...

    def get_role_name(self) -> str:
        """获取玩家的角色名称。"""
        ...

    def get_camp(self) -> Camp:
        """获取玩家的阵营。"""
        ...


@runtime_checkable
class GameStateProtocol(Protocol):
    """游戏状态对象的协议。"""

    players: list[PlayerProtocol]
    player_dict: dict[str, PlayerProtocol]
    phase: GamePhase
    round_number: int
    night_deaths: set[str]
    day_deaths: set[str]
    death_abilities_used: set[str]
    death_causes: dict[str, str]
    werewolf_target: str | None
    werewolf_votes: dict[str, str]
    witch_save_used: bool
    witch_poison_used: bool
    witch_saved_target: str | None
    witch_poison_target: str | None
    guard_protected: str | None
    guardian_wolf_protected: str | None
    nightmare_blocked: str | None
    seer_checked: dict[int, str]
    votes: dict[str, str]
    raven_marked: str | None
    winner: str | None
    sheriff_id: str | None
    sheriff_election_done: bool
    sheriff_votes: dict[str, str]

    def reset_deaths(self) -> None:
        """重置新回合的死亡集合。"""
        ...

    def get_phase(self) -> GamePhase:
        """获取当前游戏阶段。"""
        ...

    def set_phase(self, phase: GamePhase) -> None:
        """设置游戏阶段。"""
        ...

    def next_phase(self) -> GamePhase:
        """推进到下一阶段。"""
        ...

    def get_alive_players(self) -> list[PlayerProtocol]:
        """获取所有存活玩家。"""
        ...

    def get_player(self, player_id: str) -> PlayerProtocol | None:
        """按 ID 获取玩家。"""
        ...

    def get_players_by_camp(self, camp: Camp) -> list[PlayerProtocol]:
        """获取指定阵营的所有玩家。"""
        ...

    def count_alive_by_camp(self, camp: Camp) -> int:
        """统计指定阵营的存活玩家数。"""
        ...


@runtime_checkable
class ActionProtocol(Protocol):
    """行动对象的协议。"""

    actor: PlayerProtocol
    game_state: GameStateProtocol

    def get_action_type(self) -> ActionType:
        """获取该行动的类型。"""
        ...

    def validate(self) -> bool:
        """校验该行动是否可以执行。"""
        ...

    def execute(self) -> list[str] | None:
        """执行该行动。"""
        ...
