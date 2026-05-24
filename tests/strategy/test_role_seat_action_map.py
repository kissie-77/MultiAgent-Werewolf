"""ROLE_SEAT_ACTION 使用 catalog 中的运行时角色名。"""

from llm_werewolf.strategy.role_prompts import ROLE_SEAT_ACTION, GamePrompts
from llm_werewolf.game_runtime.roles.registry import CATALOG_TO_RUNTIME_NAME


def test_role_seat_action_runtime_alpha_wolf() -> None:
    runtime = CATALOG_TO_RUNTIME_NAME["AlphaWolf"]
    assert runtime == "Alpha Wolf"
    assert ROLE_SEAT_ACTION[runtime] == GamePrompts.WOLF_OPEN


def test_role_seat_action_runtime_graveyard_keeper() -> None:
    runtime = CATALOG_TO_RUNTIME_NAME["GraveyardKeeper"]
    assert ROLE_SEAT_ACTION[runtime] != GamePrompts.PROPHET_ACTION
