"""finalize_run artifact persistence and pipeline wrapper."""

from __future__ import annotations

import types
import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.interface.fixtures import write_sample_run


def _finalize_module():
    mod = importlib.import_module("llm_werewolf.interface.cli.runtime.finalize_run")
    assert isinstance(mod, types.ModuleType), f"expected module, got {type(mod)!r}"
    return mod


def test_persist_run_artifacts_writes_events_and_intentions(tmp_path) -> None:
    mod = _finalize_module()
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    engine = MagicMock()
    engine.event_logger.events = [MagicMock()]
    tracker = MagicMock()
    engine.game_state.vote_intention_tracker = tracker

    original = mod.event_to_dict
    mod.event_to_dict = lambda _event: {"event_type": "game_started"}
    try:
        mod.persist_run_artifacts(engine, run_dir)
    finally:
        mod.event_to_dict = original

    assert (run_dir / "events.jsonl").is_file()
    tracker.save_jsonl.assert_called_once()


def test_persist_run_artifacts_writes_beliefs(tmp_path) -> None:
    mod = _finalize_module()
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    from llm_werewolf.strategy.belief.state import BeliefLog, BeliefSnapshotRecord
    from llm_werewolf.strategy.wolf.camp_mind import init_wolf_camp_mind, merge_wolf_camp_delta
    from llm_werewolf.strategy.contracts.decisions import GodRoleDelta, WolfCampDelta

    belief_log = BeliefLog()
    belief_log.append(
        BeliefSnapshotRecord(
            round_number=1,
            phase="Day",
            anchor="initial",
            observer_id="player_1",
            observer_seat=1,
            speaker_id="",
            vote_seat=0,
            vote_reason=None,
            first_order=[],
            second_order=[],
        )
    )
    wolf_model = init_wolf_camp_mind([])
    merge_wolf_camp_delta(
        wolf_model,
        WolfCampDelta(god_role_intel=[GodRoleDelta(target_seat=2, delta={"Seer": 1.0})]),
        contributor_seat=3,
        round_number=1,
    )

    engine = MagicMock()
    engine.event_logger.events = []
    engine.game_state.vote_intention_tracker = None
    engine.game_state.belief_log = belief_log
    engine.game_state.wolf_camp_mind = wolf_model

    mod.persist_run_artifacts(engine, run_dir)
    assert (run_dir / "beliefs.jsonl").is_file()


def test_persist_run_artifacts_skips_existing_files(tmp_path) -> None:
    mod = _finalize_module()
    run_dir = tmp_path / "run"
    write_sample_run(run_dir)
    engine = MagicMock()
    engine.event_logger.events = [MagicMock()]

    mod.persist_run_artifacts(engine, run_dir)
    lines = (run_dir / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 8


@pytest.mark.asyncio
async def test_finalize_run_delegates_to_post_game(tmp_path) -> None:
    mod = _finalize_module()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    engine = MagicMock()
    engine.event_logger.events = []
    engine.game_state = None

    mock_result = MagicMock(error=None, stage_errors=None)
    mock_pipeline = AsyncMock(return_value=mock_result)
    mock_evolve = MagicMock()
    original = mod.run_post_game_pipeline
    original_evolve = mod.evolve_prompt_from_run
    mod.run_post_game_pipeline = mock_pipeline
    mod.evolve_prompt_from_run = mock_evolve
    try:
        result = await mod.finalize_run(engine, run_dir, game_result_text="done")
    finally:
        mod.run_post_game_pipeline = original
        mod.evolve_prompt_from_run = original_evolve

    assert result is mock_result
    mock_pipeline.assert_awaited_once()
    mock_evolve.assert_called_once()
    assert mock_evolve.call_args.kwargs["base_prompt_version"] == "latest"

@pytest.mark.asyncio
async def test_finalize_run_logs_pipeline_error(tmp_path) -> None:
    mod = _finalize_module()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    engine = MagicMock()
    engine.event_logger.events = []
    engine.game_state = None

    mock_result = MagicMock(error="boom", stage_errors=None)
    original = mod.run_post_game_pipeline
    original_evolve = mod.evolve_prompt_from_run
    mod.run_post_game_pipeline = AsyncMock(return_value=mock_result)
    mod.evolve_prompt_from_run = MagicMock()
    try:
        await mod.finalize_run(engine, run_dir)
    finally:
        mod.run_post_game_pipeline = original
        mod.evolve_prompt_from_run = original_evolve


@pytest.mark.asyncio
async def test_finalize_run_logs_stage_errors(tmp_path) -> None:
    mod = _finalize_module()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    engine = MagicMock()
    engine.event_logger.events = []
    engine.game_state = None

    mock_result = MagicMock(error=None, stage_errors=["stage1"])
    original = mod.run_post_game_pipeline
    original_evolve = mod.evolve_prompt_from_run
    mod.run_post_game_pipeline = AsyncMock(return_value=mock_result)
    mod.evolve_prompt_from_run = MagicMock()
    try:
        await mod.finalize_run(engine, run_dir)
    finally:
        mod.run_post_game_pipeline = original
        mod.evolve_prompt_from_run = original_evolve
