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
            PlayersConfig(language="zh-CN", agent_backend=backend, players=_six_demo_players())


def test_accepts_agentscope_backend_value() -> None:
    cfg = PlayersConfig(language="zh-CN", agent_backend="agentscope", players=_six_demo_players())
    assert cfg.use_agentscope_backend is True


def test_prompt_version_defaults_to_latest() -> None:
    cfg = PlayersConfig(language="zh-CN", players=_six_demo_players())
    assert cfg.prompt_version == "latest"


def test_prompt_version_normalizes_case() -> None:
    cfg = PlayersConfig(language="zh-CN", prompt_version="V1", players=_six_demo_players())
    assert cfg.prompt_version == "v1"


def test_rejects_invalid_prompt_version() -> None:
    with pytest.raises(ValueError, match="prompt_version must look like"):
        PlayersConfig(language="zh-CN", prompt_version="2", players=_six_demo_players())


def test_vote_intention_concurrency_defaults_to_serial_on_players_config() -> None:
    cfg = PlayersConfig(language="zh-CN", players=_six_demo_players())

    assert cfg.vote_intention_concurrency == 1


def test_vote_intention_concurrency_accepts_parallel_value() -> None:
    cfg = PlayersConfig(
        language="zh-CN", vote_intention_concurrency=6, players=_six_demo_players()
    )

    assert cfg.vote_intention_concurrency == 6
