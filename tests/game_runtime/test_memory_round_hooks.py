from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_werewolf.agent_team.agents.base import BaseAgent
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.config import create_game_config_from_player_count
from llm_werewolf.game_runtime.roles.registry import create_roles
from llm_werewolf.game_runtime.types import GamePhase


class MemoryAwareDemoAgent(BaseAgent):
    model: str = "demo"
    memory_manager: object | None = None

    async def get_response(self, message: str) -> str:
        del message
        return "[[0]]"


@pytest.mark.asyncio
async def test_step_day_voting_triggers_memory_round_end():
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config)
    players = [MemoryAwareDemoAgent(name=f"Player{i}", model="demo") for i in range(config.num_players)]
    roles = create_roles(role_names=config.role_names)
    engine.setup_game(players=players, roles=roles)

    assert engine.game_state is not None
    engine.game_state.phase = GamePhase.DAY_VOTING
    engine.game_state.round_number = 2

    for player in engine.game_state.players:
        if player.agent:
            player.agent.memory_manager = SimpleNamespace(on_round_end=MagicMock())

    engine.run_voting_phase = AsyncMock(return_value=[])
    engine.check_victory = MagicMock(return_value=False)

    await engine.step()

    for player in engine.game_state.players:
        if player.agent:
            player.agent.memory_manager.on_round_end.assert_called_once_with(2)
