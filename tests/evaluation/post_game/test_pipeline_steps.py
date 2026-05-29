"""流水线分步执行。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.pipeline import run_post_game_pipeline_sync
from llm_werewolf.evaluation.post_game.pipeline_steps import run_step


def test_run_step_captures_failure_without_raise() -> None:
    steps = []

    def ok() -> int:
        return 1

    def bad() -> None:
        msg = "boom"
        raise ValueError(msg)

    assert run_step(steps, "ok_step", ok) == 1
    assert run_step(steps, "bad_step", bad) is None
    assert len(steps) == 2
    assert steps[0].status == "ok"
    assert steps[1].status == "failed"
    assert "boom" in (steps[1].error or "")


def test_pipeline_writes_steps_and_quality_report(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "vote_intention_snapshot",
            "round_number": 1,
            "phase": "day_discussion",
            "data": {
                "channel": "public",
                "speaker_id": "player_1",
                "speaker_name": "A",
                "public_speech": "出2号",
                "before": {},
                "after": {},
                "swings": [],
                "swing_count": 0,
            },
        },
        {
            "event_type": "game_ended",
            "round_number": 1,
            "phase": "ended",
            "data": {"winner_camp": "villager", "winner_ids": ["player_1"]},
        },
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )

    result = run_post_game_pipeline_sync(tmp_path, skip_llm=True)

    assert (tmp_path / "post_game_steps.json").is_file()
    assert (tmp_path / "game_quality_report.md").is_file()
    assert (tmp_path / "mvp_scores.json").is_file()
    steps_payload = json.loads((tmp_path / "post_game_steps.json").read_text(encoding="utf-8"))
    assert steps_payload["summary"]["ok"] >= 1
    assert result.steps

    benefit = json.loads((tmp_path / "benefit_scores.json").read_text(encoding="utf-8"))
    assert benefit["schema"] == "benefit_scores_v2"
