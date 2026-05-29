"""狼队夜间讨论贡献：计划清晰度 + 队友意向跟随 + 与刀口一致。"""

from __future__ import annotations

import re
import json
from typing import TYPE_CHECKING, Any

from llm_werewolf.game_runtime.types.enums import Camp

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext

_PLAN_KEYWORDS = (
    "刀",
    "杀",
    "出",
    "投",
    "归票",
    "验",
    "身份",
    "狼坑",
    "先出",
    "集火",
    "刀口",
    "目标",
)

_SEAT_IN_TEXT = re.compile(r"(?:座位\s*)?(\d{1,2})\s*号|玩家\s*(\d{1,2})")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _wolf_player_ids(ctx: RunContext) -> set[str]:
    return {pid for pid, entry in ctx.roster.items() if entry.camp == Camp.WEREWOLF.value}


def _kills_by_round(ctx: RunContext) -> dict[int, str]:
    out: dict[int, str] = {}
    for event in ctx.events:
        if event.get("event_type") != "werewolf_killed":
            continue
        rnd = int(event.get("round_number", 0))
        target = str((event.get("data") or {}).get("target_id", ""))
        if target:
            out[rnd] = target
    return out


def _mentioned_player_ids(speech: str, ctx: RunContext) -> set[str]:
    ids: set[str] = set()
    for pid, entry in ctx.roster.items():
        if entry.player_name and entry.player_name in speech:
            ids.add(pid)
    for match in _SEAT_IN_TEXT.finditer(speech):
        seat_str = match.group(1) or match.group(2)
        if not seat_str:
            continue
        try:
            seat = int(seat_str)
        except ValueError:
            continue
        for pid, entry in ctx.roster.items():
            if entry.player_name and f"玩家{seat}" in entry.player_name:
                ids.add(pid)
    return ids


def _plan_clarity_score(speech: str) -> float:
    if not speech or len(speech.strip()) < 8:
        return 0.0
    score = 0.0
    if len(speech) >= 40:
        score += 5.0
    if any(kw in speech for kw in _PLAN_KEYWORDS):
        score += 10.0
    if _SEAT_IN_TEXT.search(speech):
        score += 12.0
    return score


def load_wolf_team_records(
    run_dir: Path, *, wolf_ids: set[str] | None = None
) -> list[dict[str, Any]]:
    """从 vote_intentions 或 events 中提取狼队频道记录。"""
    if wolf_ids is None:
        from llm_werewolf.evaluation.post_game.run_context import roster_from_events

        roster = roster_from_events(_read_jsonl(run_dir / "events.jsonl"))
        wolf_ids = {pid for pid, entry in roster.items() if entry.camp == Camp.WEREWOLF.value}

    rows = [
        row
        for row in _read_jsonl(run_dir / "vote_intentions.jsonl")
        if str(row.get("channel", "")) == "wolf_team"
    ]
    if rows:
        ctx_for_norm: RunContext | None = None
        try:
            from llm_werewolf.evaluation.post_game.run_context import load_run_context

            ctx_for_norm = load_run_context(run_dir)
        except Exception:
            ctx_for_norm = None
        return _normalize_wolf_records(rows, ctx_for_norm)

    ctx_for_norm: RunContext | None = None
    events_path = run_dir / "events.jsonl"
    if events_path.is_file():
        from llm_werewolf.evaluation.post_game.run_context import load_run_context

        try:
            ctx_for_norm = load_run_context(run_dir)
        except Exception:
            ctx_for_norm = None

    for line in _read_jsonl(events_path):
        data = line.get("data") or {}
        if data.get("channel") == "wolf_team":
            rows.append(data)
            continue
        visible = line.get("visible_to")
        if line.get("event_type") != "player_discussion" or not visible:
            continue
        vis = {str(v) for v in visible}
        if not wolf_ids or not vis.issubset(wolf_ids) or len(vis) < 2:
            continue
        rows.append({
            "channel": "wolf_team",
            "round_number": line.get("round_number"),
            "phase": line.get("phase"),
            "speaker_id": data.get("speaker_id") or data.get("player_id"),
            "speaker_name": data.get("speaker_name") or data.get("player_name"),
            "public_speech": (
                data.get("public_speech")
                or data.get("speech")
                or data.get("message")
                or line.get("message")
                or ""
            ),
        })
    return _normalize_wolf_records(rows, ctx_for_norm)


def _normalize_wolf_records(
    records: list[dict[str, Any]], ctx: RunContext | None
) -> list[dict[str, Any]]:
    """补全 speaker 字段，统一 speech 文本键。"""
    if ctx is None:
        return records
    normalized: list[dict[str, Any]] = []
    for rec in records:
        row = dict(rec)
        speaker_id = str(row.get("speaker_id") or "")
        if not speaker_id:
            continue
        entry = ctx.roster.get(speaker_id)
        if entry:
            row.setdefault("speaker_name", entry.player_name)
        if not row.get("public_speech"):
            row["public_speech"] = str(row.get("speech") or row.get("message") or "")
        normalized.append(row)
    return normalized


def build_wolf_night_scores(
    ctx: RunContext, *, wolf_records: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """返回 {by_player, speeches, has_wolf_channel}。"""
    records = (
        wolf_records
        if wolf_records is not None
        else load_wolf_team_records(ctx.run_dir, wolf_ids=_wolf_player_ids(ctx))
    )
    records = _normalize_wolf_records(records, ctx)
    kills = _kills_by_round(ctx)
    wolves = _wolf_player_ids(ctx)

    by_player: dict[str, dict[str, Any]] = {
        pid: {
            "total": 0,
            "plan_clarity": 0.0,
            "teammate_follow": 0,
            "kill_match_bonus": 0,
            "details": [],
        }
        for pid in wolves
    }
    speeches_out: list[dict[str, Any]] = []

    for rec in records:
        speaker = str(rec.get("speaker_id", ""))
        if speaker not in by_player:
            continue
        speech = str(rec.get("public_speech", ""))
        rnd = int(rec.get("round_number", 0))
        plan = _plan_clarity_score(speech)
        kill_target = kills.get(rnd)
        kill_bonus = 0
        if kill_target and kill_target in _mentioned_player_ids(speech, ctx):
            kill_bonus = 15

        swings = rec.get("swings") or []
        follow = sum(1 for s in swings if s.get("camp_aligned"))
        total = plan + follow * 5 + kill_bonus

        row = by_player[speaker]
        row["plan_clarity"] += plan
        row["teammate_follow"] += follow
        row["kill_match_bonus"] += kill_bonus
        row["total"] += total
        if plan > 0:
            row["details"].append(f"R{rnd}:plan")
        if kill_bonus:
            row["details"].append(f"R{rnd}:kill_match")

        speeches_out.append({
            "speaker_id": speaker,
            "speaker_name": rec.get("speaker_name"),
            "round_number": rnd,
            "public_speech": speech,
            "plan_clarity": plan,
            "teammate_follow": follow,
            "kill_match_bonus": kill_bonus,
            "total": total,
        })

    speeches_out.sort(key=lambda s: s.get("total", 0), reverse=True)
    return {"by_player": by_player, "speeches": speeches_out, "has_wolf_channel": bool(records)}
