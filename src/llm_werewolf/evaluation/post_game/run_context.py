"""从对局目录或引擎状态构建赛后分析上下文。"""

from __future__ import annotations

import json
from typing import Any
from pathlib import Path
from dataclasses import field, dataclass

from llm_werewolf.game_runtime.types.enums import Camp
from llm_werewolf.game_runtime.roles.catalog import ROLE_CATALOG, get_definition
from llm_werewolf.game_runtime.roles.registry import build_catalog_to_runtime_map
from llm_werewolf.evaluation.post_game.event_adapter import event_to_dict


def _runtime_role_camp_map() -> dict[str, str]:
    """运行时角色名 -> 阵营值（werewolf / villager / neutral）。"""
    catalog_to_runtime = build_catalog_to_runtime_map()
    out: dict[str, str] = {}
    for definition in ROLE_CATALOG:
        runtime_name = catalog_to_runtime.get(definition.name, definition.name)
        out[runtime_name] = definition.camp.value
        out[definition.name] = definition.camp.value
    return out


_ROLE_CAMP = _runtime_role_camp_map()


def role_name_to_camp(role_name: str) -> str | None:
    if role_name in _ROLE_CAMP:
        return _ROLE_CAMP[role_name]
    try:
        return get_definition(role_name).camp.value
    except KeyError:
        return None


@dataclass
class PlayerRosterEntry:
    player_id: str
    player_name: str
    role_name: str | None = None
    camp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "role_name": self.role_name,
            "camp": self.camp,
        }


@dataclass
class RunContext:
    """一局赛后分析所需的只读上下文。"""

    run_dir: Path
    events: list[dict[str, Any]] = field(default_factory=list)
    roster: dict[str, PlayerRosterEntry] = field(default_factory=dict)
    winner_camp: str | None = None
    winner_ids: list[str] = field(default_factory=list)
    game_result_text: str | None = None
    prompt_version: str = "v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_dir": str(self.run_dir),
            "prompt_version": self.prompt_version,
            "winner_camp": self.winner_camp,
            "winner_ids": self.winner_ids,
            "game_result_text": self.game_result_text,
            "roster": {pid: e.to_dict() for pid, e in self.roster.items()},
            "event_count": len(self.events),
        }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for _line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
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


def _apply_role(
    roster: dict[str, PlayerRosterEntry],
    player_id: str,
    role_name: str,
    player_name: str | None = None,
) -> None:
    camp = role_name_to_camp(role_name)
    entry = roster.get(player_id)
    if entry is None:
        entry = PlayerRosterEntry(player_id=player_id, player_name=player_name or player_id)
        roster[player_id] = entry
    if player_name:
        entry.player_name = player_name
    entry.role_name = role_name
    entry.camp = camp


def _apply_player_name(
    roster: dict[str, PlayerRosterEntry], player_id: str, player_name: str
) -> None:
    if not player_id or not player_name:
        return
    entry = roster.get(player_id)
    if entry is None:
        roster[player_id] = PlayerRosterEntry(player_id=player_id, player_name=player_name)
    else:
        entry.player_name = player_name


def _role_hint_from_event(event: dict[str, Any]) -> tuple[str, str, str | None] | None:
    """从单条事件提取 (player_id, role_name, player_name?)；评测读全量 events（上帝视角）。"""
    etype = str(event.get("event_type", ""))
    data = event.get("data") or {}

    if etype in {"role_acting", "player_eliminated", "role_revealed"}:
        pid = str(data.get("player_id", ""))
        role = data.get("role")
        if pid and role:
            name = data.get("player_name")
            return pid, str(role), str(name) if name else None

    if etype == "player_discussion":
        pid = str(data.get("player_id", ""))
        role = data.get("role")
        if pid and role:
            name = data.get("player_name")
            return pid, str(role), str(name) if name else None

    return None


def _names_from_vote_intention(event: dict[str, Any]) -> list[tuple[str, str]]:
    if str(event.get("event_type", "")) != "vote_intention_snapshot":
        return []
    data = event.get("data") or {}
    pairs: list[tuple[str, str]] = []
    for bucket in (data.get("before") or {}, data.get("after") or {}):
        if not isinstance(bucket, dict):
            continue
        for entry in bucket.values():
            if not isinstance(entry, dict):
                continue
            pid = str(entry.get("player_id", ""))
            name = str(entry.get("player_name", ""))
            if pid and name:
                pairs.append((pid, name))
    speaker_id = str(data.get("speaker_id", ""))
    speaker_name = str(data.get("speaker_name", ""))
    if speaker_id and speaker_name:
        pairs.append((speaker_id, speaker_name))
    return pairs


def roster_from_events(events: list[dict[str, Any]]) -> dict[str, PlayerRosterEntry]:
    """从 events.jsonl 构建 roster（PostGame 全量日志，含 role_acting 等私密字段）。"""
    roster: dict[str, PlayerRosterEntry] = {}

    for event in events:
        hint = _role_hint_from_event(event)
        if hint is not None:
            pid, role, name = hint
            _apply_role(roster, pid, role, name)

        etype = event.get("event_type")
        data = event.get("data") or {}

        if etype == "player_died":
            pid = str(data.get("player_id", ""))
            if pid and pid not in roster:
                roster[pid] = PlayerRosterEntry(
                    player_id=pid, player_name=str(data.get("player_name", pid))
                )

        if etype == "player_speech":
            pid = str(data.get("player_id", ""))
            name = str(data.get("player_name", ""))
            if pid and name:
                _apply_player_name(roster, pid, name)

        for pid, name in _names_from_vote_intention(event):
            _apply_player_name(roster, pid, name)

        if etype == "game_ended":
            for wid in data.get("winner_ids") or []:
                wid = str(wid)
                if wid not in roster:
                    roster[wid] = PlayerRosterEntry(player_id=wid, player_name=wid)

    return roster


def merge_rosters(*rosters: dict[str, PlayerRosterEntry]) -> dict[str, PlayerRosterEntry]:
    """合并多个 roster；后出现的 role_name 覆盖先前的空角色条目。"""
    merged: dict[str, PlayerRosterEntry] = {}
    for roster in rosters:
        for pid, entry in roster.items():
            if pid not in merged:
                merged[pid] = PlayerRosterEntry(
                    player_id=entry.player_id,
                    player_name=entry.player_name,
                    role_name=entry.role_name,
                    camp=entry.camp,
                )
                continue
            target = merged[pid]
            if entry.player_name and entry.player_name != pid:
                target.player_name = entry.player_name
            if entry.role_name:
                target.role_name = entry.role_name
                target.camp = entry.camp
    return merged


def winner_from_events(events: list[dict[str, Any]]) -> tuple[str | None, list[str]]:
    for event in reversed(events):
        if event.get("event_type") != "game_ended":
            continue
        data = event.get("data") or {}
        camp = data.get("winner_camp")
        ids = [str(x) for x in (data.get("winner_ids") or [])]
        return (str(camp) if camp else None, ids)
    return None, []


def roster_from_engine(engine: Any) -> dict[str, PlayerRosterEntry]:
    roster: dict[str, PlayerRosterEntry] = {}
    state = engine.game_state
    if state is None:
        return roster
    for player in state.players:
        camp = player.role.camp.value if hasattr(player, "role") and player.role else None
        roster[player.player_id] = PlayerRosterEntry(
            player_id=player.player_id,
            player_name=player.name,
            role_name=player.get_role_name(),
            camp=camp,
        )
    return roster


def load_run_context(
    run_dir: str | Path,
    *,
    engine: Any | None = None,
    game_result_text: str | None = None,
    prompt_version: str = "v1",
) -> RunContext:
    path = Path(run_dir)
    events_path = path / "events.jsonl"
    events = _read_jsonl(events_path)

    if engine is not None and hasattr(engine, "event_logger"):
        if not events and engine.event_logger.events:
            events = [event_to_dict(e) for e in engine.event_logger.events]

    from llm_werewolf.evaluation.core.vote_swing_analysis import ensure_vote_intentions_jsonl

    tracker_records: list[dict[str, Any]] | None = None
    if engine is not None and getattr(engine, "game_state", None) is not None:
        tracker = getattr(engine.game_state, "vote_intention_tracker", None)
        if tracker is not None:
            tracker_records = tracker.export_records()
    ensure_vote_intentions_jsonl(path, records=tracker_records, events=events)

    roster = roster_from_events(events)
    if engine is not None:
        roster = merge_rosters(roster, roster_from_engine(engine))

    winner_camp, winner_ids = winner_from_events(events)
    if engine is not None and engine.game_state and engine.game_state.winner:
        if not winner_camp and hasattr(engine.game_state.winner, "value"):
            winner_camp = engine.game_state.winner.value
        elif not winner_camp:
            winner_camp = str(engine.game_state.winner)

    return RunContext(
        run_dir=path,
        events=events,
        roster=roster,
        winner_camp=winner_camp,
        winner_ids=winner_ids,
        game_result_text=game_result_text,
        prompt_version=prompt_version,
    )


def target_id_to_camp(target_id: str | None, roster: dict[str, PlayerRosterEntry]) -> str | None:
    if not target_id:
        return None
    entry = roster.get(target_id)
    return entry.camp if entry else None


def is_camp_aligned_vote_target(speaker_camp: str | None, target_camp: str | None) -> bool:
    """发言者阵营是否「希望」其他玩家把票意向指向 target_camp 的玩家。"""
    if not speaker_camp or not target_camp or target_camp == Camp.NEUTRAL.value:
        return False
    if speaker_camp == Camp.WEREWOLF.value:
        return target_camp == Camp.VILLAGER.value
    if speaker_camp == Camp.VILLAGER.value:
        return target_camp == Camp.WEREWOLF.value
    return False
