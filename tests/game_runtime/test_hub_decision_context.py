"""决策提示使用 Hub 记忆；事件日志排除对话类型。"""

import pytest

from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.types import EventType
from llm_werewolf.game_runtime.config import create_game_config_from_player_count
from llm_werewolf.interface.bootstrap import create_information_hub
from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.agent_team.agents.human_interactive_agent import HumanInteractiveAgent
from llm_werewolf.game_runtime.prompts.actions import EngineContexts
from llm_werewolf.game_runtime.roles.registry import create_roles
from llm_werewolf.game_runtime.events.event_visibility import HUB_DIALOGUE_EVENT_TYPES


class _MemoryContext:
    def __init__(self) -> None:
        self.include_belief: bool | None = None

    def get_context_for_decision(self, *, include_belief: bool = True) -> str:
        self.include_belief = include_belief
        return "【内心信念】\n- 【当前信念矩阵 · 仅自己可见】测试信念"


def test_hub_dialogue_event_types_cover_speech_channels() -> None:
    assert EventType.PLAYER_SPEECH in HUB_DIALOGUE_EVENT_TYPES
    assert EventType.PLAYER_DISCUSSION in HUB_DIALOGUE_EVENT_TYPES
    assert EventType.SHERIFF_CANDIDATE_SPEECH in HUB_DIALOGUE_EVENT_TYPES
    assert EventType.PLAYER_ELIMINATED not in HUB_DIALOGUE_EVENT_TYPES


def test_wolf_roundtable_memory_notice_uses_wolf_chat_terms() -> None:
    notice = EngineContexts.hub_roundtable_memory_notice("wolf_team")

    assert "狼队夜聊" in notice
    assert "前面已发言队友" in notice
    assert "公开发言由系统注入" not in notice


@pytest.fixture
def engine_with_speech_event():
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config, information_hub=create_information_hub())
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


def test_for_agent_decision_excludes_dialogue_from_observation(engine_with_speech_event) -> None:
    """发言事件保留在日志中，但不进入 LLM 决策观察文本。"""
    engine, player = engine_with_speech_event
    full = engine.build_player_observation(player, for_agent_decision=False)
    decision = engine.build_player_observation(player, for_agent_decision=True)
    assert "secret accusation" in full
    assert "secret accusation" not in decision


def test_observation_does_not_expose_player_model_or_backend(engine_with_speech_event) -> None:
    """玩家可见上下文只包含游戏内信息，不暴露真人/模型/后端字段。"""
    engine, player = engine_with_speech_event
    player.ai_model = "human"
    engine.game_state.players[1].ai_model = "demo"

    text = engine.build_player_observation(player, for_agent_decision=True)
    lowered = text.lower()

    assert "ai_model" not in lowered
    assert "model" not in lowered
    assert "backend" not in lowered
    assert "human" not in lowered
    assert "demo" not in lowered


def test_human_discussion_context_excludes_belief_tracking_blocks() -> None:
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config, information_hub=create_information_hub())
    players = [HumanInteractiveAgent(name="玩家1", model="human")]
    players.extend(
        DemoAgent(name=f"Player{i}", model="demo") for i in range(2, config.num_players + 1)
    )
    roles = create_roles(role_names=config.role_names)
    engine.setup_game(players=players, roles=roles)

    assert engine.game_state is not None
    context = engine._build_discussion_context(engine.game_state.players[0])

    assert "当前信念矩阵" not in context
    assert "内心信念" not in context
    assert "信念/意向更新规则" not in context


def test_agent_discussion_context_includes_belief_from_working_memory() -> None:
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config, information_hub=create_information_hub())
    players = [DemoAgent(name=f"Player{i}", model="demo") for i in range(config.num_players)]
    roles = create_roles(role_names=config.role_names)
    engine.setup_game(players=players, roles=roles)

    assert engine.game_state is not None
    memory = _MemoryContext()
    engine.game_state.players[0].agent.memory_manager = memory
    context = engine._build_discussion_context(engine.game_state.players[0])

    assert memory.include_belief is True
    assert "当前信念矩阵" in context
    assert "内心信念" in context


def test_discussion_context_includes_current_role_pool_boundary() -> None:
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config, information_hub=create_information_hub())
    players = [DemoAgent(name=f"Player{i}", model="demo") for i in range(config.num_players)]
    roles = create_roles(role_names=config.role_names)
    engine.setup_game(players=players, roles=roles)

    assert engine.game_state is not None
    context = engine._build_discussion_context(engine.game_state.players[0])

    assert "【本局角色池】" in context
    assert "Werewolf x2" in context
    assert "Villager x2" in context
    assert "Guard x" not in context
    assert "【公开发言信息边界】" in context
    assert "不要无意识泄露夜间技能结果" in context
