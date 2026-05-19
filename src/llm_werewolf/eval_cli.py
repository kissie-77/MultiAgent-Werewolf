import asyncio
from pathlib import Path

import fire

from llm_werewolf.evaluation.runner import EvaluationRunner
from llm_werewolf.evaluation.scenarios import get_scenario


def main(
    output_dir: str = "eval_runs",
    scenario: str = "smoke_6p_basic",
    games: int = 10,
    timeout_seconds: float = 30.0,
    seed: int = 1,
) -> str:
    """Run offline game correctness evaluation.

    Args:
        output_dir: Directory where evaluation artifacts will be written.
        scenario: Built-in scenario name.
        games: Number of games to run.
        timeout_seconds: Hard timeout for each game.
        seed: Base random seed. Each repetition increments this seed.

    Returns:
        str: The output directory path.
    """
    resolved_output = Path(output_dir)
    eval_scenario = get_scenario(
        name=scenario,
        games=games,
        seed=seed,
        timeout_seconds=timeout_seconds,
    )
    runner = EvaluationRunner(output_dir=resolved_output, scenarios=[eval_scenario])
    asyncio.run(runner.run())
    return str(resolved_output)


def entry() -> None:
    """Entry point for the werewolf-eval command."""
    fire.Fire(main)


if __name__ == "__main__":
    entry()
