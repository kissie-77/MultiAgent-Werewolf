"""Spec §9 parity: live serialize_game_state /state == disk build_view /state mid-game."""

from __future__ import annotations

import json
import random

import pytest

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.agent_team.communication.information_hub import InformationHub
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.config import create_game_config_from_player_count
from llm_werewolf.game_runtime.roles.registry import create_roles
from llm_werewolf.game_runtime.state.serialization import serialize_game_state
from llm_werewolf.game_runtime.types import GamePhase
from llm_werewolf.interface.api.services.state import (
    build_state_from_snapshot,
    build_state_from_view,
)
from llm_werewolf.interface.api.services.view import build_view
from llm_werewolf.evaluation.post_game.event_adapter import event_to_dict


def _build_engine(seed: int) -> GameEngine:
    random.seed(seed)
    config = create_game_config_from_player_count(6)
    # main 给 setup_game 加了 information_hub fail-fast；注入与生产装配一致。
    engine = GameEngine(config, information_hub=InformationHub())
    engine.on_event = lambda _event: None
    players = [DemoAgent(name=f"P{i}", model="demo", seed=seed) for i in range(config.num_players)]
    roles = create_roles(role_names=config.role_names)
    engine.setup_game(players=players, roles=roles)
    return engine


@pytest.mark.asyncio
async def test_live_state_matches_disk_state_midgame(tmp_path) -> None:
    engine = _build_engine(20260603)
    # Advance deterministically to DAY_DISCUSSION (round 1). With sheriff disabled the
    # step sequence is SETUP->NIGHT, NIGHT->DAY_DISCUSSION, so exactly 2 steps land the
    # phase pointer at DAY_DISCUSSION with night deaths populated. The step that runs
    # DAY_DISCUSSION work (which logs the day_discussion PHASE_CHANGED + daybreak events)
    # only fires on the NEXT step, so we run run_day_phase() directly to materialize those
    # day events WITHOUT advancing to DAY_VOTING — keeping the phase at DAY_DISCUSSION and
    # votes empty on BOTH sides. (Deviation from plan's "2 steps": the phase pointer
    # advances at the step boundary before the next phase logs anything, so the disk view —
    # which reads phase off the last logged event — would otherwise lag at 'night'.)
    for _ in range(2):
        assert not engine.is_over()
        await engine.step()
    assert engine.game_state.phase == GamePhase.DAY_DISCUSSION
    await engine.run_day_phase()
    assert engine.game_state.phase == GamePhase.DAY_DISCUSSION
    assert engine.game_state.votes == {}

    # Persist roster.json + events.jsonl exactly as the API disk sink would.
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    roster = {"players": [
        {"seat": int(p.player_id.rsplit("_", 1)[-1]), "player_id": p.player_id,
         "name": p.name, "role": p.get_role_name(), "camp": p.get_camp().value,
         "model": getattr(p, "ai_model", None)}
        for p in engine.game_state.players
    ]}
    (run_dir / "roster.json").write_text(json.dumps(roster, ensure_ascii=False), encoding="utf-8")
    rows = [event_to_dict(ev) for ev in engine.get_events()]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    # Live /state from the engine snapshot.
    snapshot = serialize_game_state(engine.game_state)
    camps = {p.player_id: p.get_camp().value for p in engine.game_state.players}
    live = build_state_from_snapshot(
        snapshot, status="running", error=None, cursor=len(rows), camps=camps)

    # Disk /state from the reconstructed view.
    view = build_view(run_dir, since=0, status="running", error=None)
    disk = build_state_from_view(view)

    # Field-for-field parity on everything build_view reconstructs.
    assert live.phase == disk.phase
    assert live.round == disk.round
    assert live.winner == disk.winner
    assert live.sheriff_seat == disk.sheriff_seat
    assert sorted(p.seat for p in live.players if p.is_alive) == \
        sorted(p.seat for p in disk.players if p.is_alive)
    assert sorted(p.seat for p in live.players if not p.is_alive) == \
        sorted(p.seat for p in disk.players if not p.is_alive)
    assert live.alive_count == disk.alive_count
    assert live.dead_count == disk.dead_count
    # votes: the disk fallback (view.py _build_snapshot) never reconstructs a vote tally,
    # so disk tally is always {}. We stopped at a pre-voting phase where the live tally is
    # also empty, making this parity meaningful rather than accidental.
    assert disk.votes.tally == {}
    assert live.votes.tally == {}
    # widened role_data (Hunter/Seer) is present on the live snapshot players
    for p in snapshot.players:
        if p.role_name in ("Hunter", "Seer"):
            assert set(p.role_data) >= {"ability_uses", "disabled"}
