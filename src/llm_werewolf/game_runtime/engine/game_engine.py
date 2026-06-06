"""组合所有 Mixin 的主 GameEngine 类。"""

from llm_werewolf.game_runtime.engine.base import GameEngineBase
from llm_werewolf.game_runtime.engine.day_phase import DayPhaseMixin
from llm_werewolf.game_runtime.engine.night_phase import NightPhaseMixin
from llm_werewolf.game_runtime.engine.voting_phase import VotingPhaseMixin
from llm_werewolf.game_runtime.engine.death_handler import DeathHandlerMixin
from llm_werewolf.game_runtime.engine.action_processor import ActionProcessorMixin
from llm_werewolf.game_runtime.engine.sheriff_election import SheriffElectionMixin


class GameEngine(
    DeathHandlerMixin,
    ActionProcessorMixin,
    NightPhaseMixin,
    SheriffElectionMixin,
    DayPhaseMixin,
    VotingPhaseMixin,
    GameEngineBase,
):
    """控制狼人杀流程的核心游戏引擎。

    本类通过多个 Mixin 组织游戏逻辑：
    - GameEngineBase：核心初始化与主循环
    - DeathHandlerMixin：死亡相关逻辑（狼刀、恋人殉情等）
    - ActionProcessorMixin：处理游戏行动
    - NightPhaseMixin：夜晚阶段执行
    - SheriffElectionMixin：警长选举阶段执行
    - DayPhaseMixin：白天讨论阶段执行
    - VotingPhaseMixin：投票阶段执行
    """

    def describe(self) -> str:
        """返回当前对局摘要，便于日志与调试。"""
        state = self.game_state
        if state is None:
            return "GameEngine(state=uninitialized)"
        alive = state.get_alive_players()
        return (
            f"GameEngine(phase={state.phase.value}, round={state.round_number}, "
            f"alive={len(alive)}/{len(state.players)}, winner={state.winner!r})"
        )

    def __repr__(self) -> str:
        return self.describe()
