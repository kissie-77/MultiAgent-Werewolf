"""Entry-layer game mode selection."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass


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
        config_path=Path("configs/demo-6.yaml"),
        description="基础全自动对局（不带警徽流）：6 人 Demo 对局。",
    ),
    ("all_agent", "badge_flow"): GameMode(
        participation="all_agent",
        rules="badge_flow",
        config_path=Path("configs/llm-12p-agentscope.yaml"),
        description="12 人 AgentScope 对局：主展示路线，包含警长/警徽相关流程。",
    ),
    ("all_agent", "extended_roles"): GameMode(
        participation="all_agent",
        rules="extended_roles",
        config_path=Path("configs/llm-12p-doubao.yaml"),
        description="扩展人数 AgentScope 对局：用于角色扩展验证。",
    ),
    ("human_mixed", "basic"): GameMode(
        participation="human_mixed",
        rules="basic",
        config_path=Path("configs/xiaomi.yaml"),
        description="基础人机混战：使用真实 LLM 配置，并将指定座位替换为人类玩家。",
    ),
    ("human_mixed", "badge_flow"): GameMode(
        participation="human_mixed",
        rules="badge_flow",
        config_path=Path("configs/llm-12p-agentscope.yaml"),
        description="警徽流人机混战：使用真实 LLM 配置，并将指定座位替换为人类玩家。",
    ),
    ("human_mixed", "extended_roles"): GameMode(
        participation="human_mixed",
        rules="extended_roles",
        config_path=Path("configs/llm-12p-doubao.yaml"),
        description="扩展角色人机混战：使用真实 LLM 配置，并将指定座位替换为人类玩家。",
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
