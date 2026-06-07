"""Task 5: StartGameRequest.human + StartGameResponse player_token/stream_path."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from llm_werewolf.interface.api.models.actions import (
    HumanSeatSpec,
    StartGameRequest,
    StartGameResponse,
)


def test_request_accepts_human_seat() -> None:
    req = StartGameRequest(config_id="standard-6p", human={"seat": 1})
    assert req.human is not None
    assert req.human.seat == 1
    assert req.human.role is None


def test_request_human_defaults_to_none() -> None:
    req = StartGameRequest(config_id="standard-6p")
    assert req.human is None


def test_human_seat_spec_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        HumanSeatSpec(seat=0)
    with pytest.raises(ValidationError):
        HumanSeatSpec(seat=21)


def test_human_seat_spec_accepts_optional_role() -> None:
    spec = HumanSeatSpec(seat=3, role="seer")
    assert spec.seat == 3
    assert spec.role == "seer"


def test_response_has_token_fields() -> None:
    r = StartGameResponse(
        run_id="x",
        status="running",
        config_id="c",
        run_dir="d",
        game_page_path="g",
        status_path="s",
        replay_page_path="r",
        player_token="tok",
        stream_path="/api/v1/games/x/stream",
    )
    assert r.player_token == "tok"
    assert r.stream_path == "/api/v1/games/x/stream"


def test_response_token_fields_default_to_none() -> None:
    r = StartGameResponse(
        run_id="x",
        status="running",
        config_id="c",
        run_dir="d",
        game_page_path="g",
        status_path="s",
        replay_page_path="r",
    )
    assert r.player_token is None
    assert r.stream_path is None
