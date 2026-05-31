"""API app entrypoint tests."""

from __future__ import annotations

from unittest.mock import patch

from llm_werewolf.interface.api.app import entry


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
