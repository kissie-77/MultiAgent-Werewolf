"""Task 7: ``POST /games/{run_id}/input`` route — seat-token validation + broker submit.

Set-up wires a *real* :class:`HumanInputBroker` into the process registry with one
pending request (created via the public ``broker.request`` coroutine) plus a fake
``GameSession`` carrying a known ``player_token``. Then the route is exercised through
``TestClient`` for the three contract branches:

* wrong token              -> 403 (rejected before the broker is even consulted)
* unknown ``request_id``   -> 409 (broker exists but ``submit`` returns ``False``)
* correct token + id       -> 200, ``accepted=True`` (broker ``submit`` resolves)

The pending request is registered by running ``broker.request`` on a throw-away event
loop *up to its first suspension point* and then leaving that loop stopped (not closed).
A stopped-but-open loop has ``_thread_id is None``, so the later ``future.set_result``
issued from the TestClient's portal thread schedules its wake-up callback without
tripping asyncio's cross-thread guard — keeping the happy-path ``submit`` from raising.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from llm_werewolf.interface.api.app import create_app
from llm_werewolf.interface.api.services import human_input as hi
from llm_werewolf.interface.api.services.game_sessions import GameSession, game_session_manager

_RUN_ID = "input-route-test"
_TOKEN = f"seat1-{_RUN_ID}"


def _register_pending_broker() -> tuple[hi.HumanInputBroker, str, asyncio.AbstractEventLoop]:
    """Register a real broker (seat 1) with exactly one pending request.

    Returns the broker, its pending ``request_id``, and the throw-away loop (kept alive
    and intentionally *not* closed so the pending future stays submittable).
    """
    broker = hi.get_or_create_input_broker(_RUN_ID, 1)
    loop = asyncio.new_event_loop()
    loop.create_task(
        broker.request(kind="seat", prompt="请投票", valid_targets=[2, 3], fallback="0")
    )
    # Drive the loop just enough for ``request`` to register and suspend on its future.
    loop.run_until_complete(asyncio.sleep(0))
    pending = broker.pending_ids()
    assert pending, "broker.request did not register a pending entry"
    return broker, next(iter(pending)), loop


def _install_session() -> None:
    game_session_manager._sessions[_RUN_ID] = GameSession(
        run_id=_RUN_ID,
        run_dir=Path("."),
        config_path=Path("."),
        config_id="demo-6",
        player_token=_TOKEN,
        human_seat=1,
    )


def test_input_route_contract() -> None:
    client = TestClient(create_app())
    _install_session()
    _broker, rid, loop = _register_pending_broker()
    try:
        base = f"/api/v1/games/{_RUN_ID}/input"

        # Wrong token -> 403, before the broker is consulted.
        bad = client.post(
            base,
            json={"token": "WRONG", "request_id": rid, "kind": "seat", "payload": "2"},
        )
        assert bad.status_code == 403, bad.text

        # Correct token but unknown request_id -> 409.
        unknown = client.post(
            base,
            json={"token": _TOKEN, "request_id": "no-such-id", "kind": "seat", "payload": "2"},
        )
        assert unknown.status_code == 409, unknown.text

        # Correct token + real pending id -> 200 accepted.
        ok = client.post(
            base,
            json={"token": _TOKEN, "request_id": rid, "kind": "seat", "payload": "2"},
        )
        assert ok.status_code == 200, ok.text
        data = ok.json()["data"]
        assert data["run_id"] == _RUN_ID
        assert data["accepted"] is True

        # Idempotency: the same id is now consumed -> 409.
        again = client.post(
            base,
            json={"token": _TOKEN, "request_id": rid, "kind": "seat", "payload": "2"},
        )
        assert again.status_code == 409, again.text
    finally:
        hi.remove_input_broker(_RUN_ID)
        loop.close()


def test_input_route_unknown_run_is_404() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/games/does-not-exist/input",
        json={"token": "x", "request_id": "y", "kind": "seat", "payload": "0"},
    )
    assert resp.status_code == 404, resp.text
