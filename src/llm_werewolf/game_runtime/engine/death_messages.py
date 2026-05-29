"""出局/淘汰公告文案（是否公开身份由 GameConfig 控制）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import PlayerProtocol
    from llm_werewolf.game_runtime.locale import Locale


def elimination_announcement(
    locale: Locale, player: PlayerProtocol, *, show_role: bool
) -> tuple[str, dict]:
    """生成投票淘汰事件的消息与 data（不含身份时 data 不含 role）。"""
    if show_role:
        role_name = player.get_role_name()
        message = locale.get("player_eliminated", player=player.name, role=role_name)
        data = {"player_id": player.player_id, "role": role_name, "role_revealed": True}
    else:
        message = locale.get("player_eliminated_hidden", player=player.name)
        data = {"player_id": player.player_id, "role_revealed": False}
    return message, data
