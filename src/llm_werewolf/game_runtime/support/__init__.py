"""运行时辅助：配置加载、座位、观察、环境。

子模块可安全直接导入（如 ``support.observation``），避免经本包 __init__ 产生循环依赖。
"""

__all__ = [
    "ActionSelector",
    "ObservationBuilder",
    "PlayerObservation",
    "flatten_private_notes",
    "get_player_seat",
    "load_config",
    "load_project_dotenv",
    "resolve_player_by_seat",
]


def __getattr__(name: str):
    if name == "ActionSelector":
        from llm_werewolf.game_runtime.support.action_selector import ActionSelector

        return ActionSelector
    if name in {"ObservationBuilder", "PlayerObservation", "flatten_private_notes"}:
        from llm_werewolf.game_runtime.support import observation as obs

        return getattr(obs, name)
    if name == "load_config":
        from llm_werewolf.game_runtime.support.utils import load_config

        return load_config
    if name == "load_project_dotenv":
        from llm_werewolf.game_runtime.support.env import load_project_dotenv

        return load_project_dotenv
    if name == "get_player_seat":
        from llm_werewolf.game_runtime.support.seat import get_player_seat

        return get_player_seat
    if name == "resolve_player_by_seat":
        from llm_werewolf.game_runtime.support.seat import resolve_player_by_seat

        return resolve_player_by_seat
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
