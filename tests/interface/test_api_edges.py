"""Edge cases and error paths for API layer coverage."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from fixtures import write_sample_run
from llm_werewolf.interface.api.deps import get_artifacts_dir
from llm_werewolf.interface.api.services.board import build_board_presets
from llm_werewolf.interface.api.services.config import list_config_files, parse_config_brief
from llm_werewolf.interface.api.services.pages import build_replay_page_enriched
from llm_werewolf.interface.api.services.replay import extract_game_snapshot
from llm_werewolf.interface.api.services.runs import get_run_detail, list_run_dirs, resolve_run_path


def test_get_artifacts_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "artifacts").mkdir()
    assert get_artifacts_dir() == tmp_path / "artifacts"


def test_build_board_presets_covers_standard_sizes() -> None:
    presets = build_board_presets()
    counts = {p.player_count for p in presets}
    assert 6 in counts
    assert 12 in counts


def test_parse_config_brief_invalid_yaml(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(":\n  - [unclosed", encoding="utf-8")
    assert parse_config_brief(bad) is None


def test_list_config_files_empty_dir(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert list_config_files(empty) == []


def test_resolve_run_path_eval_batch_layout(api_dirs: dict[str, Path]) -> None:
    path = resolve_run_path(
        "eval-run-1",
        api_dirs["runs_dir"],
        api_dirs["eval_runs_dir"],
        source="eval",
    )
    assert path is not None
    assert path.name == "eval-run-1"


def test_get_run_detail_with_manifest(api_dirs: dict[str, Path]) -> None:
    run_dir = api_dirs["runs_dir"] / "test-run-1"
    (run_dir / "post_game_manifest.json").write_text("{not-json", encoding="utf-8")
    detail = get_run_detail("test-run-1", api_dirs["runs_dir"], api_dirs["eval_runs_dir"])
    assert detail is not None
    assert detail.extra == {}


def test_list_run_dirs_skips_non_directories(api_dirs: dict[str, Path]) -> None:
    (api_dirs["runs_dir"] / "not-a-dir.txt").write_text("x", encoding="utf-8")
    runs = list_run_dirs(api_dirs["runs_dir"], api_dirs["eval_runs_dir"])
    assert all(r.run_id != "not-a-dir.txt" for r in runs)


def test_extract_game_snapshot_with_sheriff(api_dirs: dict[str, Path]) -> None:
    from fixtures import sample_run_events

    run_dir = api_dirs["runs_dir"] / "sheriff-run"
    events = sample_run_events() + [
        {
            "event_type": "sheriff_elected",
            "round_number": 1,
            "phase": "day_discussion",
            "data": {"player_id": "player_1"},
        }
    ]
    run_dir.mkdir(parents=True)
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )

    snapshot = extract_game_snapshot(run_dir)
    assert snapshot.sheriff_id == "player_1"


def test_build_replay_page_enriched_with_coach(api_dirs: dict[str, Path]) -> None:
    run_dir = api_dirs["runs_dir"] / "test-run-1"
    (run_dir / "coach_summary.json").write_text(
        json.dumps({"summary": "coach insight"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "views_manifest.json").write_text(
        json.dumps({"public": {}, "werewolf": {}}),
        encoding="utf-8",
    )
    page = build_replay_page_enriched(
        "test-run-1", api_dirs["runs_dir"], api_dirs["eval_runs_dir"]
    )
    assert page is not None
    assert page.coach_excerpt == "coach insight"
    assert "public" in page.views_available


def test_legacy_game_missing_run_fallback(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/game", params={"run_id": "missing-run"})
    assert resp.status_code == 404


def test_legacy_content_generic_about(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/content/about")
    assert resp.status_code == 200


def test_legacy_role_unknown(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/roles/NoSuchRole")
    assert resp.status_code == 404


def test_legacy_replay_missing(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/replay/missing-id")
    assert resp.status_code == 404


def test_legacy_share_replay_missing(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/replay/missing-id/share")
    assert resp.status_code == 404


def test_build_mode_options_tolerates_bad_config() -> None:
    from llm_werewolf.interface.api.services.pages import _build_mode_options
    from llm_werewolf.interface.cli.runtime.modes import GameMode

    bad_mode = GameMode(
        participation="all_agent",
        rules="basic",
        config_path=Path("/nonexistent/config.yaml"),
        description="bad",
    )
    with patch("llm_werewolf.interface.api.services.pages.list_modes", return_value=[bad_mode]):
        options = _build_mode_options()
    assert len(options) == 1
    assert options[0].player_count is None
