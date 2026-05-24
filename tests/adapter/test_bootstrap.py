"""AgentScope 游戏引导辅助函数的测试。"""

from unittest.mock import MagicMock, patch

from llm_werewolf.adapter.bootstrap import (
    create_players_from_config,
    wire_agentscope_after_setup,
)
from llm_werewolf.agent_team.base import DemoAgent
from llm_werewolf.core.config import PlayerConfig, PlayersConfig


def _six_demo_players() -> list[PlayerConfig]:
    return [PlayerConfig(name=f"P{i}", model="demo") for i in range(1, 7)]


def test_create_players_demo_never_agentscope_class() -> None:
    cfg = PlayersConfig(language="zh-CN", agent_backend="agentscope", players=_six_demo_players())
    players = create_players_from_config(cfg)

    assert all(isinstance(p, DemoAgent) for p in players)


def test_wire_agentscope_calls_bind_after_setup() -> None:
    cfg = PlayersConfig(language="zh-CN", players=_six_demo_players())
    engine = MagicMock()
    engine.game_state = MagicMock()

    with patch("llm_werewolf.adapter.bootstrap.bind_agentscope_roles") as mock_bind:
        wire_agentscope_after_setup(engine, cfg)
        mock_bind.assert_called_once_with(engine.game_state, default_plan="default")


def test_wire_skips_openai_backend() -> None:
    cfg = PlayersConfig(
        language="zh-CN",
        agent_backend="openai",
        players=_six_demo_players(),
    )
    engine = MagicMock()
    engine.game_state = MagicMock()

    with patch("llm_werewolf.adapter.bootstrap.bind_agentscope_roles") as mock_bind:
        wire_agentscope_after_setup(engine, cfg)
        mock_bind.assert_not_called()
