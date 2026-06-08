import asyncio

from llm_werewolf.interface.api.services.human_input import (
    HumanInputBroker,
    get_input_broker,
    remove_input_broker,
    get_or_create_input_broker,
)


class _Spy:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def publish(self, ev: dict) -> None:
        self.events.append(ev)


async def test_request_resolves_on_submit():
    spy = _Spy()
    broker = HumanInputBroker(run_id="r1", seat=1, broadcaster=spy)
    task = asyncio.create_task(
        broker.request(kind="seat", prompt="投票", valid_targets=[2, 3], fallback="0")
    )
    await asyncio.sleep(0)  # 让 request 登记并推事件
    rid = next(iter(broker.pending_ids()))
    awaiting = next(e for e in spy.events if e["event_type"] == "awaiting_input")
    assert awaiting["visible_to"] == ["player_1"]
    assert awaiting["seat"] == 1
    assert awaiting["request_id"] == rid
    assert awaiting["kind"] == "seat"
    assert awaiting["valid_targets"] == [2, 3]
    assert broker.submit(request_id=rid, payload="2") is True
    assert await task == "2"
    # 幂等：再次 submit 同 id 返回 False
    assert broker.submit(request_id=rid, payload="3") is False


async def test_request_times_out_to_fallback():
    spy = _Spy()
    broker = HumanInputBroker(run_id="r1", seat=1, broadcaster=spy)
    out = await broker.request(
        kind="seat", prompt="投票", valid_targets=[2], fallback="0", deadline=0.05
    )
    assert out == "0"
    assert any(ev["event_type"] == "input_timeout" for ev in spy.events)
    assert broker.pending_ids() == set()


def test_submit_unknown_request_is_false():
    broker = HumanInputBroker(run_id="r1", seat=1, broadcaster=_Spy())
    assert broker.submit(request_id="nope", payload="2") is False


async def test_awaiting_input_event_is_seat_scoped_for_sse():
    # Anti-cheat composition (closes a verifier-flagged gap): the REAL awaiting_input
    # event the broker publishes, run through the REAL SSE visibility filter, must
    # reach the human's OWN seat stream + god view but be filtered out of every OTHER
    # seat's stream — so seat 3 never learns seat 1 is being asked to act.
    from llm_werewolf.interface.api.services.event_stream import event_visible_for

    spy = _Spy()
    broker = HumanInputBroker(run_id="r1", seat=1, broadcaster=spy)
    task = asyncio.create_task(
        broker.request(kind="seat", prompt="投票", valid_targets=[2], fallback="0")
    )
    await asyncio.sleep(0)
    awaiting = next(e for e in spy.events if e["event_type"] == "awaiting_input")
    assert event_visible_for(awaiting, view="seat", seat=1) is True   # owner sees it
    assert event_visible_for(awaiting, view="seat", seat=3) is False  # other seat: filtered
    assert event_visible_for(awaiting, view="god", seat=None) is True  # god sees it

    # the resolution event must stay seat-scoped too (no leak that seat 1 acted)
    rid = next(iter(broker.pending_ids()))
    assert broker.submit(request_id=rid, payload="2") is True
    assert await task == "2"
    received = next(e for e in spy.events if e["event_type"] == "input_received")
    assert event_visible_for(received, view="seat", seat=3) is False


def test_registry_get_or_create_is_idempotent():
    remove_input_broker("run-h")
    spy = _Spy()
    b1 = get_or_create_input_broker("run-h", 1, spy)
    b2 = get_or_create_input_broker("run-h", 1, spy)
    assert b1 is b2
    assert get_input_broker("run-h") is b1
    remove_input_broker("run-h")
    assert get_input_broker("run-h") is None
