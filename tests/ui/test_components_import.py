"""UI components package import tests."""

from __future__ import annotations

import importlib


def test_components_package_imports_without_panels() -> None:
    components = importlib.import_module("llm_werewolf.ui.components")

    assert components.__all__ == []
