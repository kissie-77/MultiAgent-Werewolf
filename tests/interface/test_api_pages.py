"""Full coverage for unified /api/v1/pages/* endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_page_spec_detail_home(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/spec/home")
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert body["data"]["page_key"] == "home"
    assert body["data"]["api_path"] == "/api/v1/pages/home"


def test_page_spec_unknown_returns_404(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/spec/not-a-page")
    assert resp.status_code == 404


def test_pages_about(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/about")
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert "sections" in body["data"]
    assert "platform_stats" in body["data"]


def test_pages_features(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/features")
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert len(body["data"]["feature_cards"]) >= 1


def test_pages_how_to_play(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/how-to-play")
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert len(body["data"]["phase_flow"]) >= 4
    assert "victory_conditions" in body["data"]


def test_pages_strategy(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/strategy")
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert "general_tips" in body["data"]
    assert "role_tips_by_camp" in body["data"]


def test_pages_game_default(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/game")
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert len(body["data"]["modes"]) >= 1
    assert body["data"]["active_run"] is None


def test_pages_game_with_run(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/game", params={"run_id": "test-run-1", "source": "runs"})
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert body["data"]["active_run"]["run_id"] == "test-run-1"
    assert body["data"]["snapshot"]["winner_camp"] == "werewolf"
    assert len(body["data"]["players"]) == 6


def test_pages_game_with_config_id(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/game", params={"config_id": "standard-6p"})
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["board_preset"]["player_count"] == 6


def test_pages_game_missing_run_returns_404(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/game", params={"run_id": "missing-run"})
    assert resp.status_code == 404


def test_pages_role_detail_unknown_returns_404(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/roles/NotARealRole")
    assert resp.status_code == 404


def test_pages_model_detail(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/models/demo")
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert body["data"]["model_id"] == "demo"
    assert len(body["data"]["player_slots"]) == 6


def test_pages_models_compare(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/models/compare", params=[("ids", "demo"), ("ids", "other")])
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert len(body["data"]["models"]) == 2
    assert "metric_labels" in body["data"]


def test_pages_models_compare_requires_two_ids(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/models/compare", params={"ids": "demo"})
    assert resp.status_code == 422


def test_pages_replay(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/replay", params={"run_id": "test-run-1", "source": "runs"})
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert body["data"]["run"]["run_id"] == "test-run-1"
    assert len(body["data"]["timeline"]) >= 1
    assert "phase_summary" in body["data"]
    assert len(body["data"]["mvp_ranking"]) >= 1


def test_pages_replay_eval_source(api_client: TestClient) -> None:
    resp = api_client.get(
        "/api/v1/pages/replay", params={"run_id": "eval-run-1", "source": "eval"}
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["run"]["source"] == "eval"


def test_pages_replay_missing_returns_404(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/replay", params={"run_id": "no-such-run"})
    assert resp.status_code == 404


def test_pages_share_replay(api_client: TestClient) -> None:
    resp = api_client.get(
        "/api/v1/pages/share-replay", params={"run_id": "test-run-1", "source": "runs"}
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert body["data"]["run_id"] == "test-run-1"
    assert body["data"]["og_title"]
    assert body["data"]["mvp_winner"]["player_name"] == "W"


def test_pages_share_replay_missing_returns_404(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/pages/share-replay", params={"run_id": "missing"})
    assert resp.status_code == 404
