"""POST action API tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from pathlib import Path

from fastapi.testclient import TestClient

from llm_werewolf.interface.api.services.game_sessions import game_session_manager


def test_actions_spec(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/actions/spec")
    assert resp.status_code == 200
    actions = resp.json()["data"]["actions"]
    assert any(a["action"] == "start_game" for a in actions)


def test_start_game_unknown_config(api_client: TestClient) -> None:
    resp = api_client.post("/api/v1/games/start", json={"config_id": "no-such-config"})
    assert resp.status_code == 404


def test_start_game_returns_run_id(api_client: TestClient) -> None:
    with patch.object(game_session_manager, "_run_game", new=AsyncMock()):
        resp = api_client.post("/api/v1/games/start", json={"config_id": "demo-6"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["run_id"]
    assert data["status"] == "running"
    assert data["player_count"] == 6
    assert "game?run_id=" in data["game_page_path"]


def test_start_game_default_mode(api_client: TestClient) -> None:
    with patch.object(game_session_manager, "_run_game", new=AsyncMock()):
        resp = api_client.post("/api/v1/games/start", json={})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["config_id"] == "llm-12p-kimi"
    assert data["rules"] == "basic"


def test_start_game_mode_badge_flow(api_client: TestClient) -> None:
    with patch.object(game_session_manager, "_run_game", new=AsyncMock()):
        resp = api_client.post(
            "/api/v1/games/start",
            json={"participation": "all_agent", "rules": "basic"},
        )
    assert resp.status_code == 200
    assert resp.json()["data"]["rules"] == "basic"


def test_start_game_custom_roster(api_client: TestClient) -> None:
    with patch.object(game_session_manager, "_run_game", new=AsyncMock()):
        resp = api_client.post(
            "/api/v1/games/start",
            json={
                "config_id": "demo-6",
                "player_count": 8,
                "players": [{"name": "SeatOne"}, {"name": "SeatTwo"}],
            },
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["player_count"] == 8
    assert data["custom_roster"] is True
    run_id = data["run_id"]
    session = game_session_manager._sessions[run_id]
    assert session.players_config is not None
    assert session.players_config.players[0].name == "SeatOne"


def test_start_game_rejects_human_seats_for_web(api_client: TestClient) -> None:
    with patch.object(game_session_manager, "_run_game", new=AsyncMock()):
        resp = api_client.post(
            "/api/v1/games/start",
            json={"config_id": "demo-6", "human_seats": [1], "badge_flow": True},
        )
    assert resp.status_code == 400
    assert "human-player games are not supported" in resp.json()["detail"]


def test_start_game_rejects_human_config_for_web(
    api_client: TestClient, api_dirs: dict[str, Path]
) -> None:
    (api_dirs["configs_dir"] / "human-6p-demo.yaml").write_text(
        "\n".join([
            "language: zh-CN",
            "agent_backend: agentscope",
            "players:",
            "  - name: P1",
            "    model: human",
            "  - name: P2",
            "    model: demo",
            "  - name: P3",
            "    model: demo",
            "  - name: P4",
            "    model: demo",
            "  - name: P5",
            "    model: demo",
            "  - name: P6",
            "    model: demo",
        ]),
        encoding="utf-8",
    )

    with patch.object(game_session_manager, "_run_game", new=AsyncMock()):
        resp = api_client.post("/api/v1/games/start", json={"config_id": "human-6p-demo"})

    assert resp.status_code == 400
    assert "human-player games are not supported" in resp.json()["detail"]


def test_list_start_modes(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/games/modes")
    assert resp.status_code == 200
    modes = resp.json()["data"]["modes"]
    assert any(m["rules"] == "basic" for m in modes)
    assert all(m["participation"] != "human_mixed" for m in modes)
    assert all(m["config_id"] != "human-6p-demo" for m in modes)
    assert resp.json()["data"]["default_rules"] == "basic"


def test_game_status_for_sample_run(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/games/test-run-1/status", params={"source": "runs"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["run_id"] == "test-run-1"
    assert data["snapshot"] is not None


def test_game_status_missing(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/games/missing-run/status")
    assert resp.status_code == 404


def test_compare_models_post(api_client: TestClient) -> None:
    resp = api_client.post(
        "/api/v1/models/compare",
        json={"ids": ["demo", "other-model"]},
    )
    assert resp.status_code == 200
    models = resp.json()["data"]["compare"]["models"]
    assert len(models) == 2


def test_compare_models_post_requires_two_ids(api_client: TestClient) -> None:
    resp = api_client.post("/api/v1/models/compare", json={"ids": ["demo"]})
    assert resp.status_code == 422


def test_trigger_post_game_on_sample_run(api_client: TestClient) -> None:
    resp = api_client.post(
        "/api/v1/runs/test-run-1/post-game",
        json={"source": "runs", "force": False},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["run_id"] == "test-run-1"


def test_trigger_post_game_missing(api_client: TestClient) -> None:
    resp = api_client.post("/api/v1/runs/missing/post-game", json={})
    assert resp.status_code == 404


def test_cancel_unknown_session(api_client: TestClient) -> None:
    resp = api_client.post("/api/v1/games/not-started/cancel")
    assert resp.status_code == 404
