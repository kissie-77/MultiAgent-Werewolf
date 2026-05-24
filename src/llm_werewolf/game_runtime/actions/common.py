from llm_werewolf.game_runtime.types import ActionType, PlayerProtocol, GameStateProtocol
from llm_werewolf.game_runtime.actions.base import Action


class VoteAction(Action):
    """白天投票行动。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化投票行动。

        Args:
            actor: 投票的玩家。
            target: 被投票的玩家。
            game_state: 当前游戏状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """获取行动类型。"""
        return ActionType.VOTE

    def validate(self) -> bool:
        """校验投票。"""
        return (
            self.actor.can_vote()
            and self.target.is_alive()
            and self.actor.player_id != self.target.player_id
        )

    def execute(self) -> list[str]:
        """执行投票。"""
        self.game_state.add_vote(self.actor.player_id, self.target.player_id)
        return [f"{self.actor.name} votes for {self.target.name}"]


class HunterShootAction(Action):
    """猎人死亡时开枪行动。"""

    def __init__(
        self, actor: PlayerProtocol, target: PlayerProtocol, game_state: GameStateProtocol
    ) -> None:
        """初始化猎人开枪行动。

        Args:
            actor: 执行行动的猎人。
            target: 射击目标。
            game_state: 当前游戏状态。
        """
        super().__init__(actor, game_state)
        self.target = target

    def get_action_type(self) -> ActionType:
        """获取行动类型。"""
        return ActionType.HUNTER_SHOOT

    def validate(self) -> bool:
        """校验猎人开枪。"""
        return not self.actor.is_alive() and self.target.is_alive()

    def execute(self) -> list[str]:
        """执行猎人开枪。"""
        self.target.kill()
        self.game_state.night_deaths.add(self.target.player_id)
        return [f"Hunter {self.actor.name} shoots {self.target.name}"]
