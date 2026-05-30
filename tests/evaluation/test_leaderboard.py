import json
from pathlib import Path

from llm_werewolf.evaluation.leaderboard.ab_compare import compare_entries, write_ab_report
from llm_werewolf.evaluation.leaderboard.aggregator import collect_entries, write_leaderboard
from llm_werewolf.evaluation.leaderboard.entry_builder import (
    build_entry,
    infer_previous_run_dir,
    load_experiment_meta,
    write_entry,
    write_entry_bundle,
    write_experiment_meta,
)


def _write_run_fixture(run_dir: Path, *, run_name: str, winner_camp: str = "villager") -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "total_games": 2,
                "completed_games": 2,
                "completion_rate": 1.0,
                "avg_rounds_per_game": 4.5,
                "information_leak_count": 0,
                "phase_order_violation_count": 0,
                "role_skill_violation_count": 0,
                "top_errors": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "manifest.json").write_text(
        json.dumps({"scenarios": [{"name": "smoke_6p_basic"}]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    games_dir = run_dir / "games"
    for index in range(2):
        game_dir = games_dir / f"{run_name}_{index}"
        game_dir.mkdir(parents=True, exist_ok=True)
        (game_dir / "post_game_manifest.json").write_text(
            json.dumps({"context": {"winner_camp": winner_camp}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (game_dir / "mvp_scores.json").write_text(
            json.dumps({"summary": {"mvp_score": 0.5 + index * 0.1}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (game_dir / "benefit_scores.json").write_text(
            json.dumps({"summary": {"total_score": 0.4 + index * 0.1}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (game_dir / "intention_scores.json").write_text(
            json.dumps({"summary": {"avg_score": 0.3 + index * 0.1}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def test_build_entry_from_run_dir(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_a"
    _write_run_fixture(run_dir, run_name="run_a")

    entry = build_entry(
        run_dir,
        version_id="kimi_v2_baseline",
        model="kimi",
        prompt_version="v2",
        skill_version="baseline",
    )
    path = write_entry(run_dir, entry)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "leaderboard_entry_v1"
    assert payload["version_id"] == "kimi_v2_baseline"
    assert payload["scenario"] == "smoke_6p_basic"
    assert payload["games"] == 2
    assert payload["win_rate"] == 1.0
    assert payload["avg_mvp_score"] == 0.55


def test_build_entry_prefers_experiment_meta_when_cli_uses_defaults(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_meta"
    _write_run_fixture(run_dir, run_name="run_meta")
    write_experiment_meta(
        run_dir,
        version_id="coach_v3",
        model="kimi-k2",
        prompt_version="prompt_v5",
        skill_version="skill_v7",
        scenario="ranked_12p",
        notes=["night focus", "coach enabled"],
    )

    entry = build_entry(run_dir)

    assert entry.version_id == "coach_v3"
    assert entry.model == "kimi-k2"
    assert entry.prompt_version == "prompt_v5"
    assert entry.skill_version == "skill_v7"
    assert entry.scenario == "ranked_12p"
    assert entry.notes == ["night focus", "coach enabled"]


def test_write_entry_bundle_writes_experiment_meta(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_bundle"
    _write_run_fixture(run_dir, run_name="run_bundle")

    entry = build_entry(
        run_dir,
        version_id="bundle_v1",
        model="kimi",
        prompt_version="prompt_v2",
        skill_version="skill_v1",
        scenario="smoke_6p_basic",
        notes=["bundle"],
    )
    _, meta_path = write_entry_bundle(
        run_dir,
        entry,
        previous_run_dir="../run_prev",
    )

    meta = load_experiment_meta(run_dir)
    assert meta_path.is_file()
    assert meta["version_id"] == "bundle_v1"
    assert meta["previous_run_dir"] == "../run_prev"
    assert meta["notes"] == ["bundle"]


def test_infer_previous_run_dir_uses_latest_valid_sibling(tmp_path: Path) -> None:
    older_run = tmp_path / "run_old"
    latest_run = tmp_path / "run_latest"
    current_run = tmp_path / "run_current"
    ignored_dir = tmp_path / "notes"

    _write_run_fixture(older_run, run_name="run_old")
    _write_run_fixture(latest_run, run_name="run_latest")
    _write_run_fixture(current_run, run_name="run_current")
    ignored_dir.mkdir(parents=True, exist_ok=True)
    (ignored_dir / "random.txt").write_text("x", encoding="utf-8")

    (older_run / "skill_snapshot.json").write_text("{}", encoding="utf-8")
    (latest_run / "skill_snapshot.json").write_text("{}", encoding="utf-8")

    inferred = infer_previous_run_dir(current_run)

    assert inferred == str(latest_run.resolve())


def test_write_entry_bundle_auto_fills_previous_run_dir(tmp_path: Path) -> None:
    previous_run = tmp_path / "run_prev"
    current_run = tmp_path / "run_current"
    _write_run_fixture(previous_run, run_name="run_prev")
    _write_run_fixture(current_run, run_name="run_current")
    (previous_run / "skill_snapshot.json").write_text("{}", encoding="utf-8")

    entry = build_entry(current_run, version_id="current_v1")
    write_entry_bundle(current_run, entry)

    meta = load_experiment_meta(current_run)
    assert meta["previous_run_dir"] == str(previous_run.resolve())


def test_write_leaderboard_aggregates_entries(tmp_path: Path) -> None:
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"
    run_c = tmp_path / "run_c"
    _write_run_fixture(run_a, run_name="run_a", winner_camp="villager")
    _write_run_fixture(run_b, run_name="run_b", winner_camp="")
    _write_run_fixture(run_c, run_name="run_c", winner_camp="villager")

    write_entry(
        run_a,
        build_entry(run_a, version_id="a", model="kimi", prompt_version="v2", skill_version="baseline"),
    )
    write_entry(
        run_b,
        build_entry(run_b, version_id="b", model="kimi", prompt_version="v2", skill_version="coach_v1"),
    )
    write_entry(
        run_c,
        build_entry(run_c, version_id="c", model="doubao", prompt_version="v3", skill_version="coach_v1"),
    )

    path = write_leaderboard(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload["entries"]

    assert len(entries) == 3
    assert entries[0]["version_id"] == "a"
    assert (tmp_path / "leaderboards" / "leaderboard.csv").is_file()
    assert (tmp_path / "leaderboards" / "leaderboard.md").is_file()
    assert (tmp_path / "leaderboards" / "model_leaderboard.json").is_file()
    assert (tmp_path / "leaderboards" / "model_leaderboard.md").is_file()
    assert (tmp_path / "leaderboards" / "prompt_leaderboard.json").is_file()
    assert (tmp_path / "leaderboards" / "skill_leaderboard.json").is_file()
    assert (tmp_path / "leaderboards" / "best_summary.json").is_file()
    assert (tmp_path / "leaderboards" / "best_summary.md").is_file()
    assert len(collect_entries(tmp_path)) == 3

    model_payload = json.loads((tmp_path / "leaderboards" / "model_leaderboard.json").read_text(encoding="utf-8"))
    prompt_payload = json.loads((tmp_path / "leaderboards" / "prompt_leaderboard.json").read_text(encoding="utf-8"))
    skill_payload = json.loads((tmp_path / "leaderboards" / "skill_leaderboard.json").read_text(encoding="utf-8"))
    best_summary = json.loads((tmp_path / "leaderboards" / "best_summary.json").read_text(encoding="utf-8"))

    assert model_payload["group_by"] == "model"
    assert prompt_payload["group_by"] == "prompt_version"
    assert skill_payload["group_by"] == "skill_version"
    assert model_payload["groups"][0]["group_key"] in {"kimi", "doubao"}
    assert any(group["group_key"] == "coach_v1" for group in skill_payload["groups"])
    assert best_summary["schema"] == "leaderboard_best_summary_v1"
    assert best_summary["best_model_group"] is not None
    assert best_summary["best_prompt_group"] is not None
    assert best_summary["best_skill_group"] is not None


def test_compare_entries_and_write_ab_report(tmp_path: Path) -> None:
    entry_a = {
        "version_id": "baseline",
        "games": 20,
        "win_rate": 0.45,
        "completion_rate": 1.0,
        "avg_mvp_score": 0.41,
        "avg_benefit_score": 0.38,
        "avg_intention_score": 0.52,
    }
    entry_b = {
        "version_id": "coach_v1",
        "games": 20,
        "win_rate": 0.56,
        "completion_rate": 1.0,
        "avg_mvp_score": 0.49,
        "avg_benefit_score": 0.44,
        "avg_intention_score": 0.61,
    }
    report = compare_entries(entry_a, entry_b)
    assert report.recommendation == "recommend_b"
    assert report.win_rate_delta > 0.05

    path_a = tmp_path / "entry_a.json"
    path_b = tmp_path / "entry_b.json"
    path_a.write_text(json.dumps(entry_a, ensure_ascii=False, indent=2), encoding="utf-8")
    path_b.write_text(json.dumps(entry_b, ensure_ascii=False, indent=2), encoding="utf-8")
    json_path = write_ab_report(path_a, path_b, output_dir=tmp_path / "ab_reports")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "ab_report_v1"
    assert payload["recommendation"] == "recommend_b"
    assert (tmp_path / "ab_reports" / "ab_baseline_vs_coach_v1.md").is_file()
