"""Interactive startup menu for the console CLI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StartupSelection:
    participation: str
    rules: str
    human_seat: str | None
    players: int | None


_PARTICIPATION_OPTIONS: dict[str, tuple[str, str | None]] = {
    "1": ("all_agent", None),
    "2": ("human_mixed", "1"),
}

_RULE_OPTIONS: dict[str, str] = {
    "1": "basic",
    "2": "badge_flow",
    "3": "extended_roles",
}

_RULE_PLAYER_COUNTS: dict[str, int] = {
    "basic": 6,
    "badge_flow": 12,
    "extended_roles": 12,
}

_MIN_PLAYERS = 6
_MAX_PLAYERS = 20


def _prompt_choice(prompt: str, valid_options: set[str], default: str) -> str:
    while True:
        raw = input(prompt).strip()
        choice = raw or default
        if choice in valid_options:
            return choice
        print(f"输入无效，请输入 {', '.join(sorted(valid_options))}。")


def _prompt_player_count(default: int) -> int:
    while True:
        raw = input(
            f"请输入本局总人数（{_MIN_PLAYERS}-{_MAX_PLAYERS}，默认 {default}）："
        ).strip()
        value = raw or str(default)
        if value.isdigit() and _MIN_PLAYERS <= int(value) <= _MAX_PLAYERS:
            return int(value)
        print(f"输入无效，请输入 {_MIN_PLAYERS} 到 {_MAX_PLAYERS} 的整数。")


def _prompt_human_seat(default: str = "1", *, max_seat: int = _MAX_PLAYERS) -> str:
    while True:
        raw = input(f"请输入人类玩家座位号（1-{max_seat}，默认 {default}）：").strip()
        seat = raw or default
        if seat.isdigit() and 1 <= int(seat) <= max_seat:
            return seat
        print(f"输入无效，请输入 1 到 {max_seat} 的整数。")


def prompt_startup_selection() -> StartupSelection:
    print("先选参与方式：")
    print("1. 全 Agent 对局")
    print("2. 人机混战")
    participation_choice = _prompt_choice("请输入 1 或 2（默认 1）：", {"1", "2"}, "1")

    print("")
    print("再选规则模式：")
    print("1. 基础对局")
    print("2. 警徽流对局")
    print("3. 扩展角色对局")
    rules_choice = _prompt_choice("请输入 1、2 或 3（默认 2）：", {"1", "2", "3"}, "2")

    rules = _RULE_OPTIONS[rules_choice]
    player_count = _prompt_player_count(default=_RULE_PLAYER_COUNTS[rules])

    participation, human_seat = _PARTICIPATION_OPTIONS[participation_choice]
    if participation_choice == "2":
        human_seat = _prompt_human_seat(default=human_seat or "1", max_seat=player_count)

    return StartupSelection(
        participation=participation,
        rules=rules,
        human_seat=human_seat,
        players=player_count,
    )
