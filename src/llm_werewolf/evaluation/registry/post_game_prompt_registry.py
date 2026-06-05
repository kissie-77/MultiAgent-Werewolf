"""Load externalized post-game (replay / coach) prompt packages."""

from __future__ import annotations

import os
import re
from typing import Any
from pathlib import Path
from functools import lru_cache
from dataclasses import dataclass

import yaml

_EVAL_ROOT = Path(__file__).resolve().parent.parent
_REPLAY_PROMPTS_ROOT = _EVAL_ROOT / "prompts" / "replay"
_COACH_PROMPTS_ROOT = _EVAL_ROOT / "prompts" / "coach"
_GENERATED_POST_GAME_ROOT = Path("artifacts") / "prompt_post_game"
_EXTRA_REPLAY_ROOTS: list[Path] = []
_EXTRA_COACH_ROOTS: list[Path] = []

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def replay_prompt_search_roots() -> list[Path]:
    roots = [_REPLAY_PROMPTS_ROOT, _GENERATED_POST_GAME_ROOT / "replay", *_EXTRA_REPLAY_ROOTS]
    env_roots = os.getenv("LLM_WEREWOLF_POST_GAME_REPLAY_PROMPT_ROOTS", "")
    for raw in env_roots.split(os.pathsep):
        value = raw.strip()
        if value:
            roots.append(Path(value))
    return _dedupe_roots(roots)


def coach_prompt_search_roots() -> list[Path]:
    roots = [_COACH_PROMPTS_ROOT, _GENERATED_POST_GAME_ROOT / "coach", *_EXTRA_COACH_ROOTS]
    env_roots = os.getenv("LLM_WEREWOLF_POST_GAME_COACH_PROMPT_ROOTS", "")
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


def register_replay_prompt_search_root(root: str | Path) -> None:
    path = Path(root)
    if path not in _EXTRA_REPLAY_ROOTS:
        _EXTRA_REPLAY_ROOTS.append(path)
    _clear_replay_caches()


def register_coach_prompt_search_root(root: str | Path) -> None:
    path = Path(root)
    if path not in _EXTRA_COACH_ROOTS:
        _EXTRA_COACH_ROOTS.append(path)
    _clear_coach_caches()


def _clear_replay_caches() -> None:
    list_replay_versions.cache_clear()
    resolve_replay_prompt_dir.cache_clear()
    load_replay_prompt_bundle.cache_clear()


def _clear_coach_caches() -> None:
    list_coach_versions.cache_clear()
    resolve_coach_prompt_dir.cache_clear()
    load_coach_semantic_extract_bundle.cache_clear()


def render_template(template: str, **values: object) -> str:
    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            return match.group(0)
        return str(values[key])

    return _PLACEHOLDER_RE.sub(_replace, template)


@lru_cache(maxsize=8)
def list_replay_versions(*, fallback: str = "v1") -> tuple[str, ...]:
    return _list_versions(replay_prompt_search_roots(), marker="system.md", fallback=fallback)


@lru_cache(maxsize=8)
def list_coach_versions(*, fallback: str = "v1") -> tuple[str, ...]:
    return _list_versions(coach_prompt_search_roots(), marker="semantic_extract.yaml", fallback=fallback)


def _list_versions(roots: list[Path], *, marker: str, fallback: str) -> tuple[str, ...]:
    versions: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if path.is_dir() and (path / marker).is_file():
                versions.add(path.name)
    if not versions:
        return (fallback,)
    from llm_werewolf.strategy.registry.role_version_manifest import version_sort_key

    return tuple(sorted(versions, key=version_sort_key))


def resolve_latest_replay_version(*, fallback: str = "v1") -> str:
    from llm_werewolf.strategy.registry.role_version_manifest import pick_latest_version

    return pick_latest_version(list_replay_versions(fallback=fallback), fallback=fallback)


def resolve_latest_coach_version(*, fallback: str = "v1") -> str:
    from llm_werewolf.strategy.registry.role_version_manifest import pick_latest_version

    return pick_latest_version(list_coach_versions(fallback=fallback), fallback=fallback)


@lru_cache(maxsize=16)
def resolve_replay_prompt_dir(version: str) -> Path:
    for root in replay_prompt_search_roots():
        candidate = root / version
        if (candidate / "system.md").is_file():
            return candidate
    msg = f"Unknown replay prompt package '{version}'. Searched: {replay_prompt_search_roots()}"
    raise FileNotFoundError(msg)


@lru_cache(maxsize=16)
def resolve_coach_prompt_dir(version: str) -> Path:
    for root in coach_prompt_search_roots():
        candidate = root / version
        if (candidate / "semantic_extract.yaml").is_file():
            return candidate
    msg = f"Unknown coach prompt package '{version}'. Searched: {coach_prompt_search_roots()}"
    raise FileNotFoundError(msg)


@dataclass(frozen=True)
class ReplayPromptBundle:
    version: str
    system_prompt: str
    user_template: dict[str, Any]
    dimensions: dict[str, str]
    json_reminder: str
    plain_json_fallback: str


@dataclass(frozen=True)
class CoachSemanticExtractBundle:
    version: str
    intro: tuple[str, ...]
    result_win: str
    result_loss: str
    episode_line: str


@lru_cache(maxsize=8)
def load_replay_prompt_bundle(version: str | None = None) -> ReplayPromptBundle:
    resolved = version or resolve_latest_replay_version()
    prompt_dir = resolve_replay_prompt_dir(resolved)
    system_prompt = (prompt_dir / "system.md").read_text(encoding="utf-8").strip()
    user_data = yaml.safe_load((prompt_dir / "user_template.yaml").read_text(encoding="utf-8")) or {}
    dim_data = yaml.safe_load((prompt_dir / "dimensions.yaml").read_text(encoding="utf-8")) or {}
    dimensions = dim_data.get("dimensions") if isinstance(dim_data, dict) else None
    if not isinstance(user_data, dict) or not isinstance(dimensions, dict):
        msg = f"Invalid replay prompt package: {prompt_dir}"
        raise ValueError(msg)
    return ReplayPromptBundle(
        version=resolved,
        system_prompt=system_prompt,
        user_template=user_data,
        dimensions={str(k): str(v) for k, v in dimensions.items()},
        json_reminder=str(user_data.get("json_reminder", "")),
        plain_json_fallback=str(user_data.get("plain_json_fallback", "")).strip(),
    )


@lru_cache(maxsize=8)
def load_coach_semantic_extract_bundle(version: str | None = None) -> CoachSemanticExtractBundle:
    resolved = version or resolve_latest_coach_version()
    prompt_dir = resolve_coach_prompt_dir(resolved)
    data = yaml.safe_load((prompt_dir / "semantic_extract.yaml").read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        msg = f"Invalid coach prompt package: {prompt_dir}"
        raise ValueError(msg)
    intro = data.get("intro") or []
    if not isinstance(intro, list):
        msg = f"Invalid coach intro section: {prompt_dir}"
        raise ValueError(msg)
    return CoachSemanticExtractBundle(
        version=resolved,
        intro=tuple(str(line) for line in intro),
        result_win=str(data.get("result_win", "本局结果：胜利")),
        result_loss=str(data.get("result_loss", "本局结果：失败")),
        episode_line=str(data.get("episode_line", "第{round_number}轮：{messages}")),
    )
