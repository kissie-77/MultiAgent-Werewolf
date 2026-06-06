"""Per-role version resolution tests."""

from pathlib import Path

import pytest

from llm_werewolf.strategy.registry.role_version_manifest import (
    RoleVersionManifest,
    pick_latest_version,
    version_sort_key,
)


@pytest.fixture(autouse=True)
def _isolate_role_prompt_roots(monkeypatch: pytest.MonkeyPatch):
    from llm_werewolf.strategy.registry import role_prompt_registry

    monkeypatch.setattr(role_prompt_registry, "_EXTRA_ROLE_PROMPT_ROOTS", [])
    monkeypatch.delenv("LLM_WEREWOLF_ROLE_PROMPT_ROOTS", raising=False)
    role_prompt_registry.resolve_role_prompt_dir.cache_clear()
    role_prompt_registry.get_role_card.cache_clear()
    role_prompt_registry.list_prompt_versions.cache_clear()
    yield
    role_prompt_registry.resolve_role_prompt_dir.cache_clear()
    role_prompt_registry.get_role_card.cache_clear()
    role_prompt_registry.list_prompt_versions.cache_clear()


def test_version_sort_key_orders_numeric_suffixes() -> None:
    labels = ["v1", "v10", "v2", "baseline", "prompt_v3"]
    assert sorted(labels, key=version_sort_key) == ["v1", "v2", "v10", "baseline", "prompt_v3"]


def test_pick_latest_version_prefers_highest_v_label() -> None:
    assert pick_latest_version(["v1", "v3", "v2"]) == "v3"


def test_manifest_uses_latest_prompt_and_skill_when_unpinned(
    tmp_path: Path, monkeypatch
) -> None:
    from llm_werewolf.agent_team.skill_support import skill_loader
    from llm_werewolf.strategy.registry import role_prompt_registry

    prompt_root = tmp_path / "prompt_roles"
    skill_root = tmp_path / "skills"
    (prompt_root / "wolf" / "v1").mkdir(parents=True)
    (prompt_root / "wolf" / "v1" / "role.yaml").write_text("role_name: 狼人\n", encoding="utf-8")
    (prompt_root / "wolf" / "v2").mkdir(parents=True)
    (prompt_root / "wolf" / "v2" / "role.yaml").write_text("role_name: 狼人\n", encoding="utf-8")
    (skill_root / "wolf" / "v1").mkdir(parents=True)
    (skill_root / "wolf" / "v2").mkdir(parents=True)

    role_prompt_registry.register_role_prompt_search_root(prompt_root)
    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: skill_root)
    monkeypatch.setattr(
        "llm_werewolf.strategy.registry.role_version_manifest._skills_root",
        lambda: skill_root,
    )
    skill_loader.list_role_skill_files.cache_clear()

    manifest = RoleVersionManifest()
    assert manifest.prompt_version_for("wolf") == "v2"
    assert manifest.skill_version_for("wolf") == "v2"


def test_manifest_honors_explicit_role_pins(tmp_path: Path, monkeypatch) -> None:
    from llm_werewolf.agent_team.skill_support import skill_loader
    from llm_werewolf.strategy.registry import role_prompt_registry

    prompt_root = tmp_path / "prompt_roles"
    skill_root = tmp_path / "skills"
    (prompt_root / "wolf" / "v1").mkdir(parents=True)
    (prompt_root / "wolf" / "v1" / "role.yaml").write_text("role_name: 狼人\n", encoding="utf-8")
    (prompt_root / "wolf" / "v2").mkdir(parents=True)
    (prompt_root / "wolf" / "v2" / "role.yaml").write_text("role_name: 狼人\n", encoding="utf-8")
    (skill_root / "wolf" / "v1").mkdir(parents=True)
    (skill_root / "wolf" / "v2").mkdir(parents=True)

    role_prompt_registry.register_role_prompt_search_root(prompt_root)
    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: skill_root)
    monkeypatch.setattr(
        "llm_werewolf.strategy.registry.role_version_manifest._skills_root",
        lambda: skill_root,
    )
    skill_loader.list_role_skill_files.cache_clear()

    manifest = RoleVersionManifest(
        prompt_versions={"wolf": "v1"},
        skill_versions={"wolf": "v1"},
    )
    assert manifest.prompt_version_for("wolf") == "v1"
    assert manifest.skill_version_for("wolf") == "v1"
