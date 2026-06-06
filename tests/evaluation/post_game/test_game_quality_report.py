"""对局质量报告。"""

from pathlib import Path

from llm_werewolf.evaluation.post_game.run_context import RunContext, PlayerRosterEntry
from llm_werewolf.evaluation.post_game.game_quality_report import write_game_quality_report


def test_game_quality_report_contains_mvp_and_golden(tmp_path: Path) -> None:
    mvp_payload = {
        "mvp": {
            "player_id": "player_2",
            "player_name": "狼王",
            "role_name": "Werewolf",
            "camp": "werewolf",
            "mvp_total": 72.5,
            "breakdown_raw": {"persuasion": 30, "wolf_night": 20, "strategy": 10, "outcome": 12},
            "breakdown_norm": {"persuasion": 80, "wolf_night": 70, "strategy": 50, "outcome": 40},
            "golden_speech_candidates": [
                {
                    "kind": "public_persuasion",
                    "round_number": 2,
                    "excerpt": "今天必须出五号，他发言前后矛盾。",
                    "score": 40,
                }
            ],
            "top_evidence": [{"kind": "wolf_night", "why": "夜间计划与刀口一致"}],
        },
        "players": [],
        "camp_mvp": {},
        "data_quality": {"confidence": "high", "has_vote_intentions": True},
        "dimension_context_paths": {"persuasion": "views/score_contexts/persuasion.md"},
    }
    ctx = RunContext(
        run_dir=tmp_path,
        winner_camp="villager",
        roster={
            "player_2": PlayerRosterEntry(
                player_id="player_2", player_name="狼王", role_name="Werewolf", camp="werewolf"
            )
        },
    )
    steps = [
        {
            "step_id": "mvp_scores",
            "status": "ok",
            "duration_ms": 12.0,
            "error": None,
            "artifacts": [],
        }
    ]

    path = write_game_quality_report(ctx, mvp_payload, steps=steps)
    text = path.read_text(encoding="utf-8")

    assert "对局质量报告" in text
    assert "狼王" in text
    assert "金句" in text or "关键发言" in text
    assert "今天必须出五号" in text
    assert (tmp_path / "game_quality_report.json").is_file()
