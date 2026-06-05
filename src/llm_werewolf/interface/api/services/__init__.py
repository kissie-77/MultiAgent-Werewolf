"""API service layer."""

from llm_werewolf.interface.api.services.runs import (
    list_run_dirs,
    paginate_runs,
    get_run_detail,
    aggregate_model_usage,
)
from llm_werewolf.interface.api.services.config import (
    compare_models,
    get_model_detail,
    list_models_page,
)
from llm_werewolf.interface.api.services.replay import get_replay_page, get_share_replay_page
from llm_werewolf.interface.api.services.catalog import get_role_detail, list_roles_page
from llm_werewolf.interface.api.services.content import (
    get_about_page,
    get_home_content,
    default_nav_links,
    get_features_page,
    get_strategy_page,
    get_how_to_play_page,
    get_night_phase_page,
)

__all__ = [
    "aggregate_model_usage",
    "compare_models",
    "default_nav_links",
    "get_about_page",
    "get_features_page",
    "get_home_content",
    "get_how_to_play_page",
    "get_model_detail",
    "get_night_phase_page",
    "get_replay_page",
    "get_role_detail",
    "get_run_detail",
    "get_share_replay_page",
    "get_strategy_page",
    "list_models_page",
    "list_roles_page",
    "list_run_dirs",
    "paginate_runs",
]
