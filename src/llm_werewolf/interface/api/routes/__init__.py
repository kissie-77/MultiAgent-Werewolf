"""HTTP route modules."""

from llm_werewolf.interface.api.routes.legacy import (
    content_router,
    game_router,
    home_router,
    models_router,
    replay_router,
    roles_router,
    runs_router,
)
from llm_werewolf.interface.api.routes.actions import router as actions_router
from llm_werewolf.interface.api.routes.pages import router as pages_router

__all__ = [
    "actions_router",
    "content_router",
    "game_router",
    "home_router",
    "models_router",
    "pages_router",
    "replay_router",
    "roles_router",
    "runs_router",
]
