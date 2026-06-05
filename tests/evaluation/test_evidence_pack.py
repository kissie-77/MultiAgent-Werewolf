import json
from pathlib import Path

from conftest_evolution import build_evolution_fixtures
from llm_werewolf.evaluation.core.evidence_pack import (
    build_evidence_pack,
    summarize_evolution,
    summarize_information_isolation,
)


def test_summarize_information_isolation_passes_when_no_leaks(tmp_path: Path) -> None:
    game_dir = tmp_path / "run" / "games" / "g1"
    game_dir.mkdir(parents=True)
    (game_dir / "checks.json").write_text(
        json.dumps(
            [
                {
                    "checker": "InformationIsolationChecker",
                    "passed": True,
                    "message": "ok",
                    "severity": "info",
                    "data": {},
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = summarize_information_isolation(tmp_path)

    assert summary["status"] == "pass"
    assert summary["games_with_checks"] == 1
    assert summary["information_leak_count"] == 0


def test_summarize_information_isolation_detects_leaks(tmp_path: Path) -> None:
    game_dir = tmp_path / "run" / "games" / "g1"
    game_dir.mkdir(parents=True)
    (game_dir / "checks.json").write_text(
        json.dumps(
            [
                {
                    "checker": "InformationIsolationChecker",
                    "passed": False,
                    "message": "Private event content appeared in unauthorized observation",
                    "severity": "critical",
                    "data": {"player_id": "player_3"},
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = summarize_information_isolation(tmp_path)

    assert summary["status"] == "fail"
    assert summary["information_leak_count"] == 1
    assert summary["critical_leak_count"] == 1
    assert summary["examples"][0]["data"]["player_id"] == "player_3"


def test_build_evidence_pack_writes_json_and_markdown(tmp_path: Path) -> None:
    eval_root = tmp_path / "eval"
    evolution_root = eval_root / "evolution"
    build_evolution_fixtures(evolution_root)
    out = tmp_path / "out"

    paths = build_evidence_pack(
        eval_root=eval_root,
        output_dir=out,
        evolution_root=evolution_root,
    )

    assert paths.json_path.is_file()
    assert paths.markdown_path.is_file()
    payload = json.loads(paths.json_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "grading_evidence_pack_v1"
    assert payload["scope"] == "non_frontend"
    assert payload["score_estimate"]["best_primary_track"] == "进阶 B：评测 + 复盘"
    items = {item["item"]: item for item in payload["rubric_items"]}
    assert items["Few-shot / 思维链"]["status"] == "implemented"
    assert items["文档完整度"]["status"] == "implemented"
    assert "信息隔离" in paths.markdown_path.read_text(encoding="utf-8")


def test_summarize_evolution_marks_engineering_ready_with_ab_report(tmp_path: Path) -> None:
    evolution_root = tmp_path / "evolution"
    build_evolution_fixtures(evolution_root)
    ab_dir = evolution_root / "ab_reports"
    ab_dir.mkdir()
    ab_path = ab_dir / "ab_v1_vs_v3.json"
    ab_path.write_text(
        json.dumps(
            {
                "schema": "ab_report_v1",
                "win_rate_p_value": 0.08,
                "win_rate_significant": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (evolution_root / "evolution_summary.json").write_text(
        json.dumps(
            {
                "schema": "evolution_cycle_v1",
                "rounds": [
                    {"run_dir": str(evolution_root / "v1-baseline")},
                    {"run_dir": str(evolution_root / "v3-skill-matured")},
                ],
                "prompt_version_chain": [{"prompt_version_changed": True}],
                "ab_report_path": str(ab_path),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = summarize_evolution(evolution_root)

    assert summary["status"] == "engineering_ready"
    assert summary["has_ab_report"] is True
    assert summary["has_prompt_loop"] is True
    assert summary["games_total"] == 15
