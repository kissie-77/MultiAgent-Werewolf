"""Route tests for GET /api/v1/games/{run_id}/state."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_state_disk_fallback_for_sample_run(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/games/test-run-1/state", params={"source": "runs"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "ended"
    assert data["phase"] == "ended"
    assert data["winner"] == "werewolf"
    assert data["play_state"] == "playing"
    assert data["speed"] == 1
    assert isinstance(data["players"], list)
    assert data["last_night"] == {
        "deaths": [], "saved_seat": None, "guarded_seat": None, "poisoned_seat": None,
    }


def test_state_missing_run_returns_404(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/games/no-such-run/state")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Run not found: no-such-run"
