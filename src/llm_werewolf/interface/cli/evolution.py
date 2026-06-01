from pathlib import Path

import fire

from llm_werewolf.evaluation.evolution.runner import run_evolution_cycle
from llm_werewolf.paths import EVAL_RUNS_DIR


def main(
    output_root: str = str(EVAL_RUNS_DIR / "evolution"),
    scenario: str = "smoke_6p_basic",
    rounds: int = 2,
    games_per_round: int = 3,
    timeout_seconds: float = 30.0,
    seed: int = 1,
    model: str = "unknown",
    prompt_version: str = "v2",
    initial_skill_version: str = "baseline",
    notes: list[str] | None = None,
) -> str:
    summary_path = run_evolution_cycle(
        output_root=Path(output_root),
        scenario=scenario,
        rounds=rounds,
        games_per_round=games_per_round,
        timeout_seconds=timeout_seconds,
        seed=seed,
        model=model,
        prompt_version=prompt_version,
        initial_skill_version=initial_skill_version,
        notes=notes,
    )
    return str(summary_path)


def entry() -> None:
    fire.Fire(main)


if __name__ == "__main__":
    entry()
