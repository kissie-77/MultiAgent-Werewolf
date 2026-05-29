from types import SimpleNamespace
from unittest.mock import MagicMock

from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.types import Camp
from llm_werewolf.game_runtime.config import create_game_config_from_player_count
from llm_werewolf.agent_team.agents.base import BaseAgent
from llm_werewolf.game_runtime.roles.registry import create_roles


class MemoryAwareDemoAgent(BaseAgent):
    model: str = "demo"
    memory_manager: object | None = None

    async def get_response(self, message: str) -> str:
        del message
        return "[[0]]"


def test_check_victory_triggers_memory_game_end_hooks() -> None:
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config)
    players = [
        MemoryAwareDemoAgent(name=f"Player{i}", model="demo") for i in range(config.num_players)
    ]
    roles = create_roles(role_names=config.role_names)
    engine.setup_game(players=players, roles=roles)

    assert engine.game_state is not None

    winners: list[str] = []
    losers: list[str] = []
    for player in engine.game_state.players:
        if player.get_camp() == Camp.WEREWOLF:
            player.kill()
            losers.append(player.player_id)
        else:
            winners.append(player.player_id)
        if player.agent:
            player.agent.memory_manager = SimpleNamespace(on_game_end=MagicMock())

    assert engine.check_victory()

    for player in engine.game_state.players:
        if not player.agent:
            continue
        expected = player.player_id in winners
        player.agent.memory_manager.on_game_end.assert_called_once_with(expected)
