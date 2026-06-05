"""HTTP API package for the web frontend."""

from llm_werewolf.interface.api.app import main, entry, create_app

__all__ = ["create_app", "entry", "main"]
