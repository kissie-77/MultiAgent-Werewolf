"""Resolve explicit and template-based player configs for entrypoints."""

from __future__ import annotations

from llm_werewolf.game_runtime.config import PlayerConfig, PlayersConfig, PlayerTemplateConfig

MIN_PLAYERS = 6
MAX_PLAYERS = 20


def resolve_participation(
    players_config: PlayersConfig,
    *,
    requested_participation: str,
) -> str:
    """Use the roster mode when config declares one, otherwise keep CLI mode."""
    if players_config.player_roster is not None:
        return players_config.player_roster.mode
    return requested_participation


def resolve_player_configs(
    players_config: PlayersConfig,
    *,
    num_players: int | None = None,
) -> list[PlayerConfig]:
    """Return the concrete ordered player configs for a game."""
    if players_config.player_roster is None:
        if players_config.players is None:
            msg = "PlayersConfig must provide players or player_roster"
            raise ValueError(msg)
        if num_players is not None and num_players != len(players_config.players):
            msg = "num_players override requires a player_roster config"
            raise ValueError(msg)
        return list(players_config.players)

    roster = players_config.player_roster
    count = num_players if num_players is not None else roster.count
    _validate_player_count(count)

    if roster.mode == "human_mixed":
        human = roster.human or PlayerConfig(name="HumanPlayer", model="human")
        players = [human]
        players.extend(
            _player_from_template(roster.llm_template, seat_number)
            for seat_number in range(2, count + 1)
        )
    else:
        players = [
            _player_from_template(roster.llm_template, seat_number)
            for seat_number in range(1, count + 1)
        ]

    _validate_unique_names(players)
    return players


def _player_from_template(
    template: PlayerTemplateConfig,
    seat_number: int,
) -> PlayerConfig:
    return PlayerConfig(
        name=f"{template.name_prefix}{seat_number}",
        model=template.model,
        base_url=template.base_url,
        api_key_env=template.api_key_env,
        reasoning_effort=template.reasoning_effort,
        plan=template.plan,
    )


def _validate_player_count(num_players: int) -> None:
    if num_players < MIN_PLAYERS or num_players > MAX_PLAYERS:
        msg = f"num_players must be between {MIN_PLAYERS} and {MAX_PLAYERS}"
        raise ValueError(msg)


def _validate_unique_names(players: list[PlayerConfig]) -> None:
    names = [player.name for player in players]
    if len(names) == len(set(names)):
        return
    duplicates = {name for name in names if names.count(name) > 1}
    msg = f"Duplicate player names found: {duplicates}"
    raise ValueError(msg)
