"""API readiness endpoint."""

from fastapi.testclient import TestClient

from llm_werewolf.interface.api.app import create_app


def test_ready_endpoint_returns_checks(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OBS_READY_REQUIRE_ARK", "0")
    monkeypatch.setattr("llm_werewolf.interface.api.app.ARTIFACTS_DIR", tmp_path / "artifacts")
    client = TestClient(create_app())
    response = client.get("/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ready", "not_ready"}
    assert "checks" in payload
