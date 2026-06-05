"""PlayersConfig 智能体后端选择的测试。"""

from pathlib import Path

import pytest

from llm_werewolf.game_runtime.config import PlanAssignmentConfig, PlayerConfig, PlayersConfig
from llm_werewolf.game_runtime.support.utils import load_config


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


def test_kimi_config_enables_parallel_vote_intentions() -> None:
    cfg = load_config(Path("configs/llm-12p-kimi.yaml"))

    assert cfg.vote_intention_concurrency > 1


def test_plan_assignment_defaults_to_disabled() -> None:
    cfg = PlayersConfig(language="zh-CN", players=_six_demo_players())

    assert cfg.plan_assignment.enabled is False
    assert cfg.plan_assignment.mode == "role_cycle"


def test_plan_assignment_accepts_random_seed_and_role_plans() -> None:
    cfg = PlayersConfig(
        language="zh-CN",
        plan_assignment=PlanAssignmentConfig(
            enabled=True,
            mode="role_random",
            seed=7,
            role_plans={"wolf": ["wolf_aggressive", "wolf_skeptical"]},
        ),
        players=_six_demo_players(),
    )

    assert cfg.plan_assignment.enabled is True
    assert cfg.plan_assignment.mode == "role_random"
    assert cfg.plan_assignment.role_plans["wolf"] == ["wolf_aggressive", "wolf_skeptical"]
