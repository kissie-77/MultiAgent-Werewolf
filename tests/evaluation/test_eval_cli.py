from pathlib import Path

from llm_werewolf.eval_cli import main


def test_eval_cli_main_writes_outputs(tmp_path: Path) -> None:
    result_path = main(
        output_dir=str(tmp_path),
        scenario="smoke_6p_basic",
        games=1,
        timeout_seconds=20,
        seed=5,
    )

    assert Path(result_path) == tmp_path
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "report.md").exists()
