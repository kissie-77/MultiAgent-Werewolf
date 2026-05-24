from llm_werewolf.game_runtime.types import ActionType, Camp, PlayerProtocol, GameStateProtocol
from llm_werewolf.game_runtime.actions.base import Action
from llm_werewolf.game_runtime.roles.names import player_camp_is, seer_apparent_camp


class WitchSaveAction(Action):
    """女巫救药行动。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化女巫救人行动。

        Args:
            actor: 执行行动的女巫。
            target: 要救的目标玩家。
            game_state: 当前游戏状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """获取行动类型。"""
        return ActionType.WITCH_SAVE

    def validate(self) -> bool:
        """校验救人行动。"""
        # 检查执行者是否具有女巫能力（has_save_potion 属性）
        if not hasattr(self.actor.role, "has_save_potion"):
            return False

        if self.game_state.werewolf_target != self.target.player_id:
            return False

        return self.actor.is_alive() and self.actor.role.has_save_potion

    def execute(self) -> list[str]:
        """执行女巫救人。"""
        # 更新女巫解药状态
        if hasattr(self.actor.role, "has_save_potion"):
            self.actor.role.has_save_potion = False
        self.game_state.witch_save_used = True
        self.game_state.witch_saved_target = self.target.player_id
        return [f"Witch saves {self.target.name}"]


class WitchPoisonAction(Action):
    """女巫毒药行动。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化女巫毒杀行动。

        Args:
            actor: 执行行动的女巫。
            target: 要毒杀的目标玩家。
            game_state: 当前游戏状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """获取行动类型。"""
        return ActionType.WITCH_POISON

    def validate(self) -> bool:
        """校验毒杀行动。"""
        # 检查执行者是否具有女巫能力（has_poison_potion 属性）
        if not hasattr(self.actor.role, "has_poison_potion"):
            return False
        return (
            self.actor.is_alive() and self.actor.role.has_poison_potion and self.target.is_alive()
        )

    def execute(self) -> list[str]:
        """执行女巫毒杀。"""
        # 更新女巫毒药状态
        if hasattr(self.actor.role, "has_poison_potion"):
            self.actor.role.has_poison_potion = False
        self.game_state.witch_poison_used = True
        self.game_state.witch_poison_target = self.target.player_id
        return [f"Witch poisons {self.target.name}"]


class SeerCheckAction(Action):
    """预言家查验行动。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化预言家查验行动。

        Args:
            actor: 执行行动的预言家。
            target: 要查验的目标玩家。
            game_state: 当前游戏状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """获取行动类型。"""
        return ActionType.SEER_CHECK

    def validate(self) -> bool:
        """校验预言家查验。"""
        return self.actor.is_alive() and self.target.is_alive()

    def execute(self) -> list[str]:
        """执行预言家查验。"""
        apparent = seer_apparent_camp(self.target)
        self.game_state.seer_checked[self.game_state.round_number] = self.target.player_id
        return [f"Seer checks {self.target.name}: {apparent.value}"]


class GuardProtectAction(Action):
    """守卫保护行动。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化守卫保护行动。

        Args:
            actor: 执行行动的守卫。
            target: 要保护的目标玩家。
            game_state: 当前游戏状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """获取行动类型。"""
        return ActionType.GUARD_PROTECT

    def validate(self) -> bool:
        """校验守卫保护。"""
        # 检查执行者是否具有守卫能力（last_protected 属性）
        if not hasattr(self.actor.role, "last_protected"):
            return False

        if self.actor.role.last_protected == self.target.player_id:
            return False

        return self.actor.is_alive() and self.target.is_alive()

    def execute(self) -> list[str]:
        """执行守卫保护。"""
        # 更新守卫上一夜保护目标
        if hasattr(self.actor.role, "last_protected"):
            self.actor.role.last_protected = self.target.player_id

        self.game_state.guard_protected = self.target.player_id
        return [f"Guard protects {self.target.name}"]


class CupidLinkAction(Action):
    """丘比特连结两名恋人的行动。"""

    def __init__(
        self,
        actor: PlayerProtocol,
        target1: PlayerProtocol,
        target2: PlayerProtocol,
        game_state: GameStateProtocol,
    ) -> None:
        """初始化丘比特连结行动。

        Args:
            actor: 执行行动的丘比特。
            target1: 连结的第一名玩家。
            target2: 连结的第二名玩家。
            game_state: 当前游戏状态。
        """
        super().__init__(actor, game_state)
        self.target1 = target1
        self.target2 = target2

    def get_action_type(self) -> ActionType:
        """获取行动类型。"""
        return ActionType.CUPID_LINK

    def validate(self) -> bool:
        """校验丘比特连结。"""
        # 检查执行者是否具有丘比特能力（has_linked 属性）
        if not hasattr(self.actor.role, "has_linked"):
            return False

        if self.actor.role.has_linked:
            return False

        return (
            self.actor.is_alive()
            and self.target1.is_alive()
            and self.target2.is_alive()
            and self.target1.player_id != self.target2.player_id
        )

    def execute(self) -> list[str]:
        """执行丘比特连结。"""
        self.target1.set_lover(self.target2.player_id)
        self.target2.set_lover(self.target1.player_id)

        # 更新丘比特 has_linked 状态
        if hasattr(self.actor.role, "has_linked"):
            self.actor.role.has_linked = True

        return [f"Cupid links {self.target1.name} and {self.target2.name} as lovers"]


class RavenMarkAction(Action):
    """乌鸦标记玩家以获得额外票权的行动。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化乌鸦标记行动。

        Args:
            actor: 执行行动的乌鸦。
            target: 要标记的目标玩家。
            game_state: 当前游戏状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """获取行动类型。"""
        return ActionType.RAVEN_MARK

    def validate(self) -> bool:
        """校验乌鸦标记。"""
        return self.actor.is_alive() and self.target.is_alive()

    def execute(self) -> list[str]:
        """执行乌鸦标记。"""
        self.game_state.raven_marked = self.target.player_id
        return [f"Raven marks {self.target.name}"]


class GraveyardKeeperCheckAction(Action):
    """守墓人查验死亡玩家的行动。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化守墓人查验行动。

        Args:
            actor: 执行行动的守墓人。
            target: 要查验的死亡玩家。
            game_state: 当前游戏状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """获取行动类型。"""
        return ActionType.GRAVEYARD_KEEPER_CHECK

    def validate(self) -> bool:
        """校验守墓人查验。"""
        return self.actor.is_alive() and not self.target.is_alive()

    def execute(self) -> list[str]:
        """执行守墓人查验。"""
        camp = self.target.get_camp().value
        role_name = self.target.get_role_name()
        self.game_state.graveyard_checked[self.game_state.round_number] = self.target.player_id
        return [
            f"Graveyard Keeper checks {self.target.name}: They were a {role_name} ({camp} camp)"
        ]


class KnightDuelAction(Action):
    """骑士白天决斗的行动。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化骑士决斗行动。

        Args:
            actor: 执行行动的骑士。
            target: 决斗目标玩家。
            game_state: 当前游戏状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """获取行动类型。"""
        return ActionType.KNIGHT_DUEL

    def validate(self) -> bool:
        """校验骑士决斗。"""
        # 检查执行者是否具有骑士能力（has_dueled 属性）
        if not hasattr(self.actor.role, "has_dueled"):
            return False

        if self.actor.role.has_dueled:
            return False

        return self.actor.is_alive() and self.target.is_alive()

    def execute(self) -> list[str]:
        """执行骑士决斗。"""
        messages = []

        if player_camp_is(self.target, Camp.WEREWOLF):
            self.target.kill()
            self.game_state.day_deaths.add(self.target.player_id)
            messages.append(f"Knight {self.actor.name} duels and defeats {self.target.name}!")
        else:
            self.actor.kill()
            self.game_state.day_deaths.add(self.actor.player_id)
            messages.append(f"Knight {self.actor.name} loses the duel and dies!")

        # 更新骑士 has_dueled 状态
        if hasattr(self.actor.role, "has_dueled"):
            self.actor.role.has_dueled = True

        return messages
