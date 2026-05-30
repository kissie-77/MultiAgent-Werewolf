"""Backward-compatible shim for RuntimeMemoryManager."""

from llm_werewolf.agent_team.memory.runtime_memory_manager import MemoryManager, RuntimeMemoryManager

__all__ = ["MemoryManager", "RuntimeMemoryManager"]
