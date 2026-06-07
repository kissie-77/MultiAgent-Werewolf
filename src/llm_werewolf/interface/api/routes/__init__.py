"""HTTP route modules."""

from llm_werewolf.interface.api.routes.pages import router as pages_router
from llm_werewolf.interface.api.routes.legacy import (
    game_router,
    home_router,
    runs_router,
    roles_router,
    models_router,
    replay_router,
    content_router,
)
from llm_werewolf.interface.api.routes.actions import router as actions_router
from llm_werewolf.interface.api.routes.settings import router as settings_router

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
    "settings_router",
]
