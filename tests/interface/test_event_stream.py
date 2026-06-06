import asyncio

from llm_werewolf.interface.api.services.event_stream import (
    EventBroadcaster,
    get_broadcaster,
    event_visible_for,
    remove_broadcaster,
    get_or_create_broadcaster,
)


async def test_publish_fans_out_and_assigns_incrementing_ids():
    b = EventBroadcaster()
    received: list[dict] = []

    async def consume() -> None:
        async for ev in b.subscribe():
            received.append(ev)

    task = asyncio.create_task(consume())
    await asyncio.sleep(0)  # let subscribe() register its queue
    assert b.publish({"event_type": "a"}) == 1
    assert b.publish({"event_type": "b"}) == 2
    await asyncio.sleep(0.02)
    b.close()
    await asyncio.wait_for(task, timeout=1)
    assert [e["event_id"] for e in received] == [1, 2]
    assert received[0]["event_type"] == "a"


def test_registry_get_or_create_is_idempotent():
    remove_broadcaster("run-x")
    b1 = get_or_create_broadcaster("run-x")
    b2 = get_or_create_broadcaster("run-x")
    assert b1 is b2
    assert get_broadcaster("run-x") is b1
    remove_broadcaster("run-x")
    assert get_broadcaster("run-x") is None


def test_event_visible_for_god_sees_everything():
    ev_public = {"event_type": "vote_result", "visible_to": None}
    ev_private = {"event_type": "seer_checked", "visible_to": ["player_2"]}
    assert event_visible_for(ev_public, view="god", seat=None) is True
    assert event_visible_for(ev_private, view="god", seat=None) is True


def test_event_visible_for_seat_filters_private_events():
    ev_public = {"event_type": "vote_result", "visible_to": None}
    ev_seer = {"event_type": "seer_checked", "visible_to": ["player_2"]}
    # seat 2 sees its own private event + public; seat 3 only sees public
    assert event_visible_for(ev_public, view="seat", seat=2) is True
    assert event_visible_for(ev_seer, view="seat", seat=2) is True
    assert event_visible_for(ev_seer, view="seat", seat=3) is False
