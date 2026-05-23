"""Tests for PlayersConfig agent backend selection."""

from llm_werewolf.core.config import PlayerConfig, PlayersConfig


def _six_demo_players() -> list[PlayerConfig]:
    return [PlayerConfig(name=f"P{i}", model="demo") for i in range(1, 7)]


def test_use_agentscope_backend_default() -> None:
    cfg = PlayersConfig(language="zh-CN", players=_six_demo_players())
    assert cfg.use_agentscope_backend is True


def test_use_agentscope_backend_openai_legacy() -> None:
    for backend in ("openai", "OPENAI", "legacy", "llm"):
        cfg = PlayersConfig(
            language="zh-CN",
            agent_backend=backend,
            players=_six_demo_players(),
        )
        assert cfg.use_agentscope_backend is False
