"""Entry-layer game mode selection."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

from llm_werewolf.game_runtime.config.standard_boards import standard_config_path


@dataclass(frozen=True)
class GameMode:
    """A user-facing game startup mode."""

    participation: str
    rules: str
    config_path: Path
    description: str


_MODE_CONFIGS: dict[tuple[str, str], GameMode] = {
    ("all_agent", "basic"): GameMode(
        participation="all_agent",
        rules="basic",
        config_path=Path(standard_config_path(6)),
        description="6 人标准局：豆包（火山方舟）全自动对局（不带警徽流）。",
    ),
    ("all_agent", "badge_flow"): GameMode(
        participation="all_agent",
        rules="badge_flow",
        config_path=Path(standard_config_path(12)),
        description="12 人标准局：豆包（火山方舟）全自动对局，含警长/警徽流程。",
    ),
    ("all_agent", "extended_roles"): GameMode(
        participation="all_agent",
        rules="extended_roles",
        config_path=Path(standard_config_path(16)),
        description="16 人标准局：豆包（火山方舟）扩展角色对局。",
    ),
    ("human_mixed", "basic"): GameMode(
        participation="human_mixed",
        rules="basic",
        config_path=Path(standard_config_path(6)),
        description="6 人标准人机混战：CLI stdin 人类 + 豆包机器人。",
    ),
    ("human_mixed", "badge_flow"): GameMode(
        participation="human_mixed",
        rules="badge_flow",
        config_path=Path(standard_config_path(12)),
        description="12 人标准警徽流人机混战。",
    ),
    ("human_mixed", "extended_roles"): GameMode(
        participation="human_mixed",
        rules="extended_roles",
        config_path=Path(standard_config_path(16)),
        description="16 人标准扩展角色人机混战。",
    ),
}


def resolve_config_path(
    config: str | None = None, *, participation: str = "all_agent", rules: str = "badge_flow"
) -> Path:
    """Resolve CLI mode arguments to a concrete config path."""
    if config:
        return Path(config)

    key = (participation, rules)
    mode = _MODE_CONFIGS.get(key)
    if mode is None:
        available = ", ".join(f"{p}/{r}" for p, r in sorted(_MODE_CONFIGS))
        msg = (
            f"Unsupported mode: participation={participation!r}, rules={rules!r}. "
            f"Available modes: {available}."
        )
        raise ValueError(msg)
    return mode.config_path


def list_modes() -> list[GameMode]:
    """Return supported entry-layer modes."""
    return list(_MODE_CONFIGS.values())
