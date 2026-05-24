from abc import ABC, abstractmethod

from llm_werewolf.core.roles.catalog import get_definition_by_role_class
from llm_werewolf.core.types import (
    Camp,
    RoleConfig,
    ActionPriority,
    ActionProtocol,
    PlayerProtocol,
    GameStateProtocol,
)
class Role(ABC):
    """狼人杀游戏中所有角色的抽象基类。"""

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化角色。"""
        self.player = player
        self.ability_uses = 0
        self.config = self.get_config()
        self._apply_catalog_description()
        self.disabled = False  # 为 True 时角色技能被禁用

    def _apply_catalog_description(self) -> None:
        try:
            from llm_werewolf.core.prompts.manager import PromptManager

            definition = get_definition_by_role_class(type(self))
            description = PromptManager.get_role_description(definition)
            self.config = self.config.model_copy(update={"description": description})
        except KeyError:
            pass

    @abstractmethod
    def get_config(self) -> RoleConfig:
        """获取本角色的配置。

        Returns:
            RoleConfig: 角色配置。
        """
        pass

    @property
    def name(self) -> str:
        """获取角色名称。

        Returns:
            str: 角色名称。
        """
        return self.config.name

    @property
    def camp(self) -> Camp:
        """获取角色阵营。

        Returns:
            Camp: 角色所属阵营。
        """
        return self.config.camp

    @property
    def description(self) -> str:
        """获取角色描述。

        Returns:
            str: 角色技能说明。
        """
        return self.config.description

    @property
    def priority(self) -> ActionPriority | None:
        """获取行动优先级。

        Returns:
            ActionPriority | None: 夜间行动优先级；无夜间行动时为 None。
        """
        return self.config.priority

    def can_act_tonight(self, player: PlayerProtocol, round_number: int) -> bool:
        """检查本角色今夜是否可以行动。

        Args:
            player: 持有本角色的玩家。
            round_number: 当前回合数。

        Returns:
            bool: 今夜可行动则为 True。
        """
        if self.disabled:
            return False

        if not self.config.can_act_night:
            return False

        if not player.is_alive():
            return False

        return not (self.config.max_uses is not None and self.ability_uses >= self.config.max_uses)

    def can_act_today(self, player: PlayerProtocol) -> bool:
        """检查本角色今日是否可以行动。

        Args:
            player: 持有本角色的玩家。

        Returns:
            bool: 今日可行动则为 True。
        """
        if self.disabled:
            return False

        if not self.config.can_act_day:
            return False

        return player.is_alive()

    def get_action_prompt(self, player: PlayerProtocol, game_state: object) -> str:
        """获取本角色需要行动时给 AI 智能体的提示词。

        Args:
            player: 持有本角色的玩家。
            game_state: 当前游戏状态。

        Returns:
            str: 给 AI 智能体的提示字符串。
        """
        try:
            from llm_werewolf.core.prompts.manager import PromptManager

            definition = get_definition_by_role_class(type(self))
            return (
                f"{PromptManager.build_identity_prompt(definition)}\n"
                f"玩家名：{player.name}\n技能说明：{self.description}"
            )
        except KeyError:
            return f"你是{player.name}，身份：{self.name}。{self.description}"

    def get_private_notes(self, game_state: GameStateProtocol | None = None) -> list[str]:
        """返回仅该玩家可见的角色相关事实。"""
        return [f"你的身份是 {self.name}。", self.description]

    async def get_night_actions(self, game_state: GameStateProtocol) -> list[ActionProtocol]:
        """通过 PhaseInteraction / InformationHub 收集夜间行动。"""
        interaction = getattr(game_state, "phase_interaction", None)
        if interaction is None:
            return []
        from llm_werewolf.core.role_night_plans import dispatch_night_plan

        return await dispatch_night_plan(self, game_state, interaction)

    def has_night_action(self, game_state: GameStateProtocol) -> bool:
        """检查角色是否具有夜间行动。

        Args:
            game_state: 当前游戏状态。

        Returns:
            bool: 有夜间行动则为 True。
        """
        if self.disabled:
            return False

        if (
            hasattr(game_state, "nightmare_blocked")
            and game_state.nightmare_blocked
            and self.player
            and self.player.player_id == game_state.nightmare_blocked
        ):
            return False

        return self.config.can_act_night

    def validate_action(
        self, actor: PlayerProtocol, target: PlayerProtocol | None, action_data: dict
    ) -> bool:
        """校验行动是否合法。

        Args:
            actor: 执行行动的玩家。
            target: 目标玩家（若有）。
            action_data: 附加行动数据。

        Returns:
            bool: 行动合法则为 True。
        """
        return True

    def use_ability(self) -> None:
        """标记技能已使用。"""
        self.ability_uses += 1

    def __str__(self) -> str:
        """角色的字符串表示。

        Returns:
            str: 角色名称。
        """
        return self.name

    def __repr__(self) -> str:
        """角色的 repr 表示。

        Returns:
            str: 角色表示。
        """
        return f"{self.__class__.__name__}()"
