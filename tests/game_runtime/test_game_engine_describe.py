"""GameEngine debugging helpers."""

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.config import create_game_config_from_player_count
from llm_werewolf.game_runtime.roles.registry import create_roles
from llm_werewolf.interface.cli.runtime.bootstrap import create_information_hub


def test_game_engine_describe_before_init() -> None:
    engine = GameEngine()
    assert "uninitialized" in engine.describe()
    assert repr(engine) == engine.describe()


def test_game_engine_describe_after_setup() -> None:
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config, information_hub=create_information_hub(), silent_events=True)
    players = [DemoAgent(name=f"Player{i}", model="demo") for i in range(config.num_players)]
    roles = create_roles(role_names=config.role_names)
    engine.setup_game(players=players, roles=roles)

    text = engine.describe()
    assert "phase=setup" in text
    assert "alive=6/6" in text
