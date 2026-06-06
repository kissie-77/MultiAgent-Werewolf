from llm_werewolf.game_runtime.types import ActionType, PlayerProtocol, GameStateProtocol
from llm_werewolf.game_runtime.roles.names import (
    RoleNames,
    role_name_is,
    participates_in_wolf_team,
)
from llm_werewolf.game_runtime.actions.base import Action


class WerewolfVoteAction(Action):
    """狼人投票选择击杀目标。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化狼人投票行动。

        Args:
            actor: 发起投票的狼人。
            target: 被投票的目标玩家。
            game_state: 当前对局状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """返回行动类型。"""
        return ActionType.WEREWOLF_KILL

    def validate(self) -> bool:
        """校验投票是否合法。"""
        return (
            self.actor.is_alive()
            and self.target.is_alive()
            and participates_in_wolf_team(self.actor)
            and not participates_in_wolf_team(self.target)
            and self.actor.player_id != self.target.player_id
        )

    def execute(self) -> list[str]:
        """执行狼人投票。"""
        self.game_state.werewolf_votes[self.actor.player_id] = self.target.player_id
        return []  # 不暴露各狼人的单独投票


class WerewolfKillAction(Action):
    """狼人击杀玩家（遗留实现，保留以兼容旧逻辑）。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化狼人击杀行动。

        Args:
            actor: 执行行动的狼人。
            target: 被击杀的目标玩家。
            game_state: 当前对局状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """返回行动类型。"""
        return ActionType.WEREWOLF_KILL

    def validate(self) -> bool:
        """校验击杀是否合法。"""
        return self.actor.is_alive() and self.target.is_alive()

    def execute(self) -> list[str]:
        """执行狼人击杀。"""
        self.game_state.werewolf_target = self.target.player_id
        return [f"Werewolves target {self.target.name}"]


class WhiteWolfKillAction(Action):
    """白狼王击杀另一名狼人。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化白狼王击杀行动。

        Args:
            actor: 执行行动的白狼王。
            target: 被击杀的狼人目标。
            game_state: 当前对局状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """返回行动类型。"""
        return ActionType.WHITE_WOLF_KILL

    def validate(self) -> bool:
        """校验白狼王击杀是否合法。"""
        if not role_name_is(self.actor.role, RoleNames.WHITE_WOLF):
            return False

        # 白狼王仅在奇数轮（1、3、5…）可行动
        if self.game_state.round_number % 2 == 0:
            return False

        if (
            hasattr(self.game_state, "guardian_wolf_protected")
            and self.game_state.guardian_wolf_protected == self.target.player_id
        ):
            return False

        return (
            self.actor.is_alive()
            and self.target.is_alive()
            and participates_in_wolf_team(self.target)
            and self.target.player_id != self.actor.player_id
        )

    def execute(self) -> list[str]:
        """执行白狼王击杀。"""
        if (
            hasattr(self.game_state, "guardian_wolf_protected")
            and self.game_state.guardian_wolf_protected == self.target.player_id
        ):
            return [
                f"White Wolf attempts to kill {self.target.name}, but they are protected by Guardian Wolf!"
            ]

        self.target.kill()
        self.game_state.night_deaths.add(self.target.player_id)
        self.game_state.death_causes[self.target.player_id] = "white_wolf"
        return [f"White Wolf kills werewolf {self.target.name}"]


class WolfBeautyCharmAction(Action):
    """狼美人魅惑玩家。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化狼美人魅惑行动。

        Args:
            actor: 执行行动的狼美人。
            target: 被魅惑的目标玩家。
            game_state: 当前对局状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """返回行动类型。"""
        return ActionType.WOLF_BEAUTY_CHARM

    def validate(self) -> bool:
        """校验魅惑是否合法。"""
        # 校验行动者是否具备 WolfBeauty 能力（charmed_player 属性）
        if not hasattr(self.actor.role, "charmed_player"):
            return False

        if self.actor.role.charmed_player:
            return False

        return self.actor.is_alive() and self.target.is_alive()

    def execute(self) -> list[str]:
        """执行狼美人魅惑。"""
        # 更新 WolfBeauty 的 charmed_player 状态
        if hasattr(self.actor.role, "charmed_player"):
            self.actor.role.charmed_player = self.target.player_id

        # 持久化到 game_state 防止序列化/重建时丢失
        self.game_state.wolf_beauty_charmed = self.target.player_id

        return [f"Wolf Beauty charms {self.target.name}"]


class GuardianWolfProtectAction(Action):
    """守墓狼保护一名狼人。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化守墓狼保护行动。

        Args:
            actor: 执行行动的守墓狼。
            target: 被保护的狼人。
            game_state: 当前对局状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """返回行动类型。"""
        return ActionType.GUARD_PROTECT

    def validate(self) -> bool:
        """校验保护是否合法。"""
        return (
            self.actor.is_alive()
            and self.target.is_alive()
            and participates_in_wolf_team(self.target)
            and self.actor.player_id != self.target.player_id
        )

    def execute(self) -> list[str]:
        """执行守墓狼保护。"""
        self.game_state.guardian_wolf_protected = self.target.player_id
        return [f"Guardian Wolf protects {self.target.name}"]


class NightmareWolfBlockAction(Action):
    """梦魇狼封锁玩家技能。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化梦魇狼封锁行动。

        Args:
            actor: 执行行动的梦魇狼。
            target: 被封锁的玩家。
            game_state: 当前对局状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """返回行动类型。"""
        return ActionType.NIGHTMARE_BLOCK

    def validate(self) -> bool:
        """校验封锁是否合法。"""
        return self.actor.is_alive() and self.target.is_alive()

    def execute(self) -> list[str]:
        """执行梦魇狼封锁。"""
        self.game_state.nightmare_blocked = self.target.player_id
        return [f"Nightmare Wolf blocks {self.target.name}"]
