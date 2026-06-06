"""User-facing interface layer for LLM Werewolf.

Layout
------
cli/          Command-line entrypoints (game, TUI, eval, vote-swing)
  runtime/    Shared CLI wiring (bootstrap, modes, seat overrides)
api/          HTTP API for the web frontend
  routes/     pages.py (primary) + legacy.py (compat REST)
  models/     Pydantic request/response models
  services/   Business logic and page payload builders
"""
