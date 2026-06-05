"""Deterministic role shuffle via role_shuffle_seed."""

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.config import GameConfig, create_game_config_from_player_count
from llm_werewolf.game_runtime.roles.registry import create_roles
from llm_werewolf.interface.cli.runtime.bootstrap import create_information_hub


def _role_map(engine: GameEngine) -> dict[str, str]:
    assert engine.game_state is not None
    return {p.player_id: p.get_role_name() for p in engine.game_state.players}


def test_setup_game_role_shuffle_seed_is_deterministic() -> None:
    config = create_game_config_from_player_count(6).model_copy(update={"role_shuffle_seed": 42})
    roles = create_roles(role_names=config.role_names)
    players = [DemoAgent(name=f"P{i}", model="demo") for i in range(1, 7)]

    engine_a = GameEngine(config, information_hub=create_information_hub(), silent_events=True)
    engine_a.setup_game(players=players, roles=roles)

    engine_b = GameEngine(config, information_hub=create_information_hub(), silent_events=True)
    engine_b.setup_game(players=players, roles=roles)

    assert _role_map(engine_a) == _role_map(engine_b)

    engine_c = GameEngine(
        GameConfig(
            num_players=6,
            role_names=config.role_names,
            role_shuffle_seed=99,
        ),
        information_hub=create_information_hub(),
        silent_events=True,
    )
    engine_c.setup_game(players=players, roles=roles)
    assert _role_map(engine_c) != _role_map(engine_a)
