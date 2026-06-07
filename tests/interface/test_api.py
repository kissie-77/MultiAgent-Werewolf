"""API layer smoke tests."""

from fastapi.testclient import TestClient

from llm_werewolf.interface.api.app import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_health() -> None:
    resp = _client().get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_page_route_index() -> None:
    resp = _client().get("/api/v1/pages")
    data = resp.json()
    assert resp.status_code == 200
    assert "home" in data
    assert data["home"].startswith("/api/v1/pages/")


def test_page_spec() -> None:
    resp = _client().get("/api/v1/pages/spec")
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) >= 13


def test_pages_home_has_stats_cards() -> None:
    resp = _client().get("/api/v1/pages/home")
    body = resp.json()
    assert body["success"] is True
    assert "hero" in body["data"]
    assert "stats_cards" in body["data"]
    assert len(body["data"]["stats_cards"]) >= 3


def test_pages_roles_has_board_presets() -> None:
    resp = _client().get("/api/v1/pages/roles")
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["total"] >= 20
    assert len(body["data"]["board_presets"]) >= 10


def test_pages_role_detail() -> None:
    resp = _client().get("/api/v1/pages/roles/Seer")
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["display_name"] == "预言家"
    assert "board_sizes" in body["data"]
    assert body["data"]["prompt_count"] >= 1
    assert len(body["data"]["prompt_library"]) >= 1
    assert "skill_library" in body["data"]
    assert len(body["data"]["abilities"]) >= 1


def test_pages_cupid_is_neutral_camp() -> None:
    resp = _client().get("/api/v1/pages/roles/Cupid")
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["camp"] == "neutral"
    assert body["data"]["display_name"] == "丘比特"


def test_pages_roles_has_intro_and_counts() -> None:
    resp = _client().get("/api/v1/pages/roles")
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["intro_title"]
    werewolves = body["data"]["camps"].get("werewolf", [])
    assert werewolves
    assert werewolves[0].get("prompt_count", 0) >= 0
    assert werewolves[0].get("tagline")


def test_pages_night_phase() -> None:
    resp = _client().get("/api/v1/pages/night-phase")
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]["steps"]) >= 4
    assert "involved_roles" in body["data"]


def test_pages_models() -> None:
    resp = _client().get("/api/v1/pages/models")
    body = resp.json()
    assert body["success"] is True
    assert "by_provider" in body["data"]
    assert "configs" in body["data"]
