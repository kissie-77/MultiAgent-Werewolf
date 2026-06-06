from pathlib import Path

import fire

from llm_werewolf.paths import EVAL_RUNS_DIR
from llm_werewolf.evaluation.core.evidence_pack import build_evidence_pack


def main(
    eval_root: str = str(EVAL_RUNS_DIR),
    output_dir: str = str(EVAL_RUNS_DIR / "grading_evidence"),
    evolution_root: str | None = None,
    exclude_frontend: bool = True,
) -> str:
    paths = build_evidence_pack(
        eval_root=Path(eval_root),
        output_dir=Path(output_dir),
        evolution_root=Path(evolution_root) if evolution_root else None,
        exclude_frontend=exclude_frontend,
    )
    return str(paths.markdown_path)


def entry() -> None:
    fire.Fire(main)


if __name__ == "__main__":
    entry()
