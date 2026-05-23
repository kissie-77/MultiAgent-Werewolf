"""Backward-compatible re-export; canonical implementation in ``adapter.message``."""

from llm_werewolf.adapter.message import MessageAdapter, Msg

__all__ = ["MessageAdapter", "Msg"]
