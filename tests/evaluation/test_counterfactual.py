from pathlib import Path

from llm_werewolf.evaluation.post_game.counterfactual import (
    build_counterfactual_report,
    write_counterfactual_artifacts,
)
from llm_werewolf.evaluation.post_game.run_context import RunContext


def test_counterfactual_report_detects_close_vote() -> None:
    ctx = RunContext(
        run_dir=Path("."),
        winner_camp="werewolf",
        events=[
            {
                "event_type": "vote_result",
                "round_number": 1,
                "phase": "day_voting",
                "data": {
                    "executed": "player_3",
                    "votes": {
                        "player_3": ["player_1", "player_2", "player_4"],
                        "player_5": ["player_6", "player_7"],
                    },
                },
            }
        ],
    )

    report = build_counterfactual_report(ctx)

    assert report["case_count"] == 1
    assert report["cases"][0]["kind"] == "vote_swing"
    assert "could change" in report["cases"][0]["counterfactual"]


def test_counterfactual_artifacts_are_written(tmp_path: Path) -> None:
    ctx = RunContext(
        run_dir=tmp_path,
        winner_camp="villager",
        events=[
            {
                "event_type": "werewolf_killed",
                "round_number": 1,
                "phase": "night",
                "data": {"target_id": "player_5"},
            }
        ],
    )

    path = write_counterfactual_artifacts(ctx)

    assert path.name == "counterfactual_report.json"
    assert path.is_file()
    assert (tmp_path / "counterfactual_report.md").is_file()
    assert "Counterfactual Report" in (tmp_path / "counterfactual_report.md").read_text(
        encoding="utf-8"
    )
