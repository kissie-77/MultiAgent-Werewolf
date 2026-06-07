"""Settings API: browser-managed .env API keys."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from llm_werewolf.interface.api.app import create_app
from llm_werewolf.interface.api.deps import get_env_file_path


@pytest.fixture
def settings_client(api_dirs, monkeypatch) -> TestClient:
    env_path = api_dirs["root"] / ".env"
    monkeypatch.delenv("WEREWOLF_SETTINGS_TOKEN", raising=False)
    app = create_app()
    app.dependency_overrides[get_env_file_path] = lambda: env_path
    with TestClient(app) as client:
        yield client


def test_list_available_models_empty(settings_client: TestClient) -> None:
    resp = settings_client.get("/api/v1/settings/available-models")
    assert resp.status_code == 200
    assert resp.json()["data"]["models"] == []
    assert resp.json()["data"]["default_provider_id"] == "doubao"


def test_list_available_models_with_doubao(settings_client: TestClient, api_dirs) -> None:
    env_path = api_dirs["root"] / ".env"
    env_path.write_text(
        "ARK_API_KEY=ark-test\nARK_EP=ep-test-123\nARK_EP_DISPLAY=豆包测试模型\n",
        encoding="utf-8",
    )
    resp = settings_client.get("/api/v1/settings/available-models")
    assert resp.status_code == 200
    models = resp.json()["data"]["models"]
    assert len(models) == 1
    assert models[0]["provider_id"] == "doubao"
    assert models[0]["display_name"] == "豆包测试模型"


def test_list_providers(settings_client: TestClient) -> None:
    resp = settings_client.get("/api/v1/settings/providers")
    assert resp.status_code == 200
    data = resp.json()["data"]
    ids = {p["provider_id"] for p in data["providers"]}
    assert "doubao" in ids
    assert "deepseek" in ids
    assert data["default_provider_id"] == "doubao"


def test_post_provider_fields_writes_env(settings_client: TestClient, api_dirs) -> None:
    env_path = api_dirs["root"] / ".env"
    resp = settings_client.post(
        "/api/v1/settings/api-keys",
        json={"fields": {"ARK_API_KEY": "ark-test", "ARK_EP": "ep-test-123"}},
    )
    assert resp.status_code == 200
    text = env_path.read_text(encoding="utf-8")
    assert "ARK_API_KEY=ark-test" in text
    assert "ARK_EP=ep-test-123" in text


def test_get_api_keys_status_empty(settings_client: TestClient) -> None:
    resp = settings_client.get("/api/v1/settings/api-keys")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["keys"]["deepseek"]["configured"] is False
    assert data["writable"] is True


def test_post_api_keys_writes_env_and_process(settings_client: TestClient, api_dirs) -> None:
    env_path = api_dirs["root"] / ".env"
    resp = settings_client.post(
        "/api/v1/settings/api-keys",
        json={"deepseek": "sk-test-deepseek", "openai": "sk-test-openai"},
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert "DEEPSEEK_API_KEY" in body["updated_env_names"]
    assert body["keys"]["deepseek"]["configured"] is True
    assert body["keys"]["deepseek"]["masked"]
    assert "sk-test-deepseek" not in body["keys"]["deepseek"]["masked"]

    assert env_path.is_file()
    text = env_path.read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY=sk-test-deepseek" in text
    assert "OPENAI_API_KEY=sk-test-openai" in text
    assert os.environ.get("DEEPSEEK_API_KEY") == "sk-test-deepseek"


def test_post_api_keys_updates_existing_line(settings_client: TestClient, api_dirs) -> None:
    env_path = api_dirs["root"] / ".env"
    env_path.write_text("DEEPSEEK_API_KEY=old\n# comment\n", encoding="utf-8")

    resp = settings_client.post(
        "/api/v1/settings/api-keys",
        json={"deepseek": "sk-new"},
    )
    assert resp.status_code == 200
    text = env_path.read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY=sk-new" in text
    assert "DEEPSEEK_API_KEY=old" not in text
    assert "# comment" in text


def test_post_empty_body_is_400(settings_client: TestClient) -> None:
    resp = settings_client.post("/api/v1/settings/api-keys", json={})
    assert resp.status_code == 400


def test_settings_token_required_when_configured(settings_client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("WEREWOLF_SETTINGS_TOKEN", "secret-token")
    no_header = settings_client.get("/api/v1/settings/api-keys")
    assert no_header.status_code == 403

    ok = settings_client.get(
        "/api/v1/settings/api-keys",
        headers={"X-Settings-Token": "secret-token"},
    )
    assert ok.status_code == 200
