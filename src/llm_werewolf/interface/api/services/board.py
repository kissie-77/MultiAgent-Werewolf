"""Board preset helpers for role/model pages."""

from __future__ import annotations

from llm_werewolf.game_runtime.roles.catalog import get_catalog
from llm_werewolf.interface.api.models.pages import BoardPreset
from llm_werewolf.game_runtime.config.presets import create_game_config_from_player_count


def build_board_presets(*, min_players: int = 6, max_players: int = 20) -> list[BoardPreset]:
    presets: list[BoardPreset] = []
    for count in range(min_players, max_players + 1):
        try:
            cfg = create_game_config_from_player_count(count)
        except ValueError:
            continue
        werewolf_roles = [r for r in cfg.role_names if _camp_of(r) == "werewolf"]
        villager_roles = [r for r in cfg.role_names if _camp_of(r) == "villager"]
        presets.append(
            BoardPreset(
                player_count=count,
                role_names=list(cfg.role_names),
                werewolf_count=len(werewolf_roles),
                villager_count=len(villager_roles),
                neutral_count=count - len(werewolf_roles) - len(villager_roles),
                timeouts={
                    "night": cfg.night_timeout,
                    "day": cfg.day_timeout,
                    "vote": cfg.vote_timeout,
                },
            )
        )
    return presets


def board_sizes_for_role(role_key: str) -> list[int]:
    sizes: list[int] = []
    for preset in build_board_presets():
        if role_key in preset.role_names:
            sizes.append(preset.player_count)
    return sizes


def _camp_of(role_key: str) -> str:
    for defn in get_catalog():
        if defn.name == role_key:
            return defn.camp.value
    return "unknown"
