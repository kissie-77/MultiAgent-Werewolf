"""Task 5: pure batch distribution planning."""

from __future__ import annotations

import pytest

from llm_werewolf.interface.cli.fleet.planner import plan_batch


def test_round_robin_distribution() -> None:
    items = plan_batch(count=5, backend_urls=["A", "B"], stagger=0.0)
    assert [i.backend_url for i in items] == ["A", "B", "A", "B", "A"]
    assert [i.seq for i in items] == [0, 1, 2, 3, 4]


def test_stagger_delays() -> None:
    items = plan_batch(count=4, backend_urls=["A", "B"], stagger=1.5)
    assert [i.delay_s for i in items] == [0.0, 1.5, 3.0, 4.5]


def test_count_less_than_backends() -> None:
    items = plan_batch(count=1, backend_urls=["A", "B", "C"], stagger=0.0)
    assert len(items) == 1
    assert items[0].backend_url == "A"


def test_validation() -> None:
    with pytest.raises(ValueError):
        plan_batch(count=0, backend_urls=["A"], stagger=0.0)
    with pytest.raises(ValueError):
        plan_batch(count=2, backend_urls=[], stagger=0.0)
    with pytest.raises(ValueError):
        plan_batch(count=2, backend_urls=["A"], stagger=-1.0)
