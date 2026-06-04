"""Unit tests for interface.api.services helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from fixtures import write_sample_run, write_demo_config

from llm_werewolf.interface.api.services.runs import (
    list_run_dirs,
    paginate_runs,
    get_run_detail,
    resolve_run_path,
    aggregate_model_usage,
)
from llm_werewolf.interface.api.services.pages import (
    build_game_page,
    build_home_page,
    build_role_detail_page,
    build_replay_page_enriched,
    build_share_replay_page_enriched,
)
from llm_werewolf.interface.api.services.config import (
    compare_models,
    get_model_detail,
    list_models_page,
    list_config_files,
    parse_config_brief,
)
from llm_werewolf.interface.api.services.replay import (
    build_timeline,
    get_replay_page,
    build_mvp_ranking,
    build_phase_summary,
    extract_camp_counts,
    extract_game_snapshot,
    get_share_replay_page,
)
from llm_werewolf.interface.api.services.catalog import get_role_detail, list_roles_page
from llm_werewolf.interface.api.services.content import (
    get_about_page,
    get_features_page,
    get_strategy_page,
    get_how_to_play_page,
    get_night_phase_page,
)

if TYPE_CHECKING:
    from pathlib import Path


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
    assert replay.report_markdown

    share = get_share_replay_page("svc-run", service_dirs["runs_dir"], service_dirs["eval_runs_dir"])
    assert share is not None
    assert share.share_url_path == "/share/replay/svc-run"


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


def test_write_full_roster_json(tmp_path):
    from types import SimpleNamespace

    from llm_werewolf.interface.api.services.game_sessions import _write_full_roster

    players = [
        SimpleNamespace(player_id="player_1", name="P1", ai_model="deepseek-chat",
                        get_role_name=lambda: "预言家",
                        role=SimpleNamespace(camp=SimpleNamespace(value="villager"))),
        SimpleNamespace(player_id="player_2", name="P2", ai_model="doubao",
                        get_role_name=lambda: "狼人",
                        role=SimpleNamespace(camp=SimpleNamespace(value="werewolf"))),
    ]
    engine = SimpleNamespace(game_state=SimpleNamespace(players=players))
    _write_full_roster(engine, tmp_path)

    data = json.loads((tmp_path / "roster.json").read_text(encoding="utf-8"))
    assert data["players"][0] == {
        "seat": 1, "player_id": "player_1", "name": "P1",
        "role": "预言家", "camp": "villager", "model": "deepseek-chat",
    }
    assert data["players"][1]["role"] == "狼人"


def test_write_full_roster_skips_unparseable_seat(tmp_path):
    from types import SimpleNamespace

    from llm_werewolf.interface.api.services.game_sessions import _write_full_roster

    players = [
        SimpleNamespace(player_id="human-viewer", name="Bad", ai_model="demo",
                        get_role_name=lambda: "村民",
                        role=SimpleNamespace(camp=SimpleNamespace(value="villager"))),
        SimpleNamespace(player_id="player_2", name="P2", ai_model="doubao",
                        get_role_name=lambda: "狼人",
                        role=SimpleNamespace(camp=SimpleNamespace(value="werewolf"))),
    ]
    engine = SimpleNamespace(game_state=SimpleNamespace(players=players))
    # must not crash on the unparseable seat; just skips it
    _write_full_roster(engine, tmp_path)

    data = json.loads((tmp_path / "roster.json").read_text(encoding="utf-8"))
    assert [p["player_id"] for p in data["players"]] == ["player_2"]
    assert data["players"][0]["seat"] == 2


def test_launch_roster_never_persists_api_key(tmp_path):
    from llm_werewolf.game_runtime.config.player_config import PlayerConfig, PlayersConfig
    from llm_werewolf.interface.api.services.game_sessions import _dump_roster_without_secrets

    cfg = PlayersConfig(
        language="zh-CN",
        players=[
            PlayerConfig(name="P1", model="deepseek-chat",
                         base_url="https://api.deepseek.com/v1", api_key="sk-secret"),
            *[PlayerConfig(name=f"P{i}", model="demo") for i in range(2, 7)],
        ],
    )
    dumped = _dump_roster_without_secrets(cfg)
    text = json.dumps(dumped, ensure_ascii=False)
    assert "sk-secret" not in text
    assert all("api_key" not in p for p in dumped["players"])



import json as _json

from llm_werewolf.interface.api.services.event_hub import EventHub
from llm_werewolf.interface.api.services.game_sessions import (
    GameSession,
    GameSessionStatus,
    IncrementalEventWriter,
    make_fanout_on_event,
)


class _StubEvent:
    """Minimal stand-in for game_runtime Event accepted by event_to_dict."""

    def __init__(self, etype: str) -> None:
        from datetime import datetime

        from llm_werewolf.game_runtime.types.enums import EventType, GamePhase

        self.event_type = EventType(etype)
        self.timestamp = datetime.now()
        self.round_number = 1
        self.phase = GamePhase.DAY_DISCUSSION
        self.message = "P1: hi"
        self.data = {"player_id": "player_1", "player_name": "P1", "speech": "hi"}
        self.visible_to = None


def test_fanout_writes_disk_and_publishes_to_hub(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    session = GameSession(
        run_id="r", run_dir=run_dir,
        config_path=tmp_path / "c.yaml", config_id="c",
    )
    writer = IncrementalEventWriter(run_dir)
    on_event = make_fanout_on_event(writer, session)

    on_event(_StubEvent("player_speech"))
    on_event(_StubEvent("phase_changed"))

    # disk sink received both rows
    lines = (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert _json.loads(lines[0])["event_type"] == "player_speech"

    # hub sink assigned 0-based monotonic seqs and buffered both rows
    assert session.hub.next_seq == 2          # two events published -> next seq is 2
    backfilled = session.hub.backfill(after_seq=-1)   # -1 => all seqs >= 0
    assert [seq for seq, _ in backfilled] == [0, 1]
    assert backfilled[0][1]["event_type"] == "player_speech"


def test_game_session_has_hub_field() -> None:
    session = GameSession(
        run_id="r", run_dir=__import__("pathlib").Path("."),
        config_path=__import__("pathlib").Path("."), config_id="c",
    )
    assert isinstance(session.hub, EventHub)
    assert session.status is GameSessionStatus.PENDING
