"""默认 Event.visible_to 规则（标准狼人杀信息模型）。"""

from __future__ import annotations

from llm_werewolf.game_runtime.types import EventType

# None = 对所有玩家公开。
PRIVATE_ACTOR_TYPES: frozenset[EventType] = frozenset({
    EventType.ROLE_ACTING,
    EventType.SEER_CHECKED,
    EventType.WITCH_SAVED,
    EventType.GUARD_PROTECTED,
    EventType.WITCH_POISON_USED,
    EventType.WITCH_POISONED,
    EventType.SHERIFF_VOTE_CAST,
    EventType.GRAVEYARD_KEEPER_CHECK,
    EventType.WOLF_BEAUTY_CHARMED,
    EventType.NIGHTMARE_BLOCKED,
    EventType.RAVEN_MARKED,
})

# 仅写入复盘/评测日志，不向任何玩家 observation 暴露。
REPLAY_ONLY_TYPES: frozenset[EventType] = frozenset({
    EventType.VOTE_INTENTION_SNAPSHOT,
    EventType.BELIEF_SNAPSHOT,
})

WOLF_TEAM_TYPES: frozenset[EventType] = frozenset({
    EventType.PLAYER_DISCUSSION,
    EventType.WHITE_WOLF_KILLED,
    EventType.GUARDIAN_WOLF_PROTECTED,
})
WOLF_TEAM_MESSAGE_ACTIONS: frozenset[str] = frozenset({
    "werewolves_wake",
    "werewolves_vote",
    "werewolves_sleep",
    "werewolf_no_votes",
})

# 刀口结算：狼队知道最终刀口，存活女巫也会得知刀口以决定是否用药。
WOLF_TEAM_AND_WITCH_TYPES: frozenset[EventType] = frozenset({
    EventType.WEREWOLF_KILLED
})

# 对话写入 Event 仅供复盘/UI——LLM 决策提示从 MsgHub 读取。
HUB_DIALOGUE_EVENT_TYPES: frozenset[EventType] = frozenset({
    EventType.PLAYER_SPEECH,
    EventType.PLAYER_DISCUSSION,
    EventType.SHERIFF_CANDIDATE_SPEECH,
})

# 圆桌调用点的别名。
ROUNDTABLE_HUB_EVENT_TYPES: frozenset[EventType] = HUB_DIALOGUE_EVENT_TYPES

# 可见性由 data["player_id"] 或 data["voter_id"] 解析的事件类型。
ACTOR_ID_KEYS: dict[EventType, str] = {
    EventType.ROLE_ACTING: "player_id",
    EventType.SEER_CHECKED: "player_id",
    EventType.WITCH_SAVED: "player_id",
    EventType.GUARD_PROTECTED: "player_id",
    EventType.WITCH_POISON_USED: "player_id",
    EventType.WITCH_POISONED: "player_id",
    EventType.GRAVEYARD_KEEPER_CHECK: "player_id",
    EventType.WOLF_BEAUTY_CHARMED: "player_id",
    EventType.NIGHTMARE_BLOCKED: "player_id",
    EventType.RAVEN_MARKED: "player_id",
    EventType.SHERIFF_VOTE_CAST: "voter_id",
    EventType.ERROR: "player_id",
}

# 丘比特连结：首夜仅丘比特知晓目标。
CUPID_ACTOR_KEY = "player_id"


def resolve_visible_to(
    event_type: EventType,
    data: dict | None,
    *,
    wolf_player_ids: list[str] | None = None,
    witch_player_ids: list[str] | None = None,
) -> list[str] | None:
    """在事件写入日志前返回默认的 visible_to。"""
    if event_type in WOLF_TEAM_AND_WITCH_TYPES:
        visible: list[str] = []
        for player_id in [*(wolf_player_ids or []), *(witch_player_ids or [])]:
            if player_id not in visible:
                visible.append(player_id)
        return visible

    if event_type in WOLF_TEAM_TYPES:
        return list(wolf_player_ids) if wolf_player_ids else []

    if event_type == EventType.LOVERS_LINKED:
        actor_id = (data or {}).get(CUPID_ACTOR_KEY)
        return [actor_id] if actor_id else []

    if event_type == EventType.MESSAGE and (data or {}).get("visibility") == "wolf_team":
        return list(wolf_player_ids) if wolf_player_ids else []

    if event_type == EventType.MESSAGE and (data or {}).get("action") in WOLF_TEAM_MESSAGE_ACTIONS:
        return list(wolf_player_ids) if wolf_player_ids else []

    if event_type == EventType.MESSAGE and (data or {}).get("player_id"):
        return [(data or {})["player_id"]]

    if event_type in PRIVATE_ACTOR_TYPES:
        key = ACTOR_ID_KEYS.get(event_type, "player_id")
        actor_id = (data or {}).get(key) or (data or {}).get("player_id")
        return [actor_id] if actor_id else []

    if event_type in REPLAY_ONLY_TYPES:
        return []

    return None
