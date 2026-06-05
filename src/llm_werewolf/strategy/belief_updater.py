"""Rule-based belief matrix normalization and hard updates."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from llm_werewolf.strategy.seat import get_player_seat
from llm_werewolf.strategy.wolf_team import participates_in_wolf_team
from llm_werewolf.strategy.decisions import BeliefEntry, SecondOrderEntry
from llm_werewolf.strategy.belief_state import BeliefState

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import PlayerProtocol


def _clip_prob(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def default_wolf_prior(num_players: int) -> float:
    if num_players <= 0:
        return 0.2
    return _clip_prob(2.0 / num_players)


def init_belief_state(
    observer: PlayerProtocol,
    alive_players: list[PlayerProtocol],
    *,
    known_wolf_seats: set[int] | None = None,
) -> BeliefState:
    """Build an initial first-order row for one observer."""
    observer_seat = get_player_seat(observer) or 0
    state = BeliefState(observer_seat=observer_seat)
    prior = default_wolf_prior(len(alive_players))
    known_wolves = known_wolf_seats or set()
    observer_is_wolf = participates_in_wolf_team(observer)

    for player in alive_players:
        seat = get_player_seat(player)
        if seat is None:
            continue
        if seat == observer_seat:
            if observer_is_wolf:
                wolf_prob = 0.0
                note = "本人（狼）"
            else:
                wolf_prob = 0.0
                note = "本人（好人阵营）"
        elif seat in known_wolves or (observer_is_wolf and participates_in_wolf_team(player)):
            wolf_prob = 1.0
            note = "已知队友" if observer_is_wolf else "已知狼人"
        elif not player.is_alive():
            wolf_prob = 0.0 if not participates_in_wolf_team(player) else 1.0
            note = "已出局"
        else:
            wolf_prob = prior
            note = None
        state.set_entry(BeliefEntry(target_seat=seat, wolf_probability=wolf_prob, note=note))
    return state


def apply_revealed_role(
    state: BeliefState,
    *,
    target_seat: int,
    is_werewolf: bool,
) -> None:
    """Hard-update one column after public role reveal."""
    state.set_entry(
        BeliefEntry(
            target_seat=target_seat,
            wolf_probability=1.0 if is_werewolf else 0.0,
            note="身份已公开",
        )
    )


def apply_seer_check(
    state: BeliefState,
    *,
    target_seat: int,
    is_werewolf: bool,
) -> None:
    state.set_entry(
        BeliefEntry(
            target_seat=target_seat,
            wolf_probability=1.0 if is_werewolf else 0.0,
            note="预言家验人结果",
        )
    )


def merge_llm_beliefs(
    state: BeliefState,
    first_order: list[BeliefEntry],
    second_order: list[SecondOrderEntry],
    *,
    alive_seats: set[int],
) -> BeliefState:
    """Merge model output into existing state with clipping and alive-seat filter."""
    for entry in first_order:
        if entry.target_seat not in alive_seats:
            continue
        if entry.target_seat == state.observer_seat:
            continue
        existing = state.first_order.get(entry.target_seat)
        if existing and existing.note in {"身份已公开", "预言家验人结果", "已知队友", "已知狼人"}:
            continue
        state.set_entry(
            BeliefEntry(
                target_seat=entry.target_seat,
                wolf_probability=_clip_prob(entry.wolf_probability),
                reason=entry.reason,
                note=entry.reason or entry.note,
            )
        )

    for entry in second_order:
        if entry.observer_seat not in alive_seats:
            continue
        if entry.observer_seat == state.observer_seat:
            continue
        state.second_order[entry.observer_seat] = SecondOrderEntry(
            observer_seat=entry.observer_seat,
            suspects_me_as_wolf=_clip_prob(entry.suspects_me_as_wolf),
            reason=entry.reason,
            note=entry.reason or entry.note,
        )
    return state


def apply_public_elimination_to_all_agents(
    players: list[PlayerProtocol],
    *,
    eliminated_seat: int,
    is_werewolf: bool,
) -> None:
    """After public elimination, collapse the eliminated column for every agent."""
    for player in players:
        agent = player.agent
        if agent is None:
            continue
        state = getattr(agent, "belief_state", None)
        if not isinstance(state, BeliefState):
            continue
        apply_revealed_role(state, target_seat=eliminated_seat, is_werewolf=is_werewolf)


def known_wolf_seats_for_player(player: PlayerProtocol, alive: list[PlayerProtocol]) -> set[int]:
    if not participates_in_wolf_team(player):
        return set()
    seats: set[int] = set()
    for other in alive:
        if other.player_id == player.player_id:
            continue
        if participates_in_wolf_team(other):
            seat = get_player_seat(other)
            if seat is not None:
                seats.add(seat)
    return seats


def ensure_agent_belief_state(
    player: PlayerProtocol,
    alive: list[PlayerProtocol],
) -> BeliefState:
    agent = player.agent
    if agent is None:
        return BeliefState(observer_seat=get_player_seat(player) or 0)

    state = getattr(agent, "belief_state", None)
    if not isinstance(state, BeliefState):
        state = init_belief_state(
            player,
            alive,
            known_wolf_seats=known_wolf_seats_for_player(player, alive),
        )
        agent.belief_state = state
        return state

    alive_seats = {s for s in (get_player_seat(p) for p in alive) if s is not None}
    stale = [seat for seat in state.first_order if seat not in alive_seats]
    for seat in stale:
        del state.first_order[seat]
    stale_b2 = [seat for seat in state.second_order if seat not in alive_seats]
    for seat in stale_b2:
        del state.second_order[seat]
    state.observer_seat = get_player_seat(player) or state.observer_seat

    for other in alive:
        seat = get_player_seat(other)
        if seat is None or seat in state.first_order:
            continue
        prior = default_wolf_prior(len(alive))
        wolf_prob = 1.0 if seat in known_wolf_seats_for_player(player, alive) else prior
        state.set_entry(BeliefEntry(target_seat=seat, wolf_probability=wolf_prob))
    return state
