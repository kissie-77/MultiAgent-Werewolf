from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.config import create_game_config_from_player_count
from llm_werewolf.game_runtime.roles.registry import create_roles


def test_game_engine_wires_vote_intention_concurrency_into_information_hub() -> None:
    config = create_game_config_from_player_count(6).model_copy(
        update={"vote_intention_concurrency": 6},
    )
    engine = GameEngine(config)
    players = [DemoAgent(name=f"P{i}", model="demo") for i in range(1, 7)]
    roles = create_roles(config.role_names)

    engine.setup_game(players=players, roles=roles)

    assert engine.information_hub._vote_intention_concurrency == 6
