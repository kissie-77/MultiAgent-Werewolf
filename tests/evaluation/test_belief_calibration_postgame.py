"""Belief calibration PostGame artifact."""

from __future__ import annotations

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.scoring.belief_calibration import write_belief_calibration


def test_write_belief_calibration_emits_json(tmp_path: Path) -> None:
    beliefs = [
        {
            "observer_id": "player_1",
            "first_order": [{"target_seat": 2, "wolf_probability": 0.9}],
        }
    ]
    events = [
        {
            "event_type": "role_acting",
            "data": {"player_id": "player_1", "role": "Villager", "player_name": "A"},
        },
        {
            "event_type": "role_acting",
            "data": {"player_id": "player_2", "role": "Werewolf", "player_name": "B"},
        },
        {
            "event_type": "game_ended",
            "data": {"winner_camp": "werewolf", "winner_ids": ["player_2"]},
        },
    ]
    (tmp_path / "beliefs.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in beliefs),
        encoding="utf-8",
    )
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in events),
        encoding="utf-8",
    )
    ctx = load_run_context(tmp_path)
    path = write_belief_calibration(ctx)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "belief_calibration_v1"
    assert payload["sample_count"] >= 1
    assert payload["aggregate_brier"] is not None
