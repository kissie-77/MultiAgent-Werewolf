"""教练：将 PostGame 产物与情景记忆 episode 对齐，供后续语义记忆 / Skill 审核使用。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport
from llm_werewolf.evaluation.post_game.episodic_bridge import (
    episode_excerpt_for_player_round,
    export_player_episode_reports,
)
from llm_werewolf.evaluation.post_game.run_context import RunContext


@dataclass
class CoachResult:
    """一局 PostGame 的教练层摘要。"""

    enriched_skill_count: int = 0
    players_with_episodes: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enriched_skill_count": self.enriched_skill_count,
            "players_with_episodes": self.players_with_episodes,
            "notes": self.notes,
        }


class Coach:
    """衔接情景记忆与 Skill 产物：为每条 Skill 附加 POV episode 证据。"""

    def enrich_skills_with_episodes(
        self,
        ctx: RunContext,
        skills: list[dict[str, Any]],
        *,
        engine: Any | None = None,
    ) -> CoachResult:
        """在 role_skills[] 的 evidence 中写入 episodic_excerpt（与运行时 EpisodicMemory 同源）。"""
        result = CoachResult()
        reports = export_player_episode_reports(ctx, engine=engine)
        result.players_with_episodes = sum(
            1
            for report in reports.get("by_player", {}).values()
            if report.get("episode_count", 0) > 0
        )

        for skill in skills:
            if skill.get("status") == "skipped":
                continue
            evidence = skill.setdefault("evidence", {})
            player_id = str(skill.get("source_player_id") or "")
            round_number = int(evidence.get("round_number") or 0)
            if not player_id or round_number <= 0:
                continue
            excerpt = episode_excerpt_for_player_round(
                ctx,
                player_id,
                round_number,
                engine=engine,
            )
            if excerpt is None:
                continue
            evidence["episodic_excerpt"] = excerpt
            result.enriched_skill_count += 1

        if result.enriched_skill_count == 0 and ctx.roster:
            result.notes.append("no episodic excerpts matched skill rounds; check visible_to on events")
        return result

    def write_coach_artifacts(
        self,
        ctx: RunContext,
        camp_report: CampPersuasionReport,
        skills_payload: dict[str, Any],
        *,
        engine: Any | None = None,
        coach_result: CoachResult | None = None,
    ) -> Path:
        """写出 coach_summary.json（不修改运行时 Prompt）。"""
        if coach_result is None:
            coach_result = self.enrich_skills_with_episodes(
                ctx,
                list(skills_payload.get("skills") or []),
                engine=engine,
            )

        payload = {
            "schema": "coach_summary_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_dir": str(ctx.run_dir),
            "winner_camp": ctx.winner_camp,
            "camp_persuasion_speech_count": len(camp_report.speeches),
            "skill_count": skills_payload.get("skill_count", 0),
            "coach": coach_result.to_dict(),
            "integration": {
                "episodic_memory_api": "EpisodicMemory.export_episode_report",
                "semantic_memory": "deferred_to_runtime_MemoryManager",
            },
        }
        path = ctx.run_dir / "coach_summary.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
