"""对局日志多视角切片：god / player POV / digest。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.post_game.log_views.filters import (
    estimate_tokens,
    event_line,
    filter_events_for_player,
    sanitize_event_message,
)
from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport
from llm_werewolf.evaluation.post_game.run_context import RunContext
from llm_werewolf.game_runtime.prompts.manager import PromptManager

_PUBLIC_EVENT_TYPES = frozenset({
    "player_speech",
    "vote_cast",
    "vote_result",
    "player_eliminated",
    "player_died",
    "game_ended",
    "phase_change",
    "death_announcement",
    "vote_intention_snapshot",
})


@dataclass
class ViewManifestEntry:
    view_id: str
    path: str
    token_estimate: int
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "view_id": self.view_id,
            "path": self.path,
            "token_estimate": self.token_estimate,
            "description": self.description,
        }


@dataclass
class ViewManifest:
    views: list[ViewManifestEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"views": [v.to_dict() for v in self.views]}


def _write_text(path: Path, content: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return estimate_tokens(content)


def _write_json(path: Path, payload: Any) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")
    return estimate_tokens(text)


def build_god_timeline(events: list[dict[str, Any]], *, max_events: int = 500) -> str:
    lines = ["# God Timeline", ""]
    for event in events[-max_events:]:
        lines.append(event_line(event))
    return "\n".join(lines) + "\n"


def build_player_timeline(
    events: list[dict[str, Any]],
    player_id: str,
    *,
    max_events: int = 300,
) -> str:
    pov = filter_events_for_player(events, player_id)[-max_events:]
    lines = [f"# Player POV: {player_id}", ""]
    for event in pov:
        lines.append(event_line(event))
    return "\n".join(lines) + "\n"


def build_public_digest(events: list[dict[str, Any]], *, max_events: int = 200) -> str:
    public = [
        e
        for e in events
        if e.get("visible_to") is None or e.get("event_type") in _PUBLIC_EVENT_TYPES
    ][-max_events:]
    lines = ["# Public Digest", ""]
    for event in public:
        lines.append(event_line(event, max_len=300))
    return "\n".join(lines) + "\n"


def build_swing_digest(camp_report: CampPersuasionReport, *, top_n: int = 15) -> dict[str, Any]:
    ranked = sorted(
        camp_report.speeches,
        key=lambda s: s.camp_aligned_score,
        reverse=True,
    )[:top_n]
    return {
        "winner_camp": camp_report.winner_camp,
        "entries": [
            {
                "speaker_id": s.speaker_id,
                "speaker_name": s.speaker_name,
                "speaker_camp": s.speaker_camp,
                "round_number": s.round_number,
                "camp_aligned_score": s.camp_aligned_score,
                "camp_aligned_swings": s.camp_aligned_swings,
                "matched_round_elimination": s.matched_round_elimination,
                "public_speech_excerpt": s.public_speech[:200],
            }
            for s in ranked
        ],
    }


def build_role_timeline(
    events: list[dict[str, Any]],
    ctx: RunContext,
    prompt_role_key: str,
    *,
    max_events: int = 300,
) -> str:
    player_ids = [
        pid
        for pid, entry in ctx.roster.items()
        if entry.role_name
        and PromptManager.get_prompt_role_key(entry.role_name) == prompt_role_key
    ]
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pid in player_ids:
        for event in filter_events_for_player(events, pid):
            key = json.dumps(
                [
                    event.get("event_type"),
                    event.get("round_number"),
                    event.get("message"),
                ],
                ensure_ascii=False,
            )
            if key not in seen:
                seen.add(key)
                merged.append(event)
    merged.sort(key=lambda e: (int(e.get("round_number", 0)), str(e.get("event_type", ""))))
    lines = [f"# Role POV: {prompt_role_key}", ""]
    for event in merged[-max_events:]:
        lines.append(event_line(event))
    return "\n".join(lines) + "\n"


def write_log_views(
    ctx: RunContext,
    camp_report: CampPersuasionReport,
    *,
    max_events_per_view: int = 200,
) -> ViewManifest:
    """生成 runs/<id>/views/ 与 views_manifest.json。"""
    views_dir = ctx.run_dir / "views"
    manifest = ViewManifest()
    events = ctx.events

    god_path = views_dir / "god_timeline.md"
    god_text = build_god_timeline(events, max_events=max_events_per_view)
    manifest.views.append(
        ViewManifestEntry(
            view_id="god",
            path=str(god_path.relative_to(ctx.run_dir)),
            token_estimate=_write_text(god_path, god_text),
            description="全量事件（截断 thinking）",
        )
    )

    public_path = views_dir / "public_digest.md"
    public_text = build_public_digest(events, max_events=max_events_per_view)
    manifest.views.append(
        ViewManifestEntry(
            view_id="public_digest",
            path=str(public_path.relative_to(ctx.run_dir)),
            token_estimate=_write_text(public_path, public_text),
            description="公开讨论 + 投票 + 死亡公告",
        )
    )

    swing_path = views_dir / "swing_digest.json"
    swing_payload = build_swing_digest(camp_report)
    manifest.views.append(
        ViewManifestEntry(
            view_id="swing_digest",
            path=str(swing_path.relative_to(ctx.run_dir)),
            token_estimate=_write_json(swing_path, swing_payload),
            description="高影响说服发言摘要",
        )
    )

    for player_id in sorted(ctx.roster.keys()):
        player_path = views_dir / f"player_{player_id}_timeline.md"
        player_text = build_player_timeline(events, player_id, max_events=max_events_per_view)
        manifest.views.append(
            ViewManifestEntry(
                view_id=f"player:{player_id}",
                path=str(player_path.relative_to(ctx.run_dir)),
                token_estimate=_write_text(player_path, player_text),
                description=f"当局者 POV ({player_id})",
            )
        )

    for role_key in ("wolf", "prophet", "witch", "villager", "guard", "hunter", "wolf_king"):
        role_path = views_dir / f"role_{role_key}_timeline.md"
        role_text = build_role_timeline(events, ctx, role_key, max_events=max_events_per_view)
        manifest.views.append(
            ViewManifestEntry(
                view_id=f"role:{role_key}",
                path=str(role_path.relative_to(ctx.run_dir)),
                token_estimate=_write_text(role_path, role_text),
                description=f"同身份 POV 并集 ({role_key})",
            )
        )

    manifest_path = ctx.run_dir / "views_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
