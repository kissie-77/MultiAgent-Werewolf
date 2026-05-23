"""决策提示使用 Hub 记忆；事件日志排除对话类型。"""

import pytest

from llm_werewolf.core import GameEngine
from llm_werewolf.core.agent import DemoAgent
from llm_werewolf.core.config import create_game_config_from_player_count
from llm_werewolf.core.event_visibility import HUB_DIALOGUE_EVENT_TYPES
from llm_werewolf.core.roles.registry import create_roles
from llm_werewolf.core.types import EventType


def test_hub_dialogue_event_types_cover_speech_channels():
    assert EventType.PLAYER_SPEECH in HUB_DIALOGUE_EVENT_TYPES
    assert EventType.PLAYER_DISCUSSION in HUB_DIALOGUE_EVENT_TYPES
    assert EventType.SHERIFF_CANDIDATE_SPEECH in HUB_DIALOGUE_EVENT_TYPES
    assert EventType.PLAYER_ELIMINATED not in HUB_DIALOGUE_EVENT_TYPES


@pytest.fixture
def engine_with_speech_event():
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config)
    players = [DemoAgent(name=f"Player{i}", model="demo") for i in range(config.num_players)]
    roles = create_roles(role_names=config.role_names)
    engine.setup_game(players=players, roles=roles)
    player = engine.game_state.players[0]
    engine._log_event(
        EventType.PLAYER_SPEECH,
        "Alice said secret accusation",
        data={
            "player_id": player.player_id,
            "player_name": player.name,
            "speech": "secret accusation",
        },
    )
    return engine, player


def test_for_agent_decision_excludes_dialogue_from_observation(engine_with_speech_event):
    """发言事件保留在日志中，但不进入 LLM 决策观察文本。"""
    engine, player = engine_with_speech_event
    full = engine.build_player_observation(player, for_agent_decision=False)
    decision = engine.build_player_observation(player, for_agent_decision=True)
    assert "secret accusation" in full
    assert "secret accusation" not in decision
