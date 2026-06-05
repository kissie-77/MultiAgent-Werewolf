"""Load per-role prompt packages: strategy/prompts/roles/<role>/<version>/."""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

import yaml

from llm_werewolf.strategy.registry.prompt_yaml_utils import coerce_text_dict as _coerce_text_dict
from llm_werewolf.strategy.registry.prompt_yaml_utils import coerce_text_list as _coerce_text_list
from llm_werewolf.strategy.registry.prompt_yaml_utils import (
    render_legacy_suggestion as _render_legacy_suggestion,
)

_STRATEGY_ROOT = Path(__file__).resolve().parent.parent
_ROLE_PROMPTS_ROOT = _STRATEGY_ROOT / "prompts" / "roles"
_SHARED_AGENT_BASE = _STRATEGY_ROOT / "prompts" / "shared" / "agent_base.md"
_EXTRA_ROLE_PROMPT_ROOTS: list[Path] = []
_GENERATED_ROLE_PROMPTS_ROOT = Path("artifacts") / "prompt_roles"


def role_prompt_search_roots() -> list[Path]:
    roots = [_ROLE_PROMPTS_ROOT, _GENERATED_ROLE_PROMPTS_ROOT, *_EXTRA_ROLE_PROMPT_ROOTS]
    env_roots = os.getenv("LLM_WEREWOLF_ROLE_PROMPT_ROOTS", "")
    for raw in env_roots.split(os.pathsep):
        value = raw.strip()
        if value:
            roots.append(Path(value))
    seen: set[Path] = set()
    out: list[Path] = []
    for root in roots:
        resolved = root.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(root)
    return out


def register_role_prompt_search_root(root: str | Path) -> None:
    path = Path(root)
    if path not in _EXTRA_ROLE_PROMPT_ROOTS:
        _EXTRA_ROLE_PROMPT_ROOTS.append(path)
    resolve_role_prompt_dir.cache_clear()
    get_role_card.cache_clear()
    list_prompt_versions.cache_clear()


@lru_cache(maxsize=64)
def list_prompt_versions(role_key: str) -> tuple[str, ...]:
    """All prompt package versions for a role across search roots."""
    versions: set[str] = set()
    for root in role_prompt_search_roots():
        role_root = root / role_key
        if not role_root.is_dir():
            continue
        for path in role_root.iterdir():
            if path.is_dir() and (path / "role.yaml").is_file():
                versions.add(path.name)
    from llm_werewolf.strategy.registry.role_version_manifest import version_sort_key

    return tuple(sorted(versions, key=version_sort_key))


def resolve_latest_prompt_version(role_key: str, *, fallback: str = "v1") -> str:
    from llm_werewolf.strategy.registry.role_version_manifest import pick_latest_version

    return pick_latest_version(list_prompt_versions(role_key), fallback=fallback)


@lru_cache(maxsize=256)
def resolve_role_prompt_dir(role_key: str, version: str) -> Path:
    for root in role_prompt_search_roots():
        candidate = root / role_key / version
        if (candidate / "role.yaml").is_file():
            return candidate
    msg = (
        f"Unknown role prompt package '{role_key}@{version}'. "
        f"Searched: {role_prompt_search_roots()}"
    )
    raise FileNotFoundError(msg)


def agent_base_template_path() -> Path:
    if _SHARED_AGENT_BASE.is_file():
        return _SHARED_AGENT_BASE
    msg = f"Missing shared agent base template: {_SHARED_AGENT_BASE}"
    raise FileNotFoundError(msg)


@lru_cache(maxsize=128)
def get_role_card(role_key: str, version: str) -> dict[str, str]:
    role_path = resolve_role_prompt_dir(role_key, version) / "role.yaml"
    data = yaml.safe_load(role_path.read_text(encoding="utf-8")) or {}
    core_principles = _coerce_text_list(data.get("core_principles"))
    phase_strategies = _coerce_text_dict(data.get("phase_strategies"))
    forbidden_actions = _coerce_text_list(data.get("forbidden_actions"))
    examples = _coerce_text_list(data.get("examples"))
    return {
        "role_name": str(data.get("role_name", "")),
        "role_instruction": str(data.get("role_instruction", "")).strip(),
        "suggestion": _render_legacy_suggestion(data),
        "core_principles": "\n".join(core_principles),
        "phase_strategies": "\n".join(
            f"{phase_name}: {rule}" for phase_name, rule in phase_strategies.items()
        ),
        "forbidden_actions": "\n".join(forbidden_actions),
        "examples": "\n".join(examples),
    }


@lru_cache(maxsize=4)
def _agent_base_template() -> str:
    return agent_base_template_path().read_text(encoding="utf-8").strip()


def build_role_strategy_prompt(
    seat_number: int,
    role_key: str,
    plan_text: str,
    *,
    prompt_version: str,
) -> str:
    role_config = get_role_card(role_key, prompt_version)
    template = _agent_base_template()
    return template.format(
        number=seat_number,
        role_name=role_config["role_name"],
        role_instruction=role_config["role_instruction"],
        suggestion=role_config["suggestion"],
        plan=plan_text,
    )


def copy_role_prompt_package(
    role_key: str,
    base_version: str,
    new_version: str,
    *,
    output_root: Path | None = None,
) -> Path:
    """Copy role package to a new version directory under artifacts/prompt_roles."""
    source = resolve_role_prompt_dir(role_key, base_version)
    root = output_root or _GENERATED_ROLE_PROMPTS_ROOT
    target = root / role_key / new_version
    target.mkdir(parents=True, exist_ok=True)
    for name in ("role.yaml", "manifest.yaml"):
        src = source / name
        if src.is_file():
            (target / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    manifest_path = target / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    if not isinstance(manifest, dict):
        manifest = {}
    manifest.update(
        {
            "role": role_key,
            "version": new_version,
            "parent": base_version,
            "status": "generated",
        }
    )
    manifest_path.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    get_role_card.cache_clear()
    resolve_role_prompt_dir.cache_clear()
    register_role_prompt_search_root(root)
    return target
