"""Build start-game mode options for the HTTP API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_werewolf.game_runtime.config.standard_boards import (
    STANDARD_BOARD_SIZES,
    standard_config_id,
)
from llm_werewolf.interface.api.models.actions import StartGameModeOption, StartGameModesResponse

if TYPE_CHECKING:
    from pathlib import Path

_BOARD_DESCRIPTIONS: dict[int, str] = {
    4: "4-player standard board (1 wolf / seer / witch / villager)",
    6: "6-player standard board (2 wolves / seer / witch / 2 villagers)",
    8: "8-player standard board (2 wolves / core specials / villagers)",
    12: "12-player standard board (3 wolves / extended specials)",
    16: "16-player standard board (5 wolves / full specials)",
}


def build_start_modes(configs_dir: Path) -> StartGameModesResponse:
    modes: list[StartGameModeOption] = []

    web_human = StartGameModeOption(
        participation="human_vs_ai",
        rules="basic",
        config_id=standard_config_id(6),
        description="Browser human vs LLM agents on the 6-player standard board",
        player_count=6,
    )
    modes.append(web_human)

    for count in STANDARD_BOARD_SIZES:
        config_id = standard_config_id(count)
        path = configs_dir / f"{config_id}.yaml"
        if not path.is_file():
            continue
        modes.append(
            StartGameModeOption(
                participation="all_agent",
                rules="standard",
                config_id=config_id,
                description=_BOARD_DESCRIPTIONS[count],
                player_count=count,
            )
        )

    return StartGameModesResponse(modes=modes)
