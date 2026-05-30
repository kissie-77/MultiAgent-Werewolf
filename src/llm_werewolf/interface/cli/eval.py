import asyncio
from pathlib import Path

import fire

from llm_werewolf.evaluation.core.runner import EvaluationRunner
from llm_werewolf.evaluation.core.scenarios import get_scenario
from llm_werewolf.paths import EVAL_RUNS_DIR


def main(
    output_dir: str = str(EVAL_RUNS_DIR),
    scenario: str = "smoke_6p_basic",
    games: int = 10,
    timeout_seconds: float = 30.0,
    seed: int = 1,
    version_id: str | None = None,
    model: str = "unknown",
    prompt_version: str = "unknown",
    skill_version: str = "baseline",
    notes: list[str] | None = None,
    previous_run_dir: str | None = None,
    previous_skill_snapshot_path: str | None = None,
) -> str:
    resolved_output = Path(output_dir)
    eval_scenario = get_scenario(
        name=scenario,
        games=games,
        seed=seed,
        timeout_seconds=timeout_seconds,
    )
    runner = EvaluationRunner(
        output_dir=resolved_output,
        scenarios=[eval_scenario],
        version_id=version_id,
        model=model,
        prompt_version=prompt_version,
        skill_version=skill_version,
        notes=notes,
        previous_run_dir=previous_run_dir,
        previous_skill_snapshot_path=previous_skill_snapshot_path,
    )
    asyncio.run(runner.run())
    return str(resolved_output)


def entry() -> None:
    fire.Fire(main)


if __name__ == "__main__":
    entry()
