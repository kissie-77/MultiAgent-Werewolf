"""Task 1: collision-proof run_id generation."""

from __future__ import annotations

from llm_werewolf.interface.api.services.game_sessions import build_run_id


def test_plain_run_id_no_tag_no_collision() -> None:
    rid = build_run_id("6p-deepseek", "20260607-101500", tag=None, exists=lambda _r: False)
    assert rid == "6p-deepseek-20260607-101500"


def test_tag_is_appended() -> None:
    rid = build_run_id("demo", "20260607-101500", tag="i2", exists=lambda _r: False)
    assert rid == "demo-20260607-101500-i2"


def test_collision_appends_counter() -> None:
    taken = {"demo-20260607-101500"}
    rid = build_run_id("demo", "20260607-101500", tag=None, exists=lambda r: r in taken)
    assert rid == "demo-20260607-101500-2"


def test_collision_counter_increments_until_free() -> None:
    taken = {
        "demo-20260607-101500",
        "demo-20260607-101500-2",
        "demo-20260607-101500-3",
    }
    rid = build_run_id("demo", "20260607-101500", tag=None, exists=lambda r: r in taken)
    assert rid == "demo-20260607-101500-4"


def test_tag_and_collision_compose() -> None:
    taken = {"demo-20260607-101500-i1"}
    rid = build_run_id("demo", "20260607-101500", tag="i1", exists=lambda r: r in taken)
    assert rid == "demo-20260607-101500-i1-2"
