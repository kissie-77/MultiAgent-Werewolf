"""Authoritative live-state response models for GET /games/{run_id}/state (spec §5.1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PlayState = Literal["playing", "paused"]
SessionStatus = Literal["running", "paused", "ended", "cancelled", "error"]
# sub_phase is an OPEN-ENDED display hint (spec §5.1 shows "... "). The engine's
# night scheduler (M3) emits free-form names beyond this canonical set (e.g.
# "pre_wolf", "werewolf_kill"), so the response field is `str | None` — this
# constant documents the common values but does NOT constrain the field.
COMMON_SUB_PHASES = (
    "werewolf_chat", "witch_decide", "seer_check", "guard", "graveyard_check",
)


class StatePlayer(BaseModel):
    seat: int
    name: str
    role: str | None = None
    camp: str | None = None
    is_alive: bool = True
    is_sheriff: bool = False
    model: str | None = None
    status_flags: list[str] = Field(default_factory=list)


class NightDeath(BaseModel):
    seat: int
    cause: str | None = None


class LastNight(BaseModel):
    deaths: list[NightDeath] = Field(default_factory=list)
    saved_seat: int | None = None
    guarded_seat: int | None = None
    poisoned_seat: int | None = None


class StateVotes(BaseModel):
    by_seat: dict[str, int] = Field(default_factory=dict)
    tally: dict[str, int] = Field(default_factory=dict)


class GameStateResponse(BaseModel):
    status: SessionStatus
    error: str | None = None
    play_state: PlayState = "playing"
    speed: int = 1
    phase: str = "setup"
    sub_phase: str | None = None    # open-ended display hint (see COMMON_SUB_PHASES)
    round: int = 0
    current_actor_seat: int | None = None
    winner: str | None = None
    sheriff_seat: int | None = None
    alive_count: int = 0
    dead_count: int = 0
    last_night: LastNight = Field(default_factory=LastNight)
    votes: StateVotes = Field(default_factory=StateVotes)
    cursor: int = 0
    players: list[StatePlayer] = Field(default_factory=list)
