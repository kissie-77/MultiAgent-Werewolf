import asyncio
from pathlib import Path

import fire

from llm_werewolf.paths import EVAL_RUNS_DIR
from llm_werewolf.evaluation.core.runner import EvaluationRunner
from llm_werewolf.evaluation.core.scenarios import get_scenario


def main(
    output_dir: str = str(EVAL_RUNS_DIR),
    scenario: str = "smoke_6p_basic",
    games: int = 10,
    timeout_seconds: float = 30.0,
    seed: int = 1,
) -> str:
    """运行离线游戏正确性评测。

    Args:
        output_dir: 评测产物输出目录。
        scenario: 内置场景名，例如 smoke_6p_basic。
        games: 要运行的局数。
        timeout_seconds: 单局硬超时时间。
        seed: 基础随机种子；多局运行时每局递增。

    Returns:
        str: 输出目录路径，便于 CLI 和测试读取。
    """
    resolved_output = Path(output_dir)
    # CLI 只负责把参数翻译成 EvaluationScenario，真正的运行逻辑交给 runner。
    eval_scenario = get_scenario(
        name=scenario, games=games, seed=seed, timeout_seconds=timeout_seconds
    )
    runner = EvaluationRunner(output_dir=resolved_output, scenarios=[eval_scenario])
    # fire 入口是同步函数，因此这里用 asyncio.run 启动异步 runner。
    asyncio.run(runner.run())
    return str(resolved_output)


def entry() -> None:
    """`werewolf-eval` 命令入口。"""
    fire.Fire(main)


if __name__ == "__main__":
    entry()
