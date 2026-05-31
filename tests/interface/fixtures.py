"""Shared test data builders for interface API tests."""

from __future__ import annotations

import json
from pathlib import Path


def sample_run_events() -> list[dict]:
    roles = [
        ("player_1", "A", "Seer"),
        ("player_2", "W", "Werewolf"),
        ("player_3", "B", "Villager"),
        ("player_4", "C", "Witch"),
        ("player_5", "D", "Guard"),
        ("player_6", "E", "Villager"),
    ]
    events: list[dict] = []
    for pid, name, role in roles:
        events.append(
            {
                "event_type": "role_acting",
                "round_number": 1,
                "phase": "night",
                "data": {"player_id": pid, "player_name": name, "role": role},
            }
        )
    events.extend(
        [
            {
                "event_type": "player_eliminated",
                "round_number": 1,
                "phase": "day_voting",
                "data": {"player_id": "player_5", "role": "Guard"},
            },
            {
                "event_type": "game_ended",
                "round_number": 1,
                "phase": "ended",
                "data": {"winner_camp": "werewolf", "winner_ids": ["player_2"]},
            },
        ]
    )
    return events


def write_sample_run(run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    events = sample_run_events()
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    (run_dir / "mvp_scores.json").write_text(
        json.dumps(
            [
                {
                    "player_id": "player_2",
                    "player_name": "W",
                    "role_name": "Werewolf",
                    "total": 9.5,
                    "ai_model": "demo",
                },
                {
                    "player_id": "player_1",
                    "player_name": "A",
                    "role_name": "Seer",
                    "total": 7.0,
                    "ai_model": "demo",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (run_dir / "post_game_report.md").write_text("# 测试复盘\n狼人阵营获胜。", encoding="utf-8")
    return run_dir


def write_demo_config(configs_dir: Path) -> Path:
    configs_dir.mkdir(parents=True, exist_ok=True)
    path = configs_dir / "demo-6.yaml"
    path.write_text(
        """language: zh-CN
players:
  - name: DemoPlayer1
    model: demo
  - name: DemoPlayer2
    model: demo
  - name: DemoPlayer3
    model: demo
  - name: DemoPlayer4
    model: demo
  - name: DemoPlayer5
    model: demo
  - name: DemoPlayer6
    model: demo
""",
        encoding="utf-8",
    )
    return path
