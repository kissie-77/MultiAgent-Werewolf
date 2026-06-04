"""Project events.jsonl + roster.json into render-ready ViewResponse (方案B)."""

from __future__ import annotations

import json
from pathlib import Path

from llm_werewolf.interface.api.models.view import (
    ViewEvent, ViewPlayer, ViewResponse, ViewSnapshot,
)
from llm_werewolf.interface.api.services.seat import seat_of as _seat_of

# --- event_type -> UI classification ------------------------------------
_SPEECH_TYPES = {"player_speech", "player_discussion", "sheriff_candidate_speech"}
_DEATH_TYPES = {"player_died", "player_eliminated", "lover_died"}
_VOTE_TYPES = {"vote_cast", "vote_result", "sheriff_vote_cast"}
_SKILL_TYPES = {
    "werewolf_killed", "witch_saved", "witch_poisoned", "seer_checked",
    "guard_protected", "graveyard_keeper_check", "hunter_revenge",
    "sheriff_badge_transferred", "role_acting",
}
_PHASE_TYPES = {"phase_changed", "round_started"}
_NIGHT_PHASES = {"night", "setup"}
# Skills that happen publicly during the day; never god-only.
_PUBLIC_SKILLS = {"hunter_revenge", "sheriff_badge_transferred"}

_PHASE_LABELS = {
    "setup": "准备", "night": "夜晚", "sheriff_election": "警长竞选",
    "day_discussion": "白天讨论", "day_voting": "放逐投票", "ended": "对局结束",
}

_SKILL_KIND = {
    "werewolf_killed": "wolf_kill", "witch_saved": "witch_save",
    "witch_poisoned": "witch_poison", "seer_checked": "seer_check",
    "guard_protected": "guard", "hunter_revenge": "hunter_shoot",
    "sheriff_badge_transferred": "badge_transfer",
}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _classify(event_type: str) -> str:
    if event_type in _SPEECH_TYPES:
        return "speech"
    if event_type in _DEATH_TYPES:
        return "death"
    if event_type in _VOTE_TYPES:
        return "vote"
    if event_type in _SKILL_TYPES:
        return "skill"
    if event_type in _PHASE_TYPES:
        return "phase"
    if event_type == "belief_snapshot":
        return "belief"
    if event_type == "vote_intention_snapshot":
        return "vote_intention"
    return "system"


def _reveal_visibility(event_type: str, phase: str) -> tuple[str, str]:
    ui = _classify(event_type)
    if event_type in _PUBLIC_SKILLS:
        return "now", "public"
    # night-phase speech/vote/death stay public; other night actions are god-only until game end
    if ui in {"skill", "belief", "vote_intention"} or phase in _NIGHT_PHASES:
        if ui == "speech" or event_type in _VOTE_TYPES or ui == "death":
            return "now", "public"
        return "on_game_end", "god"
    return "now", "public"


def _map_event(seq: int, row: dict) -> ViewEvent:
    event_type = str(row.get("event_type", ""))
    phase = str(row.get("phase", ""))
    data = row.get("data") or {}
    ui = _classify(event_type)
    reveal, visibility = _reveal_visibility(event_type, phase)

    ev = ViewEvent(
        seq=seq, type=ui, day=int(row.get("round_number", 0)), phase=phase,
        text=str(row.get("message", "")), reveal=reveal, visibility=visibility,
    )
    if ui == "speech":
        ev.speaker = {"seat": _seat_of(data.get("player_id")), "name": data.get("player_name")}
        ev.public_text = data.get("speech")
        ev.private_thought = data.get("private_thought")
    elif ui == "skill":
        ev.skill = {
            "kind": _SKILL_KIND.get(event_type, event_type),
            "actor": {"seat": _seat_of(data.get("player_id"))},
            "target": {"seat": _seat_of(data.get("target_id"))},
            "result": data.get("result"),
        }
    elif ui == "vote":
        ev.vote = {
            "voter": {"seat": _seat_of(data.get("voter_id") or data.get("player_id"))},
            "target": {"seat": _seat_of(data.get("target_id"))},
        }
    elif ui == "death":
        ev.death = {"seat": _seat_of(data.get("player_id")), "name": data.get("player_name"),
                    "cause": data.get("cause")}
    return ev


def _build_snapshot(run_dir: Path, rows: list[dict], status: str) -> ViewSnapshot:
    roster_raw = {}
    roster_path = run_dir / "roster.json"
    if roster_path.is_file():
        try:
            roster_raw = json.loads(roster_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            roster_raw = {}
    roster = roster_raw.get("players", [])

    dead_ids: set[str] = set()
    sheriff_seat = None
    winner = None
    last_phase = "setup"
    last_round = 0
    for row in rows:
        etype = str(row.get("event_type", ""))
        data = row.get("data") or {}
        last_phase = str(row.get("phase", last_phase)) or last_phase
        last_round = int(row.get("round_number", last_round) or last_round)
        if etype in _DEATH_TYPES and data.get("player_id"):
            dead_ids.add(str(data["player_id"]))
        if etype == "sheriff_elected":
            sheriff_seat = _seat_of(data.get("player_id"))
        if etype == "game_ended":
            winner = data.get("winner_camp")

    players: list[ViewPlayer] = []
    for entry in roster:
        pid = entry.get("player_id", "")
        is_alive = pid not in dead_ids
        players.append(ViewPlayer(
            seat=int(entry.get("seat", 0)), name=entry.get("name", ""),
            role=entry.get("role"), camp=entry.get("camp"),
            is_alive=is_alive, is_sheriff=(_seat_of(pid) == sheriff_seat),
            model=entry.get("model"),
            death=None if is_alive else {"reveal": "now"},
        ))
    players.sort(key=lambda p: p.seat)

    return ViewSnapshot(
        day=last_round, phase=last_phase,
        phase_label=f"第{last_round}天 · {_PHASE_LABELS.get(last_phase, last_phase)}",
        winner=winner, alive_count=sum(1 for p in players if p.is_alive),
        dead_count=len(dead_ids), sheriff_seat=sheriff_seat, players=players,
    )


def build_view(run_dir: Path, *, since: int = 0, status: str = "running",
               error: str | None = None) -> ViewResponse:
    rows = _read_jsonl(run_dir / "events.jsonl")
    new_events = [_map_event(idx, row) for idx, row in enumerate(rows) if idx >= since]
    snapshot = _build_snapshot(run_dir, rows, status)
    return ViewResponse(cursor=len(rows), status=status, error=error,
                        snapshot=snapshot, events=new_events)
