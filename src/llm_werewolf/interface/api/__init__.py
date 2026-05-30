"""HTTP API package for the web frontend."""

from llm_werewolf.interface.api.app import create_app, entry, main

__all__ = ["create_app", "entry", "main"]
