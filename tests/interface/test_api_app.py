"""API app entrypoint tests."""

from __future__ import annotations

from unittest.mock import patch

from llm_werewolf.interface.api.app import entry, create_app


def test_api_entry_starts_uvicorn() -> None:
    with patch("llm_werewolf.interface.api.app.uvicorn.run") as mock_run:
        entry(host="0.0.0.0", port=9000, reload=True)
    mock_run.assert_called_once_with(
        "llm_werewolf.interface.api.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=9000,
        reload=True,
    )


def test_create_app_normalizes_cors_origins(monkeypatch) -> None:
    monkeypatch.setenv(
        "WEREWOLF_CORS_ORIGINS",
        " http://localhost:3000, http://localhost:5173, ",
    )

    app = create_app()
    cors = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls.__name__ == "CORSMiddleware"
    )

    assert cors.kwargs["allow_origins"] == [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
