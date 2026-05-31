"""CLI runtime helpers: player count, human seat overrides."""

from __future__ import annotations

import pytest

from llm_werewolf.game_runtime.config import PlayerConfig, PlayersConfig
from llm_werewolf.interface.cli.runtime.overrides import apply_human_seats, parse_seat_list
from llm_werewolf.interface.cli.runtime.player_count import resize_players_config


def _demo_config(count: int = 6) -> PlayersConfig:
    return PlayersConfig(
        language="zh-CN",
        players=[PlayerConfig(name=f"P{i}", model="demo") for i in range(1, count + 1)],
    )


def test_parse_seat_list_variants() -> None:
    assert parse_seat_list(None) == []
    assert parse_seat_list("") == []
    assert parse_seat_list(2) == [2]
    assert parse_seat_list("1, 3") == [1, 3]
    assert parse_seat_list([1, 2]) == [1, 2]
    assert parse_seat_list((4,)) == [4]


def test_apply_human_seats() -> None:
    cfg = _demo_config()
    updated = apply_human_seats(cfg, [1, 3])
    assert updated.players[0].model == "human"
    assert updated.players[2].model == "human"
    assert updated.players[1].model == "demo"


def test_apply_human_seats_noop() -> None:
    cfg = _demo_config()
    assert apply_human_seats(cfg, []) is cfg


def test_apply_human_seats_out_of_range() -> None:
    with pytest.raises(ValueError, match="超出范围"):
        apply_human_seats(_demo_config(), [7])


def test_resize_players_config_same_size() -> None:
    cfg = _demo_config()
    assert resize_players_config(cfg, 6) is cfg


def test_resize_players_config_expand() -> None:
    cfg = resize_players_config(_demo_config(), 8)
    assert len(cfg.players) == 8
    assert all(p.model == "demo" for p in cfg.players)


def test_resize_players_config_shrink() -> None:
    cfg = resize_players_config(_demo_config(8), 6)
    assert len(cfg.players) == 6


def test_resize_players_config_invalid_count() -> None:
    with pytest.raises(ValueError, match="必须在 6-20"):
        resize_players_config(_demo_config(), 5)


def test_resize_players_config_cannot_drop_human() -> None:
    cfg = apply_human_seats(_demo_config(8), [7, 8])
    with pytest.raises(ValueError, match="human 座位"):
        resize_players_config(cfg, 6)


def test_resize_players_config_cannot_shrink_past_human_tail() -> None:
    cfg = apply_human_seats(_demo_config(8), [7, 8])
    with pytest.raises(ValueError, match="丢弃 human"):
        resize_players_config(cfg, 6)
