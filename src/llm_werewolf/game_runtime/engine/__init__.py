"""LLM 狼人杀游戏引擎模块。

本模块将核心引擎功能拆分到多个文件：
- base.py：引擎初始化与主循环
- night_phase.py：夜晚阶段逻辑
- day_phase.py：白天讨论阶段逻辑
- voting_phase.py：投票阶段逻辑
- death_handler.py：死亡相关逻辑（击杀、恋人殉情等）
- action_processor.py：动作处理逻辑

GameEngine 类通过 Mixin 组合上述组件。
"""

from llm_werewolf.game_runtime.engine.game_engine import GameEngine

__all__ = ["GameEngine"]
