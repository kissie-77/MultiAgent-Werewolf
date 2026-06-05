"""Load externalized game-flow prompts and plan strategies."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_STRATEGY_ROOT = Path(__file__).resolve().parent.parent
_PHASE_PROMPTS_ROOT = _STRATEGY_ROOT / "prompts" / "phase"
_PLAN_PROMPTS_ROOT = _STRATEGY_ROOT / "prompts" / "plans"
_GENERATED_PHASE_ROOT = Path("artifacts") / "prompt_phase"
_GENERATED_PLAN_ROOT = Path("artifacts") / "prompt_plans"
_EXTRA_PHASE_ROOTS: list[Path] = []
_EXTRA_PLAN_ROOTS: list[Path] = []


def phase_prompt_search_roots() -> list[Path]:
    roots = [_PHASE_PROMPTS_ROOT, _GENERATED_PHASE_ROOT, *_EXTRA_PHASE_ROOTS]
    env_roots = os.getenv("LLM_WEREWOLF_PHASE_PROMPT_ROOTS", "")
    for raw in env_roots.split(os.pathsep):
        value = raw.strip()
        if value:
            roots.append(Path(value))
    return _dedupe_roots(roots)


def plan_prompt_search_roots() -> list[Path]:
    roots = [_PLAN_PROMPTS_ROOT, _GENERATED_PLAN_ROOT, *_EXTRA_PLAN_ROOTS]
    env_roots = os.getenv("LLM_WEREWOLF_PLAN_PROMPT_ROOTS", "")
    for raw in env_roots.split(os.pathsep):
        value = raw.strip()
        if value:
            roots.append(Path(value))
    return _dedupe_roots(roots)


def _dedupe_roots(roots: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for root in roots:
        resolved = root.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(root)
    return out


def register_phase_prompt_search_root(root: str | Path) -> None:
    path = Path(root)
    if path not in _EXTRA_PHASE_ROOTS:
        _EXTRA_PHASE_ROOTS.append(path)
    _clear_phase_caches()


def register_plan_prompt_search_root(root: str | Path) -> None:
    path = Path(root)
    if path not in _EXTRA_PLAN_ROOTS:
        _EXTRA_PLAN_ROOTS.append(path)
    _clear_plan_caches()


def _clear_phase_caches() -> None:
    list_phase_versions.cache_clear()
    resolve_phase_prompt_dir.cache_clear()
    load_phase_prompts.cache_clear()
    load_seat_action_map.cache_clear()


def _clear_plan_caches() -> None:
    list_plan_versions.cache_clear()
    resolve_plan_prompt_dir.cache_clear()
    load_plan_bundle.cache_clear()


@lru_cache(maxsize=8)
def list_phase_versions(*, fallback: str = "v1") -> tuple[str, ...]:
    versions: set[str] = set()
    for root in phase_prompt_search_roots():
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if path.is_dir() and (path / "prompts.yaml").is_file():
                versions.add(path.name)
    if not versions:
        return (fallback,)
    from llm_werewolf.strategy.registry.role_version_manifest import version_sort_key

    return tuple(sorted(versions, key=version_sort_key))


@lru_cache(maxsize=8)
def list_plan_versions(*, fallback: str = "v1") -> tuple[str, ...]:
    versions: set[str] = set()
    for root in plan_prompt_search_roots():
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if path.is_dir() and (path / "plans.yaml").is_file():
                versions.add(path.name)
    if not versions:
        return (fallback,)
    from llm_werewolf.strategy.registry.role_version_manifest import version_sort_key

    return tuple(sorted(versions, key=version_sort_key))


def resolve_latest_phase_version(*, fallback: str = "v1") -> str:
    from llm_werewolf.strategy.registry.role_version_manifest import pick_latest_version

    return pick_latest_version(list_phase_versions(fallback=fallback), fallback=fallback)


def resolve_latest_plan_version(*, fallback: str = "v1") -> str:
    from llm_werewolf.strategy.registry.role_version_manifest import pick_latest_version

    return pick_latest_version(list_plan_versions(fallback=fallback), fallback=fallback)


@lru_cache(maxsize=16)
def resolve_phase_prompt_dir(version: str) -> Path:
    for root in phase_prompt_search_roots():
        candidate = root / version
        if (candidate / "prompts.yaml").is_file():
            return candidate
    msg = f"Unknown phase prompt package '{version}'. Searched: {phase_prompt_search_roots()}"
    raise FileNotFoundError(msg)


@lru_cache(maxsize=16)
def resolve_plan_prompt_dir(version: str) -> Path:
    for root in plan_prompt_search_roots():
        candidate = root / version
        if (candidate / "plans.yaml").is_file():
            return candidate
    msg = f"Unknown plan prompt package '{version}'. Searched: {plan_prompt_search_roots()}"
    raise FileNotFoundError(msg)


@lru_cache(maxsize=8)
def load_phase_prompts(version: str | None = None) -> dict[str, str]:
    resolved = version or resolve_latest_phase_version()
    path = resolve_phase_prompt_dir(resolved) / "prompts.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    prompts = data.get("prompts") if isinstance(data, dict) else None
    if not isinstance(prompts, dict):
        msg = f"Invalid phase prompts file: {path}"
        raise ValueError(msg)
    return {str(key): str(value) for key, value in prompts.items()}


def _resolve_action_value(raw: object, prompts: dict[str, str]) -> str:
    text = str(raw).strip()
    if text in prompts:
        return prompts[text]
    return text


@lru_cache(maxsize=8)
def load_seat_action_map(version: str | None = None) -> dict[str, str]:
    resolved = version or resolve_latest_phase_version()
    prompts = load_phase_prompts(resolved)
    seat_path = resolve_phase_prompt_dir(resolved) / "seat_actions.yaml"
    data = yaml.safe_load(seat_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        msg = f"Invalid seat actions file: {seat_path}"
        raise ValueError(msg)

    catalog_actions = data.get("catalog_actions") or {}
    catalog_to_runtime = data.get("catalog_to_runtime") or {}
    if not isinstance(catalog_actions, dict) or not isinstance(catalog_to_runtime, dict):
        msg = f"Invalid seat actions schema: {seat_path}"
        raise ValueError(msg)

    merged: dict[str, str] = {}
    for catalog, raw_action in catalog_actions.items():
        merged[str(catalog)] = _resolve_action_value(raw_action, prompts)
    for catalog, runtime in catalog_to_runtime.items():
        catalog_key = str(catalog)
        if catalog_key in catalog_actions:
            merged[str(runtime)] = merged[catalog_key]
    return merged


@dataclass(frozen=True)
class PlanBundle:
    plans: dict[str, dict[str, str]]
    role_labels: dict[str, str]
    style_templates: dict[str, str]
    style_order: tuple[str, ...]


@lru_cache(maxsize=8)
def load_plan_bundle(version: str | None = None) -> PlanBundle:
    resolved = version or resolve_latest_plan_version()
    path = resolve_plan_prompt_dir(resolved) / "plans.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        msg = f"Invalid plan strategies file: {path}"
        raise ValueError(msg)

    raw_plans = data.get("plans") or {}
    role_labels = data.get("role_labels") or {}
    style_templates = data.get("style_templates") or {}
    style_order = data.get("style_order") or []
    if not isinstance(raw_plans, dict):
        msg = f"Invalid plans section: {path}"
        raise ValueError(msg)

    plans: dict[str, dict[str, str]] = {}
    for plan_name, payload in raw_plans.items():
        if not isinstance(payload, dict):
            continue
        entry = {str(key): str(value) for key, value in payload.items()}
        entry.setdefault("name", str(plan_name))
        plans[str(plan_name)] = entry

    return PlanBundle(
        plans=plans,
        role_labels={str(k): str(v) for k, v in role_labels.items()} if isinstance(role_labels, dict) else {},
        style_templates={
            str(k): str(v) for k, v in style_templates.items()
        }
        if isinstance(style_templates, dict)
        else {},
        style_order=tuple(str(item) for item in style_order) if isinstance(style_order, list) else (),
    )


def hydrate_prompt_namespace(namespace: type, prompts: dict[str, str]) -> None:
    for key, value in prompts.items():
        setattr(namespace, key, value)
