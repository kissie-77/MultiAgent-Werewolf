"""Unit tests for interface.api.services helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from llm_werewolf.interface.api.services.catalog import get_role_detail, list_roles_page
from llm_werewolf.interface.api.services.config import (
    compare_models,
    get_model_detail,
    list_config_files,
    list_models_page,
    parse_config_brief,
)
from llm_werewolf.interface.api.services.content import (
    get_about_page,
    get_features_page,
    get_how_to_play_page,
    get_night_phase_page,
    get_strategy_page,
)
from llm_werewolf.interface.api.services.pages import (
    build_game_page,
    build_home_page,
    build_replay_page_enriched,
    build_role_detail_page,
    build_share_replay_page_enriched,
)
from llm_werewolf.interface.api.services.replay import (
    build_mvp_ranking,
    build_phase_summary,
    build_timeline,
    extract_camp_counts,
    extract_game_snapshot,
    get_replay_page,
    get_share_replay_page,
)
from llm_werewolf.interface.api.services.runs import (
    aggregate_model_usage,
    get_run_detail,
    list_run_dirs,
    paginate_runs,
    resolve_run_path,
)

from fixtures import write_demo_config, write_sample_run


@pytest.fixture
def service_dirs(tmp_path: Path) -> dict[str, Path]:
    runs_dir = tmp_path / "artifacts" / "runs"
    eval_runs_dir = tmp_path / "artifacts" / "eval_runs"
    configs_dir = tmp_path / "configs"
    write_demo_config(configs_dir)
    write_sample_run(runs_dir / "svc-run")
    return {
        "runs_dir": runs_dir,
        "eval_runs_dir": eval_runs_dir,
        "configs_dir": configs_dir,
    }


def test_list_run_dirs_and_paginate(service_dirs: dict[str, Path]) -> None:
    runs = list_run_dirs(service_dirs["runs_dir"], service_dirs["eval_runs_dir"])
    assert len(runs) == 1
    assert runs[0].run_id == "svc-run"
    assert runs[0].has_replay is True

    page = paginate_runs(
        service_dirs["runs_dir"],
        service_dirs["eval_runs_dir"],
        page=1,
        page_size=10,
        source="runs",
    )
    assert page.meta.total == 1
    assert page.items[0].winner_camp == "werewolf"


def test_resolve_and_get_run_detail(service_dirs: dict[str, Path]) -> None:
    path = resolve_run_path("svc-run", service_dirs["runs_dir"], service_dirs["eval_runs_dir"])
    assert path is not None
    assert path.name == "svc-run"

    detail = get_run_detail("svc-run", service_dirs["runs_dir"], service_dirs["eval_runs_dir"])
    assert detail is not None
    assert detail.winner_camp == "werewolf"
    assert len(detail.roster) == 6


def test_aggregate_model_usage(service_dirs: dict[str, Path]) -> None:
    stats = aggregate_model_usage(service_dirs["runs_dir"], service_dirs["eval_runs_dir"])
    demo = next((s for s in stats if s.model_id == "demo"), None)
    assert demo is not None
    assert demo.avg_mvp == pytest.approx(8.25)


def test_replay_helpers(service_dirs: dict[str, Path]) -> None:
    run_dir = service_dirs["runs_dir"] / "svc-run"
    timeline = build_timeline(run_dir)
    assert timeline
    assert timeline[-1].event_type == "game_ended"

    snapshot = extract_game_snapshot(run_dir)
    assert snapshot.winner_camp == "werewolf"
    assert snapshot.is_ended is True

    camps = extract_camp_counts(run_dir)
    assert sum(camps.values()) >= 1

    phases = build_phase_summary(run_dir)
    assert phases

    mvp = build_mvp_ranking(run_dir)
    assert mvp[0].player_name == "W"


def test_replay_and_share_pages(service_dirs: dict[str, Path]) -> None:
    replay = get_replay_page("svc-run", service_dirs["runs_dir"], service_dirs["eval_runs_dir"])
    assert replay is not None
    assert replay.view_scope == "public"
    assert replay.report_markdown

    share = get_share_replay_page("svc-run", service_dirs["runs_dir"], service_dirs["eval_runs_dir"])
    assert share is not None
    assert share.share_url_path == "/share/replay/svc-run"


def test_replay_page_defaults_to_public_visibility(service_dirs: dict[str, Path]) -> None:
    run_dir = service_dirs["runs_dir"] / "svc-run"
    private_event = {
        "event_type": "belief_snapshot",
        "round_number": 1,
        "phase": "day_discussion",
        "message": "私密信念矩阵",
        "visible_to": [],
        "data": {},
    }
    malformed_legacy_event = {
        "event_type": "belief_snapshot",
        "round_number": 1,
        "phase": "day_discussion",
        "message": "legacy belief snapshot",
        "visible_to": None,
        "data": {},
    }
    with (run_dir / "events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("\n" + json.dumps(private_event, ensure_ascii=False))
        fh.write("\n" + json.dumps(malformed_legacy_event, ensure_ascii=False))
    (run_dir / "beliefs.jsonl").write_text(
        json.dumps({"observer_seat": 1, "first_order": []}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    public_page = get_replay_page(
        "svc-run", service_dirs["runs_dir"], service_dirs["eval_runs_dir"]
    )
    god_page = get_replay_page(
        "svc-run", service_dirs["runs_dir"], service_dirs["eval_runs_dir"], view="god"
    )
    player_page = get_replay_page(
        "svc-run",
        service_dirs["runs_dir"],
        service_dirs["eval_runs_dir"],
        viewer_id="player_1",
    )

    assert public_page is not None
    assert god_page is not None
    assert player_page is not None
    assert public_page.view_scope == "public"
    assert god_page.view_scope == "god"
    assert player_page.view_scope == "player"
    assert "legacy belief snapshot" not in [event.message for event in public_page.timeline]
    assert "legacy belief snapshot" not in [event.message for event in player_page.timeline]
    assert "私密信念矩阵" not in [event.message for event in public_page.timeline]
    assert "私密信念矩阵" in [event.message for event in god_page.timeline]
    assert "legacy belief snapshot" in [event.message for event in god_page.timeline]
    assert public_page.belief_snapshots == []
    assert god_page.belief_snapshots


def test_page_builders(service_dirs: dict[str, Path]) -> None:
    home = build_home_page(
        service_dirs["runs_dir"],
        service_dirs["eval_runs_dir"],
        service_dirs["configs_dir"],
    )
    assert home.stats_cards
    assert home.recent_runs

    game = build_game_page(
        service_dirs["runs_dir"],
        service_dirs["eval_runs_dir"],
        run_id="svc-run",
    )
    assert game is not None
    assert game.active_run is not None
    assert game.snapshot is not None

    replay = build_replay_page_enriched(
        "svc-run", service_dirs["runs_dir"], service_dirs["eval_runs_dir"]
    )
    assert replay is not None
    assert replay.turning_points is not None

    share = build_share_replay_page_enriched(
        "svc-run", service_dirs["runs_dir"], service_dirs["eval_runs_dir"]
    )
    assert share is not None
    assert share.mvp_winner is not None


def test_catalog_and_content() -> None:
    roles = list_roles_page()
    assert roles.total >= 20
    assert "werewolf" in roles.camps

    detail = get_role_detail("Seer")
    assert detail.display_name == "预言家"

    enriched = build_role_detail_page("Seer")
    assert enriched.board_sizes
    assert enriched.related_roles

    assert get_about_page().sections
    assert get_features_page().sections
    assert get_how_to_play_page().sections
    assert get_night_phase_page().steps
    assert get_strategy_page().general_tips


def test_config_service(service_dirs: dict[str, Path]) -> None:
    files = list_config_files(service_dirs["configs_dir"])
    assert files

    brief = parse_config_brief(files[0])
    assert brief is not None
    assert brief.config_id == "demo-6"
    assert brief.models == ["demo"] * 6

    listing = list_models_page(service_dirs["configs_dir"])
    assert listing.configs

    detail = get_model_detail("demo", service_dirs["configs_dir"])
    assert detail.model_id == "demo"

    compare = compare_models(["demo", "missing-model"])
    assert len(compare.models) == 2
    assert compare.models[1].run_count == 0


def test_config_provider_inference(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    (configs_dir / "llm-6p-doubao.yaml").write_text(
        "players:\n  - name: P1\n    model: doubao-seed\n",
        encoding="utf-8",
    )
    (configs_dir / "llm-6p-deepseek.yaml").write_text(
        "players:\n  - name: P1\n    model: deepseek-chat\n",
        encoding="utf-8",
    )
    (configs_dir / "human-6p-demo.yaml").write_text(
        "players:\n  - name: P1\n    model: human\n",
        encoding="utf-8",
    )
    listing = list_models_page(configs_dir)
    providers = {c.config_id: c.provider for c in listing.configs}
    assert providers["llm-6p-doubao"] == "volcengine_ark"
    assert providers["llm-6p-deepseek"] == "deepseek"
    assert providers["human-6p-demo"] == "local"


def test_aggregate_model_usage_reads_mvp_scores(api_dirs: dict[str, Path]) -> None:
    run_dir = api_dirs["runs_dir"] / "model-run"
    write_sample_run(run_dir)
    stats = aggregate_model_usage(api_dirs["runs_dir"], api_dirs["eval_runs_dir"])
    demo = next(item for item in stats if item.model_id == "demo")
    assert demo.avg_mvp == pytest.approx(8.25)

