"""Unit tests for the /state composition service and engine wiring."""

from __future__ import annotations

from pathlib import Path

from llm_werewolf.interface.api.services.game_sessions import GameSession


def _make_session(tmp_path: Path) -> GameSession:
    return GameSession(
        run_id="r1",
        run_dir=tmp_path,
        config_path=tmp_path / "cfg.yaml",
        config_id="demo-6",
    )


def test_game_session_has_engine_field_defaulting_none(tmp_path):
    session = _make_session(tmp_path)
    assert session.engine is None


from llm_werewolf.interface.api.models.state import (
    GameStateResponse,
    LastNight,
    StatePlayer,
    StateVotes,
)


def test_state_models_defaults_match_spec():
    resp = GameStateResponse(status="running", phase="night", round=2)
    assert resp.play_state == "playing"
    assert resp.speed == 1
    assert resp.sub_phase is None
    assert resp.current_actor_seat is None
    assert resp.winner is None
    assert resp.error is None
    assert resp.last_night == LastNight()
    assert resp.votes == StateVotes()
    assert resp.players == []
    assert resp.cursor == 0


def test_state_player_status_flags_default_empty():
    p = StatePlayer(seat=1, name="P1")
    assert p.status_flags == []
    assert p.is_alive is True
    assert p.is_sheriff is False


from llm_werewolf.game_runtime.state.serialization import GameStateSnapshot, PlayerSnapshot
from llm_werewolf.interface.api.services.state import build_state_from_snapshot


def _snapshot() -> GameStateSnapshot:
    return GameStateSnapshot(
        players=[
            PlayerSnapshot(player_id="player_1", name="P1", role_name="Seer",
                           is_alive=True, statuses=["alive"], ai_model="deepseek-chat"),
            PlayerSnapshot(player_id="player_2", name="P2", role_name="Werewolf",
                           is_alive=False, statuses=["dead"], ai_model="doubao"),
            PlayerSnapshot(player_id="player_3", name="P3", role_name="Guard",
                           is_alive=True, statuses=["alive"], ai_model="demo"),
        ],
        phase="night",
        round_number=2,
        night_deaths=["player_2"],
        death_causes={"player_2": "wolf_kill"},
        witch_saved_target=None,
        witch_poison_target=None,
        guard_protected="player_3",
        votes={"player_1": "player_2", "player_3": "player_2"},
        sheriff_id="player_1",
        winner=None,
    )


def test_build_state_from_snapshot_authoritative_fields():
    state = build_state_from_snapshot(
        _snapshot(), status="running", error=None, cursor=142,
        camps={"player_1": "villager", "player_2": "werewolf", "player_3": "villager"},
    )
    assert state.status == "running"
    assert state.phase == "night"
    assert state.round == 2
    assert state.winner is None
    assert state.sheriff_seat == 1
    assert state.alive_count == 2
    assert state.dead_count == 1
    assert state.cursor == 142
    assert state.play_state == "playing"


def test_build_state_from_snapshot_last_night_and_votes():
    state = build_state_from_snapshot(
        _snapshot(), status="running", error=None, cursor=0, camps={},
    )
    assert [d.model_dump() for d in state.last_night.deaths] == [
        {"seat": 2, "cause": "wolf_kill"}
    ]
    assert state.last_night.guarded_seat == 3
    assert state.last_night.saved_seat is None
    assert state.votes.by_seat == {"1": 2, "3": 2}
    assert state.votes.tally == {"2": 2}


def test_build_state_from_snapshot_players_projection():
    state = build_state_from_snapshot(
        _snapshot(), status="running", error=None, cursor=0,
        camps={"player_1": "villager", "player_2": "werewolf"},
    )
    p1 = next(p for p in state.players if p.seat == 1)
    assert p1.role == "Seer"
    assert p1.camp == "villager"
    assert p1.is_sheriff is True
    assert p1.model == "deepseek-chat"
    assert p1.status_flags == ["alive"]
    p2 = next(p for p in state.players if p.seat == 2)
    assert p2.is_alive is False
    assert p2.is_sheriff is False


import json

from llm_werewolf.interface.api.services.state import build_state_from_view
from llm_werewolf.interface.api.services.view import build_view


def _seed_finished_run(tmp_path) -> Path:
    run_dir = tmp_path / "finished"
    run_dir.mkdir()
    (run_dir / "roster.json").write_text(json.dumps({"players": [
        {"seat": 1, "player_id": "player_1", "name": "P1", "role": "预言家",
         "camp": "villager", "model": "deepseek-chat"},
        {"seat": 2, "player_id": "player_2", "name": "P2", "role": "狼人",
         "camp": "werewolf", "model": "doubao"},
    ]}), encoding="utf-8")
    rows = [
        {"event_type": "sheriff_elected", "round_number": 1, "phase": "sheriff_election",
         "message": "1号当选警长", "data": {"player_id": "player_1"}},
        {"event_type": "player_eliminated", "round_number": 1, "phase": "day_voting",
         "message": "2号被放逐", "data": {"player_id": "player_2", "player_name": "P2"}},
        {"event_type": "game_ended", "round_number": 1, "phase": "ended",
         "message": "好人获胜", "data": {"winner_camp": "villager"}},
    ]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return run_dir


def test_build_state_from_view_disk_fallback(tmp_path):
    run_dir = _seed_finished_run(tmp_path)
    view = build_view(run_dir, since=0, status="ended", error=None)
    state = build_state_from_view(view)
    assert state.status == "ended"
    assert state.phase == "ended"
    assert state.round == 1
    assert state.winner == "villager"
    assert state.sheriff_seat == 1
    assert state.alive_count == 1
    assert state.dead_count == 1
    assert state.cursor == 3
    p1 = next(p for p in state.players if p.seat == 1)
    assert p1.role == "预言家"
    assert p1.camp == "villager"
    assert p1.is_sheriff is True
    p2 = next(p for p in state.players if p.seat == 2)
    assert p2.is_alive is False
    assert p2.status_flags == ["dead"]


from types import SimpleNamespace

from llm_werewolf.game_runtime.types import GamePhase
from llm_werewolf.interface.api.services.game_sessions import (
    GameSessionManager,
    GameSessionStatus,
)


def _live_engine():
    role = SimpleNamespace(camp=SimpleNamespace(value="villager"))
    player = SimpleNamespace(
        player_id="player_1", name="P1", ai_model="deepseek-chat",
        get_role_name=lambda: "Seer", get_camp=lambda: role.camp,
        is_alive=lambda: True, statuses=[SimpleNamespace(value="alive")],
        lover_partner_id=None, can_vote_flag=True, role=role,
    )
    game_state = SimpleNamespace(
        players=[player], phase=GamePhase.NIGHT, round_number=2,
        night_deaths=set(), day_deaths=set(), death_abilities_used=set(),
        death_causes={}, werewolf_target=None, werewolf_votes={},
        witch_save_used=False, witch_poison_used=False, witch_saved_target=None,
        witch_poison_target=None, guard_protected=None, guardian_wolf_protected=None,
        nightmare_blocked=None, seer_checked={}, graveyard_checked={}, votes={},
        raven_marked=None, wolf_beauty_charmed=None, sheriff_id=None,
        enable_sheriff=False, sheriff_election_done=False, sheriff_votes={},
        sheriff_tie_count=0, vote_tie_count=0, winner=None,
    )
    return SimpleNamespace(game_state=game_state)


def test_get_state_uses_live_engine(tmp_path):
    mgr = GameSessionManager()
    session = GameSession(
        run_id="live-1", run_dir=tmp_path, config_path=tmp_path / "c.yaml",
        config_id="demo-6", status=GameSessionStatus.RUNNING,
    )
    session.engine = _live_engine()
    mgr._sessions["live-1"] = session
    state = mgr.get_state("live-1", runs_dir=tmp_path, eval_runs_dir=tmp_path)
    assert state is not None
    assert state.status == "running"
    assert state.phase == "night"
    assert state.round == 2
    assert state.players[0].camp == "villager"


def test_get_state_disk_fallback_when_no_session(tmp_path):
    run_dir = _seed_finished_run(tmp_path)
    runs_dir = run_dir.parent
    mgr = GameSessionManager()
    state = mgr.get_state("finished", runs_dir=runs_dir, eval_runs_dir=runs_dir)
    assert state is not None
    assert state.status == "ended"
    assert state.winner == "villager"


def test_get_state_unknown_run_returns_none(tmp_path):
    mgr = GameSessionManager()
    state = mgr.get_state("nope", runs_dir=tmp_path, eval_runs_dir=tmp_path)
    assert state is None
