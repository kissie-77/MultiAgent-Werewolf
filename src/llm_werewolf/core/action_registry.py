"""将动作类型映射到夜间优先级与事件日志处理器。"""

from __future__ import annotations

from llm_werewolf.core.types import ActionPriority

ACTION_PRIORITY_BY_CLASS: dict[str, int] = {
    "CupidLinkAction": ActionPriority.CUPID.value,
    "NightmareWolfBlockAction": ActionPriority.NIGHTMARE_WOLF.value,
    "GuardProtectAction": ActionPriority.GUARD.value,
    "GuardianWolfProtectAction": ActionPriority.GUARD.value,
    "WerewolfVoteAction": ActionPriority.WEREWOLF.value,
    "WerewolfKillAction": ActionPriority.WEREWOLF.value,
    "WolfBeautyCharmAction": ActionPriority.WEREWOLF.value,
    "WhiteWolfKillAction": ActionPriority.WHITE_WOLF.value,
    "WitchSaveAction": ActionPriority.WITCH.value,
    "WitchPoisonAction": ActionPriority.WITCH.value,
    "SeerCheckAction": ActionPriority.SEER.value,
    "GraveyardKeeperCheckAction": ActionPriority.GRAVEYARD_KEEPER.value,
    "RavenMarkAction": ActionPriority.RAVEN.value,
}


def get_action_priority(action_class_name: str) -> int:
    """返回动作类名对应的夜间执行优先级。"""
    return ACTION_PRIORITY_BY_CLASS.get(action_class_name, 0)
