"""PlayersConfig 智能体后端选择的测试。"""

import pytest

from llm_werewolf.game_runtime.config import PlayerConfig, PlayersConfig


def _six_demo_players() -> list[PlayerConfig]:
    return [PlayerConfig(name=f"P{i}", model="demo") for i in range(1, 7)]


def test_use_agentscope_backend_default() -> None:
    cfg = PlayersConfig(language="zh-CN", players=_six_demo_players())
    assert cfg.use_agentscope_backend is True


def test_rejects_removed_single_call_llm_backends() -> None:
    for backend in ("openai", "OPENAI", "legacy", "llm"):
        with pytest.raises(ValueError, match="agent_backend only supports 'agentscope'"):
            PlayersConfig(
                language="zh-CN",
                agent_backend=backend,
                players=_six_demo_players(),
            )


def test_accepts_agentscope_backend_value() -> None:
    cfg = PlayersConfig(
        language="zh-CN",
        agent_backend="agentscope",
        players=_six_demo_players(),
    )
    assert cfg.use_agentscope_backend is True
