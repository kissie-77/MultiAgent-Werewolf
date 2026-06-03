"""Compose the authoritative GET /state response (spec §5.1).

Live path: from a GameStateSnapshot produced by serialize_game_state.
Disk fallback path: from a ViewResponse produced by build_view.
"""

from __future__ import annotations

from llm_werewolf.game_runtime.state.serialization import GameStateSnapshot
from llm_werewolf.interface.api.models.state import (
    GameStateResponse,
    LastNight,
    NightDeath,
    StatePlayer,
    StateVotes,
)
from llm_werewolf.interface.api.models.view import ViewResponse


def _seat_of(player_id: str | None) -> int | None:
    if not player_id:
        return None
    try:
        return int(str(player_id).rsplit("_", 1)[-1])
    except (ValueError, IndexError):
        return None


def _last_night(snapshot: GameStateSnapshot) -> LastNight:
    deaths = [
        NightDeath(seat=seat, cause=snapshot.death_causes.get(pid))
        for pid in snapshot.night_deaths
        if (seat := _seat_of(pid)) is not None
    ]
    deaths.sort(key=lambda d: d.seat)
    return LastNight(
        deaths=deaths,
        saved_seat=_seat_of(snapshot.witch_saved_target),
        guarded_seat=_seat_of(snapshot.guard_protected),
        poisoned_seat=_seat_of(snapshot.witch_poison_target),
    )


def _votes(snapshot: GameStateSnapshot) -> StateVotes:
    by_seat: dict[str, int] = {}
    tally: dict[str, int] = {}
    for voter_id, target_id in snapshot.votes.items():
        voter_seat = _seat_of(voter_id)
        target_seat = _seat_of(target_id)
        if voter_seat is None or target_seat is None:
            continue
        by_seat[str(voter_seat)] = target_seat
        tally[str(target_seat)] = tally.get(str(target_seat), 0) + 1
    return StateVotes(by_seat=by_seat, tally=tally)


def build_state_from_snapshot(
    snapshot: GameStateSnapshot,
    *,
    status: str,
    error: str | None,
    cursor: int,
    camps: dict[str, str],
    play_state: str = "playing",
    speed: int = 1,
    captured_last_night: LastNight | None = None,
) -> GameStateResponse:
    sheriff_seat = _seat_of(snapshot.sheriff_id)
    players: list[StatePlayer] = []
    alive_count = 0
    for p in snapshot.players:
        seat = _seat_of(p.player_id)
        if seat is None:
            continue
        if p.is_alive:
            alive_count += 1
        players.append(StatePlayer(
            seat=seat,
            name=p.name,
            role=p.role_name,
            camp=camps.get(p.player_id),
            is_alive=p.is_alive,
            is_sheriff=(seat == sheriff_seat),
            model=p.ai_model,
            status_flags=list(p.statuses),
        ))
    players.sort(key=lambda sp: sp.seat)
    return GameStateResponse(
        status=status,
        error=error,
        play_state=play_state,
        speed=speed,
        phase=snapshot.phase,
        round=snapshot.round_number,
        winner=snapshot.winner,
        sheriff_seat=sheriff_seat,
        alive_count=alive_count,
        dead_count=len(players) - alive_count,
        last_night=captured_last_night if captured_last_night is not None else _last_night(snapshot),
        votes=_votes(snapshot),
        cursor=cursor,
        players=players,
    )


def build_state_from_view(view: ViewResponse) -> GameStateResponse:
    snap = view.snapshot
    tally: dict[str, int] = {}
    if isinstance(snap.vote_tally, dict):
        for target, count in snap.vote_tally.items():
            try:
                tally[str(target)] = int(count)
            except (TypeError, ValueError):
                continue
    players = [
        StatePlayer(
            seat=p.seat,
            name=p.name,
            role=p.role,
            camp=p.camp,
            is_alive=p.is_alive,
            is_sheriff=p.is_sheriff,
            model=p.model,
            status_flags=["alive"] if p.is_alive else ["dead"],
        )
        for p in snap.players
    ]
    players.sort(key=lambda sp: sp.seat)
    return GameStateResponse(
        status=view.status,
        error=view.error,
        phase=snap.phase,
        round=snap.day,
        winner=snap.winner,
        sheriff_seat=snap.sheriff_seat,
        alive_count=snap.alive_count,
        dead_count=snap.dead_count,
        votes=StateVotes(tally=tally),
        cursor=view.cursor,
        players=players,
    )
