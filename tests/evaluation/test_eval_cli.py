from pathlib import Path

from llm_werewolf.interface.eval_cli import main


def test_eval_cli_main_writes_outputs(tmp_path: Path) -> None:
    result_path = main(
        output_dir=str(tmp_path),
        scenario="smoke_6p_basic",
        games=1,
        timeout_seconds=20,
        seed=5,
        version_id="cli_v1",
        model="demo",
        prompt_version="prompt_v1",
        skill_version="baseline",
        notes=["cli-auto"],
    )

    assert Path(result_path) == tmp_path
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "experiment_meta.json").exists()
    assert (tmp_path / "leaderboard_entry.json").exists()
