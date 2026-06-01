"""Resolve frontend config identifiers to on-disk YAML paths."""

from __future__ import annotations

from pathlib import Path

from llm_werewolf.interface.cli.runtime.modes import resolve_config_path


def resolve_config_for_start(
    configs_dir: Path,
    *,
    config_id: str | None = None,
    config_path: str | None = None,
    participation: str | None = None,
    rules: str | None = None,
) -> Path:
    """Resolve start-game parameters to an existing config file."""
    if config_path:
        path = Path(config_path)
        if not path.is_file():
            path = configs_dir / config_path
        if not path.is_file():
            msg = f"Config file not found: {config_path}"
            raise FileNotFoundError(msg)
        return path

    if config_id:
        candidate = configs_dir / f"{config_id}.yaml"
        if candidate.is_file():
            return candidate
        msg = f"Unknown config_id: {config_id}"
        raise FileNotFoundError(msg)

    resolved_participation = participation or "all_agent"
    if rules is not None:
        resolved_rules = rules
    elif participation:
        resolved_rules = "badge_flow"
    else:
        resolved_rules = "basic"

    if participation or rules is not None or not (config_path or config_id):
        rel = resolve_config_path(
            None,
            participation=resolved_participation,
            rules=resolved_rules,
        )
        candidate = Path(rel)
        if candidate.is_file():
            return candidate
        nested = configs_dir / candidate.name
        if nested.is_file():
            return nested
        msg = f"Mode config not found for participation={resolved_participation!r}, rules={resolved_rules!r}"
        raise FileNotFoundError(msg)

    msg = "Must provide config_id, config_path, or participation+rules"
    raise ValueError(msg)
