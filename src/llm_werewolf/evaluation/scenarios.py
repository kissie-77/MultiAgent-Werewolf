from pydantic import BaseModel, Field

from llm_werewolf.core.config import create_game_config_from_player_count


class EvaluationScenario(BaseModel):
    """一个可复现的离线评测场景。

    场景只描述“怎么创建一局游戏”，不直接运行游戏。
    runner 会根据这些字段创建 GameEngine、DemoAgent 和角色列表。
    """

    # 场景名会进入 game_id、manifest 和报告，用于区分不同实验配置。
    name: str
    # 玩家数量必须符合当前 GameConfig 的 6-20 人约束。
    num_players: int = Field(ge=6, le=20)
    # 明确写出角色列表，避免评测时因为默认配置变化导致结果不可复现。
    role_names: list[str]
    language: str = "en-US"
    # 基础随机种子；多局 repetition 会在此基础上递增。
    seed: int = 1
    # 单局硬超时，防止异步流程卡住后阻塞整批评测。
    timeout_seconds: float = 30.0
    repetitions: int = Field(default=1, ge=1)


def smoke_6p_basic(
    seed: int = 1,
    repetitions: int = 1,
    timeout_seconds: float = 30.0,
) -> EvaluationScenario:
    """创建 6 人基础 smoke 场景。

    这个场景不依赖 API，适合开发时快速验证 runner、recorder 和报告链路。
    """
    return EvaluationScenario(
        name="smoke_6p_basic",
        num_players=6,
        role_names=["Werewolf", "Werewolf", "Seer", "Witch", "Villager", "Villager"],
        seed=seed,
        timeout_seconds=timeout_seconds,
        repetitions=repetitions,
    )


def regression_default_demo(
    seed: int = 1,
    repetitions: int = 1,
    timeout_seconds: float = 30.0,
) -> EvaluationScenario:
    """创建默认 16 人 demo 回归场景。

    它使用项目当前按人数自动分配出的角色组合，适合捕获复杂默认路径中的问题。
    """
    config = create_game_config_from_player_count(16)
    return EvaluationScenario(
        name="regression_default_demo",
        num_players=config.num_players,
        role_names=config.role_names,
        language="zh-TW",
        seed=seed,
        timeout_seconds=timeout_seconds,
        repetitions=repetitions,
    )


def get_scenario(
    name: str,
    games: int = 1,
    seed: int = 1,
    timeout_seconds: float = 30.0,
) -> EvaluationScenario:
    """按名称解析内置场景。

    CLI 入口只暴露字符串参数，通过这个函数集中维护可用场景列表。
    """
    if name == "smoke_6p_basic":
        return smoke_6p_basic(seed=seed, repetitions=games, timeout_seconds=timeout_seconds)
    if name == "regression_default_demo":
        return regression_default_demo(seed=seed, repetitions=games, timeout_seconds=timeout_seconds)

    msg = f"Unknown evaluation scenario: {name}"
    raise ValueError(msg)
