"""Human-mixed game regressions."""

from __future__ import annotations

import asyncio
import random
from pathlib import Path

import pytest

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.support.utils import load_config
from llm_werewolf.interface.cli.runtime.bootstrap import (
    create_information_hub,
    prepare_game_roster,
    wire_agentscope_after_setup,
)


_SENSITIVE_ENGINE_TERMS = ("human", "demo", "backend", "model", "ai_model", "agent_backend")


@pytest.mark.asyncio
async def test_human_mixed_demo_prompts_do_not_expose_control_or_model_terms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    random.seed(20260602)
    prompts: list[str] = []
    original_get_response = DemoAgent.get_response
    original_get_structured = DemoAgent.get_structured_response

    async def record_response(self: DemoAgent, message: str) -> str:
        prompts.append(message)
        return await original_get_response(self, message)

    async def record_structured(self: DemoAgent, message: str, schema: type) -> object | None:
        prompts.append(message)
        return await original_get_structured(self, message, schema)

    monkeypatch.setattr(DemoAgent, "get_response", record_response)
    monkeypatch.setattr(DemoAgent, "get_structured_response", record_structured)
    monkeypatch.setattr("builtins.input", lambda _prompt="": (_ for _ in ()).throw(EOFError()))

    cfg = load_config(Path("configs/archive/human-6p-demo.yaml"))
    agents, roles, game_config = prepare_game_roster(cfg)
    engine = GameEngine(game_config, language=cfg.language, information_hub=create_information_hub())
    engine.on_event = lambda _event: None
    engine.setup_game(players=agents, roles=roles)
    wire_agentscope_after_setup(engine, cfg)

    await asyncio.wait_for(engine.play_game(), timeout=20)

    assert prompts
    combined = "\n".join(prompts).lower()
    for term in _SENSITIVE_ENGINE_TERMS:
        assert term not in combined

    assert engine.game_state is not None
    for player in engine.game_state.players:
        observation = engine.build_player_observation(player, for_agent_decision=True).lower()
        for term in _SENSITIVE_ENGINE_TERMS:
            assert term not in observation
