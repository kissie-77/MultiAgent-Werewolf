"""Backward-compatible CLI module shim for pyproject scripts."""

from llm_werewolf.interface.cli import entry, main

__all__ = ["entry", "main"]
