# 导出所有枚举
from llm_werewolf.game_runtime.types.enums import (
    Camp,
    EventType,
    GamePhase,
    ActionType,
    VictoryGoal,
    PlayerStatus,
    ActionPriority,
)

# 导出所有模型（须在 PlayerObservation 之前，以便 Pydantic 解析前向引用）
from llm_werewolf.game_runtime.types.models import (
    Event,
    PlayerInfo,
    RoleConfig,
    GameStateInfo,
    VictoryResult,
)
from llm_werewolf.game_runtime.support.observation import PlayerObservation

PlayerObservation.model_rebuild()

# 导出所有协议
from llm_werewolf.game_runtime.types.protocols import (
    RoleProtocol,
    AgentProtocol,
    ActionProtocol,
    PlayerProtocol,
    GameStateProtocol,
)

__all__ = [
    # 枚举
    "ActionPriority",
    # 协议
    "ActionProtocol",
    "ActionType",
    "AgentProtocol",
    "Camp",
    # 模型
    "Event",
    "EventType",
    "GamePhase",
    "GameStateInfo",
    "GameStateProtocol",
    "PlayerInfo",
    "PlayerObservation",
    "PlayerProtocol",
    "PlayerStatus",
    "RoleConfig",
    "RoleProtocol",
    "VictoryGoal",
    "VictoryResult",
]
