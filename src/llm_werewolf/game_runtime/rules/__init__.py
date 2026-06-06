"""游戏规则：胜负判定与死亡技能。"""

from llm_werewolf.game_runtime.rules.victory import VictoryChecker
from llm_werewolf.game_runtime.rules.death_abilities import DEATH_ABILITY_ROLE_NAMES

__all__ = ["DEATH_ABILITY_ROLE_NAMES", "VictoryChecker"]
