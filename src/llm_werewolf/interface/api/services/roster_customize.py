"""Apply optional roster overrides from POST /games/start (in-memory only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_werewolf.interface.cli.runtime.overrides import apply_human_seats
from llm_werewolf.game_runtime.config.player_config import PlayerConfig, PlayersConfig
from llm_werewolf.game_runtime.config.provider_registry import provider_to_roster_fields
from llm_werewolf.interface.cli.runtime.player_count import resize_players_config

if TYPE_CHECKING:
    from llm_werewolf.interface.api.models.actions import (
        PlayerRosterSlot,
        StartGameRequest,
        PlayerRosterDefaults,
    )

_ROSTER_FIELDS = ("name", "model", "base_url", "api_key_env", "model_env", "plan")


def _extract_updates(source: PlayerRosterDefaults | PlayerRosterSlot) -> dict[str, object]:
    updates: dict[str, object] = {}
    provider = getattr(source, "provider", None)
    if provider:
        updates.update(provider_to_roster_fields(provider))
    for key in _ROSTER_FIELDS:
        value = getattr(source, key, None)
        if value is not None:
            updates[key] = value
    if "model" in updates and "model_env" not in updates:
        updates["model_env"] = None
    return updates


def _rebuild_players_config(cfg: PlayersConfig, players: list[PlayerConfig]) -> PlayersConfig:
    data = cfg.model_dump(mode="json", exclude={"use_agentscope_backend"})
    data["players"] = [player.model_dump(mode="json") for player in players]
    return PlayersConfig.model_validate(data)


def apply_roster_customizations(
    cfg: PlayersConfig,
    *,
    player_count: int | None = None,
    defaults: PlayerRosterDefaults | None = None,
    players: list[PlayerRosterSlot] | None = None,
    human_seats: list[int] | None = None,
) -> PlayersConfig:
    """Merge optional count/name/model/human-seat overrides into a loaded PlayersConfig."""
    result = cfg

    default_updates = _extract_updates(defaults) if defaults is not None else {}
    if default_updates:
        merged: list[PlayerConfig] = []
        for player in result.players:
            if player.model == "human":
                merged.append(player)
            else:
                merged.append(player.model_copy(update=default_updates))
        result = _rebuild_players_config(result, merged)

    if player_count is not None:
        result = resize_players_config(result, player_count)

    if players:
        roster = list(result.players)
        for index, slot in enumerate(players):
            if index >= len(roster):
                break
            slot_updates = _extract_updates(slot)
            if slot_updates:
                roster[index] = roster[index].model_copy(update=slot_updates)
        result = _rebuild_players_config(result, roster)

    if human_seats:
        result = apply_human_seats(result, human_seats)

    return result


def has_roster_customizations(request: StartGameRequest) -> bool:
    return any(
        value is not None and value != []
        for value in (
            request.player_count,
            request.defaults,
            request.players,
            request.human_seats,
        )
    )


def prepare_start_players_config(base: PlayersConfig, request: StartGameRequest) -> PlayersConfig | None:
    if not has_roster_customizations(request):
        return None
    return apply_roster_customizations(
        base,
        player_count=request.player_count,
        defaults=request.defaults,
        players=request.players,
        human_seats=request.human_seats,
    )


def resolve_start_rules(request: StartGameRequest) -> tuple[str, str]:
    if request.config_id or request.config_path:
        return request.participation or "all_agent", request.rules or "custom"
    participation = request.participation or "all_agent"
    if request.rules is not None:
        rules = request.rules
    elif request.participation:
        rules = "badge_flow"
    else:
        rules = "basic"
    return participation, rules
