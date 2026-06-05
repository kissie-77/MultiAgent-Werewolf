"""Wolf-team membership helpers for strategy layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_werewolf.game_runtime.types import Camp

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import PlayerProtocol

_BLOOD_MOON_APOSTLE = "Blood Moon Apostle"
_HIDDEN_WOLF = "Hidden Wolf"


def participates_in_wolf_team(player: PlayerProtocol) -> bool:
    """Whether the player joins wolf-team night discussion and votes."""
    if player.get_camp() != Camp.WEREWOLF:
        return False
    role = player.role
    if getattr(role, "name", None) == _BLOOD_MOON_APOSTLE and hasattr(role, "transformed"):
        return bool(getattr(role, "transformed", True))
    return True


def seer_apparent_camp(target: PlayerProtocol) -> Camp:
    """Camp shown to Seer checks (hidden wolf / untransformed blood moon)."""
    if getattr(target.role, "name", None) == _HIDDEN_WOLF:
        return Camp.VILLAGER
    if (
        getattr(target.role, "name", None) == _BLOOD_MOON_APOSTLE
        and hasattr(target.role, "transformed")
        and not getattr(target.role, "transformed", True)
    ):
        return Camp.VILLAGER
    return target.get_camp()
