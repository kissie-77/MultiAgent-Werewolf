"""Unit tests for the in-process EventHub (pub/sub + backfill)."""

from __future__ import annotations

from llm_werewolf.interface.api.services.event_hub import EventHub


def test_publish_assigns_zero_based_monotonic_seq() -> None:
    # 0-based to match build_view: first event seq=0, cursor=len(rows).
    hub = EventHub(buffer_size=128)
    assert hub.publish({"event_type": "game_started"}) == 0
    assert hub.publish({"event_type": "phase_changed"}) == 1
    assert hub.publish({"event_type": "player_speech"}) == 2
    # next_seq (== count of events published == /view cursor) is 3 after 3 publishes
    assert hub.next_seq == 3


def test_backfill_returns_only_missed_seqs_in_order() -> None:
    hub = EventHub(buffer_size=128)
    for i in range(5):  # seqs 0..4
        hub.publish({"event_type": "player_speech", "data": {"i": i}})
    # Last-Event-ID = 2 means the client has seen seq 0,1,2; backfill seq > 2.
    missed = hub.backfill(after_seq=2)
    assert [seq for seq, _ in missed] == [3, 4]
    assert [row["data"]["i"] for _, row in missed] == [3, 4]


def test_backfill_from_negative_one_returns_all() -> None:
    # A fresh connection (no Last-Event-ID) uses after_seq=-1 to get seq >= 0.
    hub = EventHub(buffer_size=128)
    for i in range(3):  # seqs 0..2
        hub.publish({"event_type": "player_speech", "data": {"i": i}})
    missed = hub.backfill(after_seq=-1)
    assert [seq for seq, _ in missed] == [0, 1, 2]


def test_backfill_after_current_is_empty() -> None:
    hub = EventHub(buffer_size=128)
    hub.publish({"event_type": "game_started"})  # seq 0
    assert hub.backfill(after_seq=10) == []


def test_ring_buffer_evicts_oldest() -> None:
    hub = EventHub(buffer_size=3)
    for i in range(5):  # seqs 0..4, only last 3 (2,3,4) retained
        hub.publish({"event_type": "player_speech", "data": {"i": i}})
    missed = hub.backfill(after_seq=-1)
    assert [seq for seq, _ in missed] == [2, 3, 4]
    # The minimum seq still buffered is exposed for the disk-fallback gap check.
    assert hub.min_buffered_seq == 2
