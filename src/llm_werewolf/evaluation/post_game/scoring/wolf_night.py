"""狼队夜间讨论贡献：计划清晰度 + 队友意向跟随 + 与刀口一致。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.post_game.run_context import RunContext, target_id_to_camp
from llm_werewolf.game_runtime.types.enums import Camp

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
    return {
        pid
        for pid, entry in ctx.roster.items()
        if entry.camp == Camp.WEREWOLF.value
    }


def _kills_by_round(ctx: RunContext) -> dict[int, str]:
    return _kills_by_round_from_events(ctx.events)


def _kills_by_round_from_events(events: list[dict[str, Any]]) -> dict[int, str]:
    out: dict[int, str] = {}
    for event in events:
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
            pname = entry.player_name or ""
            if pname == f"玩家{seat}" or pname.endswith(str(seat)):
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


def _teammate_follow_score(
    record: dict[str, Any],
    speaker_id: str,
    wolves: set[str],
) -> float:
    """发言后其他狼队成员意向是否朝村民目标变化。"""
    swings = record.get("swings") or []
    score = 0.0
    for swing in swings:
        if not isinstance(swing, dict):
            continue
        listener = str(swing.get("player_id", ""))
        if listener == speaker_id or listener not in wolves:
            continue
        to_id = swing.get("to_target_id")
        if not to_id:
            continue
        score += 8.0
    return score


def _kill_match_bonus(
    speech: str,
    rnd: int,
    ctx: RunContext,
    kills_by_round: dict[int, str],
) -> tuple[float, str | None]:
    target_id = kills_by_round.get(rnd)
    if not target_id:
        return 0.0, None
    mentioned = _mentioned_player_ids(speech, ctx)
    if target_id in mentioned:
        return 25.0, target_id
    target_camp = target_id_to_camp(target_id, ctx.roster)
    if target_camp == Camp.VILLAGER.value and _plan_clarity_score(speech) >= 10:
        return 8.0, target_id
    return 0.0, target_id


def load_wolf_team_records(run_dir: Path) -> list[dict[str, Any]]:
    intentions = _read_jsonl(run_dir / "vote_intentions.jsonl")
    return [r for r in intentions if str(r.get("channel", "")) == "wolf_team"]


def build_wolf_night_scores(
    ctx: RunContext,
    *,
    records: list[dict[str, Any]] | None = None,
    outcome_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """按狼人汇总夜间讨论贡献；仅使用 wolf_team 记录与刀口事件。"""
    wolves = _wolf_player_ids(ctx)
    if not wolves:
        return {"by_player": {}, "speeches": [], "has_wolf_channel": False}

    if records is None:
        records = load_wolf_team_records(ctx.run_dir)
        if not records:
            records = _wolf_discussion_from_events(ctx)

    kill_events = outcome_events if outcome_events is not None else ctx.events
    kills_by_round = _kills_by_round_from_events(kill_events)
    by_player: dict[str, float] = {pid: 0.0 for pid in wolves}
    speech_rows: list[dict[str, Any]] = []

    for idx, record in enumerate(records):
        speaker_id = str(record.get("speaker_id", ""))
        if speaker_id not in wolves:
            continue
        speech = str(record.get("public_speech", ""))
        rnd = int(record.get("round_number", 0))
        clarity = _plan_clarity_score(speech)
        follow = _teammate_follow_score(record, speaker_id, wolves)
        kill_bonus, kill_target = _kill_match_bonus(speech, rnd, ctx, kills_by_round)
        total = clarity + follow + kill_bonus
        by_player[speaker_id] = by_player.get(speaker_id, 0.0) + total

        speech_rows.append(
            {
                "index": idx,
                "speaker_id": speaker_id,
                "speaker_name": record.get("speaker_name", speaker_id),
                "round_number": rnd,
                "phase": record.get("phase", "night"),
                "channel": "wolf_team",
                "public_speech": speech,
                "plan_clarity": round(clarity, 1),
                "teammate_follow": round(follow, 1),
                "kill_match_bonus": round(kill_bonus, 1),
                "kill_target_id": kill_target,
                "speech_total": round(total, 1),
            }
        )

    speech_rows.sort(key=lambda r: r.get("speech_total", 0), reverse=True)

    return {
        "has_wolf_channel": bool(records),
        "by_player": {pid: round(score, 1) for pid, score in by_player.items()},
        "speeches": speech_rows,
    }


def _wolf_discussion_from_events(ctx: RunContext) -> list[dict[str, Any]]:
    """从 events 的 player_discussion（仅狼可见）回退。"""
    wolves = _wolf_player_ids(ctx)
    rows: list[dict[str, Any]] = []
    for event in ctx.events:
        if event.get("event_type") != "player_discussion":
            continue
        visible = event.get("visible_to")
        if not visible or not wolves.issubset(set(visible)) and len(visible) > 4:
            continue
        data = event.get("data") or {}
        pid = str(data.get("player_id", ""))
        if pid not in wolves:
            continue
        rows.append(
            {
                "round_number": int(event.get("round_number", 0)),
                "phase": event.get("phase", "night"),
                "channel": "wolf_team",
                "speaker_id": pid,
                "speaker_name": data.get("player_name", pid),
                "public_speech": data.get("speech", ""),
                "swings": [],
            }
        )
    return rows
