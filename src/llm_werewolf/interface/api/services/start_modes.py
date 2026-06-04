"""Build start-game mode options for the HTTP API."""

from __future__ import annotations

from pathlib import Path

from llm_werewolf.game_runtime.utils import load_config
from llm_werewolf.interface.api.models.actions import StartGameModeOption, StartGameModesResponse
from llm_werewolf.interface.cli.runtime.modes import list_modes


def build_start_modes(configs_dir: Path) -> StartGameModesResponse:
    modes: list[StartGameModeOption] = []
    for mode in list_modes():
        if mode.participation == "human_mixed":
            continue
        player_count: int | None = None
        config_id = mode.config_path.stem
        candidate = configs_dir / f"{config_id}.yaml"
        config_path = candidate if candidate.is_file() else mode.config_path
        try:
            cfg = load_config(config_path)
            player_count = len(cfg.players)
        except (ValueError, OSError):
            pass
        modes.append(
            StartGameModeOption(
                participation=mode.participation,
                rules=mode.rules,
                config_id=config_id,
                description=mode.description,
                player_count=player_count,
            )
        )

    extras = [
        ("llm-6p-doubao", "6-player Doubao LLM game"),
        ("llm-12p-doubao", "12-player Doubao LLM game"),
    ]
    seen = {item.config_id for item in modes}
    for config_id, description in extras:
        if config_id in seen:
            continue
        path = configs_dir / f"{config_id}.yaml"
        if not path.is_file():
            continue
        extra_count: int | None = None
        try:
            extra_count = len(load_config(path).players)
        except (ValueError, OSError):
            pass
        modes.append(
            StartGameModeOption(
                participation="all_agent",
                rules="custom",
                config_id=config_id,
                description=description,
                player_count=extra_count,
            )
        )

    return StartGameModesResponse(modes=modes)
