"""Architecture import boundary checks for the six project areas."""

from __future__ import annotations

import ast
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "llm_werewolf"

FORBIDDEN_IMPORTS: dict[str, set[str]] = {
    "game_runtime": {"agent_team", "evaluation", "interface", "ui"},
    "strategy": {"agent_team", "evaluation", "interface", "ui"},
    "agent_team": {"evaluation", "interface", "ui"},
    "ui": {"agent_team", "evaluation", "interface"},
}

KNOWN_IMPORT_DEBT: set[tuple[str, str]] = set()


def _relative_source(path: Path) -> str:
    return path.relative_to(SRC_ROOT).as_posix()


def _top_area(path: Path) -> str:
    return path.relative_to(SRC_ROOT).parts[0]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("llm_werewolf."):
                modules.add(node.module.removeprefix("llm_werewolf."))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("llm_werewolf."):
                    modules.add(alias.name.removeprefix("llm_werewolf."))
    return modules


def _is_forbidden(source_area: str, imported_module: str) -> bool:
    imported_area = imported_module.split(".", 1)[0]
    return imported_area in FORBIDDEN_IMPORTS.get(source_area, set())


def _is_known_debt(source_path: str, imported_module: str) -> bool:
    return any(
        source_path == debt_path and imported_module.startswith(debt_module)
        for debt_path, debt_module in KNOWN_IMPORT_DEBT
    )


def test_no_new_forbidden_cross_area_imports() -> None:
    violations: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        source_area = _top_area(path)
        source_path = _relative_source(path)
        for imported_module in sorted(_imported_modules(path)):
            if not _is_forbidden(source_area, imported_module):
                continue
            if _is_known_debt(source_path, imported_module):
                continue
            violations.append(f"{source_path} -> llm_werewolf.{imported_module}")

    assert not violations, "新增了禁止的跨板块依赖：\n" + "\n".join(violations)


def test_known_import_debt_still_documents_real_violations() -> None:
    existing_debt: set[tuple[str, str]] = set()
    for path in sorted(SRC_ROOT.rglob("*.py")):
        source_path = _relative_source(path)
        for imported_module in sorted(_imported_modules(path)):
            for debt_path, debt_module in KNOWN_IMPORT_DEBT:
                if source_path == debt_path and imported_module.startswith(debt_module):
                    existing_debt.add((debt_path, debt_module))

    stale_debt = KNOWN_IMPORT_DEBT - existing_debt
    assert not stale_debt, "以下历史依赖债务已不存在，请从 allowlist 删除：\n" + "\n".join(
        f"{path} -> llm_werewolf.{module}" for path, module in sorted(stale_debt)
    )
