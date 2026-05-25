"""AgentScope 游戏引导辅助函数的测试。"""

from unittest.mock import MagicMock, patch

from llm_werewolf.agent_team.base import DemoAgent
from llm_werewolf.game_runtime.config import (
    PlayerConfig,
    PlayersConfig,
    PlayerRosterConfig,
    PlayerTemplateConfig,
)
from llm_werewolf.interface.bootstrap import (
    prepare_game_roster,
    create_players_from_config,
    wire_agentscope_after_setup,
)


def _six_demo_players() -> list[PlayerConfig]:
    return [PlayerConfig(name=f"P{i}", model="demo") for i in range(1, 7)]


def _deepseek_template() -> PlayerTemplateConfig:
    return PlayerTemplateConfig(
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
    )


def test_create_players_demo_never_agentscope_class() -> None:
    cfg = PlayersConfig(language="zh-CN", agent_backend="agentscope", players=_six_demo_players())
    players = create_players_from_config(cfg)

    assert all(isinstance(p, DemoAgent) for p in players)


def test_prepare_game_roster_uses_num_players_override_for_roster() -> None:
    cfg = PlayersConfig(
        language="zh-CN",
        player_roster=PlayerRosterConfig(
            count=12,
            mode="all_agent",
            llm_template=_deepseek_template(),
        ),
    )

    players, roles, game_config = prepare_game_roster(cfg, num_players=8)

    assert len(players) == 8
    assert len(roles) == 8
    assert game_config.num_players == 8


def test_prepare_game_roster_can_enable_sheriff_flow() -> None:
    cfg = PlayersConfig(
        language="zh-CN",
        player_roster=PlayerRosterConfig(
            count=12,
            mode="all_agent",
            llm_template=_deepseek_template(),
        ),
    )

    _players, _roles, game_config = prepare_game_roster(cfg, enable_sheriff=True)

    assert game_config.enable_sheriff is True


def test_wire_agentscope_calls_bind_after_setup() -> None:
    cfg = PlayersConfig(language="zh-CN", players=_six_demo_players())
    engine = MagicMock()
    engine.game_state = MagicMock()

    with patch("llm_werewolf.interface.bootstrap.bind_agentscope_roles") as mock_bind:
        wire_agentscope_after_setup(engine, cfg)
        mock_bind.assert_called_once_with(
            engine.game_state,
            default_plan="default",
            show_agent_raw=False,
        )


def test_wire_agentscope_backend_is_the_only_llm_backend() -> None:
    cfg = PlayersConfig(language="zh-CN", players=_six_demo_players())
    engine = MagicMock()
    engine.game_state = MagicMock()

    with patch("llm_werewolf.interface.bootstrap.bind_agentscope_roles") as mock_bind:
        wire_agentscope_after_setup(engine, cfg)
        mock_bind.assert_called_once_with(
            engine.game_state,
            default_plan="default",
            show_agent_raw=False,
        )


def test_wire_agentscope_passes_raw_output_flag() -> None:
    cfg = PlayersConfig(language="zh-CN", players=_six_demo_players())
    engine = MagicMock()
    engine.game_state = MagicMock()

    with patch("llm_werewolf.interface.bootstrap.bind_agentscope_roles") as mock_bind:
        wire_agentscope_after_setup(engine, cfg, show_agent_raw=True)
        mock_bind.assert_called_once_with(
            engine.game_state,
            default_plan="default",
            show_agent_raw=True,
        )
