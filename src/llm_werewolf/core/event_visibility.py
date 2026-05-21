"""Default Event.visible_to rules (standard werewolf information model)."""

from __future__ import annotations

from llm_werewolf.core.types import EventType

# None = public to all players.
PRIVATE_ACTOR_TYPES: frozenset[EventType] = frozenset({
    EventType.ROLE_ACTING,
    EventType.SEER_CHECKED,
    EventType.WITCH_SAVED,
    EventType.GUARD_PROTECTED,
    EventType.WITCH_POISONED,
    EventType.VOTE_CAST,
    EventType.SHERIFF_VOTE_CAST,
})

WOLF_TEAM_TYPES: frozenset[EventType] = frozenset({
    EventType.PLAYER_DISCUSSION,
})

# Event types where visibility is resolved from data["player_id"] or data["voter_id"].
ACTOR_ID_KEYS: dict[EventType, str] = {
    EventType.ROLE_ACTING: "player_id",
    EventType.SEER_CHECKED: "player_id",
    EventType.WITCH_SAVED: "player_id",
    EventType.GUARD_PROTECTED: "player_id",
    EventType.WITCH_POISONED: "player_id",
    EventType.VOTE_CAST: "voter_id",
    EventType.SHERIFF_VOTE_CAST: "voter_id",
    EventType.ERROR: "player_id",
}

# Cupid link: only cupid knows targets on night 1.
CUPID_ACTOR_KEY = "player_id"


def resolve_visible_to(
    event_type: EventType,
    data: dict | None,
    *,
    wolf_player_ids: list[str] | None = None,
) -> list[str] | None:
    """Return default visible_to for an event before it is logged."""
    if event_type in WOLF_TEAM_TYPES:
        return list(wolf_player_ids) if wolf_player_ids else None

    if event_type == EventType.LOVERS_LINKED:
        actor_id = (data or {}).get(CUPID_ACTOR_KEY)
        return [actor_id] if actor_id else None

    if event_type == EventType.MESSAGE and (data or {}).get("visibility") == "wolf_team":
        return list(wolf_player_ids) if wolf_player_ids else None

    if event_type == EventType.MESSAGE and (data or {}).get("player_id"):
        return [(data or {})["player_id"]]

    if event_type in PRIVATE_ACTOR_TYPES:
        key = ACTOR_ID_KEYS.get(event_type, "player_id")
        actor_id = (data or {}).get(key) or (data or {}).get("player_id")
        return [actor_id] if actor_id else None

    return None
