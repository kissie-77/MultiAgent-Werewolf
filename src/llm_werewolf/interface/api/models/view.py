"""Render-ready projection models for the pure-LLM spectate frontend."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RevealMode = Literal["now", "on_death", "on_game_end"]
Visibility = Literal["public", "wolf", "god"]
ViewEventType = Literal[
    "speech", "skill", "vote", "death", "phase", "sub_phase",
    "system", "belief", "vote_intention",
]


class ViewPlayer(BaseModel):
    seat: int
    name: str
    role: str | None = None          # god-view truth; frontend masks per reveal
    camp: str | None = None
    is_alive: bool = True
    is_sheriff: bool = False
    model: str | None = None
    provider: str | None = None
    death: dict[str, Any] | None = None  # {day, phase, cause, reveal}


class ViewSnapshot(BaseModel):
    day: int = 0
    phase: str = "setup"
    phase_label: str = ""
    winner: str | None = None
    alive_count: int = 0
    dead_count: int = 0
    sheriff_seat: int | None = None
    players: list[ViewPlayer] = Field(default_factory=list)
    vote_tally: dict[str, Any] | None = None


class ViewEvent(BaseModel):
    seq: int
    type: ViewEventType
    day: int = 0
    phase: str = ""
    text: str = ""
    speaker: dict[str, Any] | None = None
    public_text: str | None = None
    private_thought: str | None = None
    skill: dict[str, Any] | None = None
    vote: dict[str, Any] | None = None
    death: dict[str, Any] | None = None
    sub_phase: dict[str, Any] | None = None
    reveal: RevealMode = "now"
    visibility: Visibility = "public"


class ViewResponse(BaseModel):
    cursor: int
    status: str                       # running | ended | cancelled | error
    error: str | None = None
    snapshot: ViewSnapshot
    events: list[ViewEvent] = Field(default_factory=list)
