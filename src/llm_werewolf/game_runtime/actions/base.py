from abc import ABC, abstractmethod

from llm_werewolf.game_runtime.types import ActionType, PlayerProtocol, GameStateProtocol


class Action(ABC):
    """所有游戏行动的抽象基类。"""

    def __init__(self, actor: PlayerProtocol, game_state: GameStateProtocol) -> None:
        """初始化行动。

        Args:
            actor: 执行行动的玩家。
            game_state: 当前游戏状态。
        """
        self.actor = actor
        self.game_state = game_state

    @abstractmethod
    def get_action_type(self) -> ActionType:
        """获取本行动的类型。

        Returns:
            ActionType: 行动类型。
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """校验行动是否可以执行。

        Returns:
            bool: 合法则为 True。
        """
        pass

    @abstractmethod
    def execute(self) -> list[str]:
        """执行行动。

        Returns:
            list[str]: 描述行动结果的消息列表。
        """
        pass
