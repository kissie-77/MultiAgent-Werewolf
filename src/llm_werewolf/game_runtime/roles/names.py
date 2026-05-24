"""与 ``Role.get_config().name`` 一致的角色名常量与判定辅助。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_werewolf.game_runtime.types import Camp

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import PlayerProtocol


class RoleNames:
    """``RoleConfig.name`` 规范值（与 roles/*.py 中 get_config 保持一致）。"""

    VILLAGER = "Villager"
    SEER = "Seer"
    WITCH = "Witch"
    HUNTER = "Hunter"
    GUARD = "Guard"
    IDIOT = "Idiot"
    ELDER = "Elder"
    KNIGHT = "Knight"
    MAGICIAN = "Magician"
    CUPID = "Cupid"
    RAVEN = "Raven"
    GRAVEYARD_KEEPER = "Graveyard Keeper"

    WEREWOLF = "Werewolf"
    ALPHA_WOLF = "Alpha Wolf"
    WHITE_WOLF = "White Wolf"
    WOLF_BEAUTY = "Wolf Beauty"
    GUARDIAN_WOLF = "Guardian Wolf"
    HIDDEN_WOLF = "Hidden Wolf"
    BLOOD_MOON_APOSTLE = "Blood Moon Apostle"
    NIGHTMARE_WOLF = "Nightmare Wolf"

    THIEF = "Thief"
    LOVER = "Lover"
    WHITE_LOVER_WOLF = "White Lover Wolf"


def role_name_is(role: object, expected: str) -> bool:
    """判断角色实例的 ``name`` 是否与规范名一致。"""
    return getattr(role, "name", None) == expected


def player_camp_is(player: PlayerProtocol, camp: Camp) -> bool:
    """判断玩家阵营（``get_camp()`` 返回 Camp 枚举）。"""
    return player.get_camp() == camp


def is_untransformed_blood_moon(role: object) -> bool:
    """血月使徒尚未变身。"""
    return (
        role_name_is(role, RoleNames.BLOOD_MOON_APOSTLE)
        and hasattr(role, "transformed")
        and not getattr(role, "transformed", True)
    )


def participates_in_wolf_team(player: PlayerProtocol) -> bool:
    """是否参与狼队夜间讨论与投票（未变身血月使徒排除）。"""
    if not player_camp_is(player, Camp.WEREWOLF):
        return False
    return not is_untransformed_blood_moon(player.role)


def seer_apparent_camp(target: PlayerProtocol) -> Camp:
    """预言家查验时对目标显示的阵营（含隐狼 / 未变身血月伪装）。"""
    if role_name_is(target.role, RoleNames.HIDDEN_WOLF):
        return Camp.VILLAGER
    if is_untransformed_blood_moon(target.role):
        return Camp.VILLAGER
    return target.get_camp()
