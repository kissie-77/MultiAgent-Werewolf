"""版本化 Prompt 变量注册表：变量 id → 外置文件正文。"""

from __future__ import annotations

from typing import Any
from pathlib import Path
from functools import lru_cache
from dataclasses import dataclass

import yaml

_PROMPTS_ROOT = Path(__file__).resolve().parent / "prompts"

ROLE_KEY_TO_VARIABLE: dict[str, str] = {
    "villager": "v2.role.villager",
    "prophet": "v2.role.prophet",
    "witch": "v2.role.witch",
    "wolf": "v2.role.wolf",
    "wolf_king": "v2.role.wolf_king",
    "guard": "v2.role.guard",
    "hunter": "v2.role.hunter",
}


@dataclass(frozen=True)
class VariableSpec:
    """variables.yaml 中单个变量的元数据。"""

    variable_id: str
    kind: str
    file: str
    format_keys: tuple[str, ...] = ()


class PromptRegistry:
    """加载指定版本目录下的 manifest + variables，并按 id 读取文案。"""

    def __init__(self, version_dir: Path) -> None:
        self.version_dir = version_dir
        self.version = self._read_manifest_version(version_dir)
        self._specs = self._load_variable_specs(version_dir)
        self._text_cache: dict[str, str] = {}
        self._role_cache: dict[str, dict[str, str]] = {}

    @staticmethod
    def _read_manifest_version(version_dir: Path) -> str:
        manifest = version_dir / "manifest.yaml"
        if not manifest.is_file():
            msg = f"Missing manifest: {manifest}"
            raise FileNotFoundError(msg)
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        return str(data.get("version", version_dir.name))

    @staticmethod
    def _load_variable_specs(version_dir: Path) -> dict[str, VariableSpec]:
        variables_path = version_dir / "variables.yaml"
        if not variables_path.is_file():
            msg = f"Missing variables: {variables_path}"
            raise FileNotFoundError(msg)
        raw = yaml.safe_load(variables_path.read_text(encoding="utf-8")) or {}
        specs: dict[str, VariableSpec] = {}
        for variable_id, meta in (raw.get("variables") or {}).items():
            if not isinstance(meta, dict):
                continue
            specs[str(variable_id)] = VariableSpec(
                variable_id=str(variable_id),
                kind=str(meta.get("kind", "text")),
                file=str(meta["file"]),
                format_keys=tuple(meta.get("format_keys") or ()),
            )
        return specs

    def list_variables(self) -> list[str]:
        return sorted(self._specs.keys())

    def variable_path(self, variable_id: str) -> Path:
        spec = self._require_spec(variable_id)
        return self.version_dir / spec.file

    def get_text(self, variable_id: str) -> str:
        if variable_id in self._text_cache:
            return self._text_cache[variable_id]
        spec = self._require_spec(variable_id)
        path = self.version_dir / spec.file
        if not path.is_file():
            msg = f"Prompt file not found for {variable_id}: {path}"
            raise FileNotFoundError(msg)
        text = path.read_text(encoding="utf-8").strip()
        self._text_cache[variable_id] = text
        return text

    def get_role_card(self, variable_id: str) -> dict[str, str]:
        if variable_id in self._role_cache:
            return dict(self._role_cache[variable_id])
        spec = self._require_spec(variable_id)
        if spec.kind != "role_card":
            msg = f"Variable {variable_id} is not a role_card (kind={spec.kind})"
            raise ValueError(msg)
        path = self.version_dir / spec.file
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        card = {
            "role_name": str(data.get("role_name", "")),
            "role_instruction": str(data.get("role_instruction", "")).strip(),
            "suggestion": str(data.get("suggestion", "")).strip(),
        }
        self._role_cache[variable_id] = card
        return dict(card)

    def resolve(self, variable_id: str, **slots: Any) -> str:
        template = self.get_text(variable_id)
        return template.format(**slots)

    def role_card_by_prompt_key(
        self, prompt_role_key: str, *, version: str | None = None
    ) -> dict[str, str]:
        prefix = version or self.version
        var_id = ROLE_KEY_TO_VARIABLE.get(prompt_role_key)
        if var_id is None:
            var_id = f"{prefix}.role.villager"
        elif not var_id.startswith(f"{prefix}."):
            var_id = f"{prefix}.role.{prompt_role_key}"
        return self.get_role_card(var_id)

    def agent_base_template(self, *, version: str | None = None) -> str:
        prefix = version or self.version
        return self.get_text(f"{prefix}.agent.base")

    def _require_spec(self, variable_id: str) -> VariableSpec:
        spec = self._specs.get(variable_id)
        if spec is None:
            msg = f"Unknown prompt variable: {variable_id}"
            raise KeyError(msg)
        return spec


@lru_cache(maxsize=4)
def get_registry(version: str = "v2") -> PromptRegistry:
    version_dir = _PROMPTS_ROOT / version
    return PromptRegistry(version_dir)


def role_prompt_key_to_variable(prompt_role_key: str, version: str = "v2") -> str:
    return ROLE_KEY_TO_VARIABLE.get(prompt_role_key, f"{version}.role.villager")
