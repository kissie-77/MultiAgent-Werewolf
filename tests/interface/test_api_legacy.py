"""Legacy REST routes under /api/v1/* (backward compatibility)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_legacy_home(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/home")
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert "hero" in body["data"]


def test_legacy_game(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/game", params={"run_id": "test-run-1"})
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["active_run"]["run_id"] == "test-run-1"


def test_legacy_content_pages(api_client: TestClient) -> None:
    for path in ("/about", "/features", "/how-to-play", "/night-phase", "/strategy"):
        resp = api_client.get(f"/api/v1/content{path}")
        body = resp.json()
        assert resp.status_code == 200, path
        assert body["success"] is True
        assert body["data"]["title"]


def test_legacy_content_unknown_returns_404(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/content/unknown-page")
    assert resp.status_code == 404


def test_legacy_roles_list(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/roles")
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["total"] >= 20


def test_legacy_role_detail(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/roles/Witch")
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["display_name"] == "女巫"


def test_legacy_models_list(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/models")
    body = resp.json()
    assert resp.status_code == 200
    assert any(c["config_id"] == "standard-6p" for c in body["data"]["configs"])


def test_legacy_models_compare(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/models/compare", params=[("ids", "demo"), ("ids", "x")])
    assert resp.status_code == 200
    assert len(resp.json()["data"]["models"]) == 2


def test_legacy_model_detail(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/models/demo")
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["model_id"] == "demo"


def test_legacy_runs_list(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/runs")
    body = resp.json()
    assert resp.status_code == 200
    items = body["data"]["runs"]["items"]
    run_ids = {item["run_id"] for item in items}
    assert "test-run-1" in run_ids
    assert "eval-run-1" in run_ids


def test_legacy_runs_pagination(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/runs", params={"page": 1, "page_size": 1, "source": "runs"})
    body = resp.json()
    assert resp.status_code == 200
    assert len(body["data"]["runs"]["items"]) == 1
    assert body["data"]["runs"]["meta"]["total"] >= 1


def test_legacy_run_detail(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/runs/test-run-1", params={"source": "runs"})
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["run_id"] == "test-run-1"
    assert len(body["data"]["roster"]) == 6


def test_legacy_run_detail_missing_returns_404(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/runs/does-not-exist")
    assert resp.status_code == 404


def test_legacy_replay(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/replay/test-run-1", params={"source": "runs"})
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["run"]["run_id"] == "test-run-1"
    assert body["data"]["timeline"]


def test_legacy_share_replay(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/replay/test-run-1/share", params={"source": "runs"})
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["run_id"] == "test-run-1"
    assert body["data"]["share_title"]
