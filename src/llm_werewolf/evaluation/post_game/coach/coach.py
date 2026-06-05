"""Coach utilities for post-game enrichment and runtime experience extraction."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from llm_werewolf.evaluation.post_game.episodic_bridge import (
    episode_excerpt_for_player_round,
    export_player_episode_reports,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from llm_werewolf.agent_team.memory.base import CompressorProtocol
    from llm_werewolf.agent_team.memory.semantic_memory import SemanticMemory
    from llm_werewolf.evaluation.post_game.camp_persuasion import CampPersuasionReport
    from llm_werewolf.evaluation.post_game.run_context import RunContext


@dataclass
class CoachResult:
    """Summary of one coach pass over post-game artifacts."""

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
    """Owns coach-layer post-game enrichment and runtime semantic extraction."""

    def extract_semantic_candidates(
        self,
        report: dict[str, Any],
        *,
        won: bool,
        semantic: SemanticMemory,
        top_k: int,
        enable_llm_extraction: bool = False,
        compressor: CompressorProtocol | None = None,
    ) -> list[str]:
        if enable_llm_extraction:
            llm_candidates = self._extract_semantic_candidates_with_llm(
                report,
                won=won,
                semantic=semantic,
                compressor=compressor,
            )
            if llm_candidates:
                return llm_candidates[:top_k]
        return self._extract_semantic_candidates_by_rules(
            report,
            won=won,
            semantic=semantic,
            top_k=top_k,
        )

    def enrich_skills_with_episodes(
        self,
        ctx: RunContext,
        skills: list[dict[str, Any]],
        *,
        engine: Any | None = None,
    ) -> CoachResult:
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
            excerpt = episode_excerpt_for_player_round(ctx, player_id, round_number, engine=engine)
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
        if coach_result is None:
            coach_result = self.enrich_skills_with_episodes(
                ctx,
                list(skills_payload.get("skills") or []),
                engine=engine,
            )

        snapshot = self.build_skill_snapshot(skills_payload)
        previous_snapshot = self._load_previous_snapshot(ctx)
        diff = self.build_skill_diff(previous_snapshot, snapshot)

        payload = {
            "schema": "coach_summary_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_dir": str(ctx.run_dir),
            "winner_camp": ctx.winner_camp,
            "camp_persuasion_speech_count": len(camp_report.speeches),
            "skill_count": skills_payload.get("skill_count", 0),
            "coach": coach_result.to_dict(),
            "skill_snapshot": snapshot,
            "skill_diff": diff,
            "integration": {
                "episodic_memory_api": "EpisodicMemory.export_episode_report",
                "semantic_memory": "coach_owns_runtime_extraction_entry",
            },
        }
        path = ctx.run_dir / "coach_summary.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.write_skill_version_artifacts(ctx, snapshot, diff)
        return path

    def build_skill_snapshot(self, skills_payload: dict[str, Any]) -> dict[str, Any]:
        skills = list(skills_payload.get("skills") or [])
        items = []
        for skill in skills:
            items.append({
                "skill_id": str(skill.get("skill_id") or ""),
                "prompt_role_key": str(skill.get("prompt_role_key") or ""),
                "source_player_id": str(skill.get("source_player_id") or ""),
                "status": str(skill.get("status") or ""),
                "weight": float(skill.get("weight") or 1.0),
                "win_count": int(skill.get("win_count") or 0),
                "use_count": int(skill.get("use_count") or 0),
                "description": str((skill.get("skill_card") or {}).get("when_to_use") or ""),
            })
        return {
            "schema": "skill_snapshot_v1",
            "skill_count": len(items),
            "skills": sorted(items, key=lambda item: (item["prompt_role_key"], item["skill_id"])),
        }

    def build_skill_diff(
        self,
        previous_snapshot: dict[str, Any] | None,
        current_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        current_items = {item["skill_id"]: item for item in current_snapshot.get("skills", [])}
        previous_items = {
            item["skill_id"]: item for item in (previous_snapshot or {}).get("skills", [])
        }

        added = [current_items[skill_id] for skill_id in current_items.keys() - previous_items.keys()]
        removed = [previous_items[skill_id] for skill_id in previous_items.keys() - current_items.keys()]

        changed: list[dict[str, Any]] = []
        for skill_id in current_items.keys() & previous_items.keys():
            before = previous_items[skill_id]
            after = current_items[skill_id]
            field_changes: dict[str, Any] = {}
            for field in ("weight", "win_count", "use_count", "status", "description"):
                if before.get(field) != after.get(field):
                    field_changes[field] = {"before": before.get(field), "after": after.get(field)}
            if field_changes:
                changed.append({"skill_id": skill_id, "changes": field_changes})

        return {
            "schema": "skill_diff_v1",
            "has_previous_version": previous_snapshot is not None,
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
            "added": sorted(added, key=lambda item: item["skill_id"]),
            "removed": sorted(removed, key=lambda item: item["skill_id"]),
            "changed": sorted(changed, key=lambda item: item["skill_id"]),
        }

    def write_skill_version_artifacts(
        self,
        ctx: RunContext,
        snapshot: dict[str, Any],
        diff: dict[str, Any],
    ) -> None:
        snapshot_path = ctx.run_dir / "skill_snapshot.json"
        snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        diff_path = ctx.run_dir / "skill_diff.json"
        diff_path.write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_previous_snapshot(self, ctx: RunContext) -> dict[str, Any] | None:
        candidates = [
            ctx.run_dir / "skill_snapshot.previous.json",
            self._resolve_previous_snapshot_path_from_meta(ctx),
            self._resolve_sibling_run_snapshot(ctx),
        ]
        for candidate in candidates:
            if candidate is None or not candidate.is_file():
                continue
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                logger.warning("Failed to load previous skill snapshot", exc_info=True)
                return None
        return None

    def _resolve_sibling_run_snapshot(self, ctx: RunContext) -> Path | None:
        from llm_werewolf.evaluation.leaderboard.entry_builder import infer_previous_run_dir

        previous_run_dir = infer_previous_run_dir(ctx.run_dir)
        if not previous_run_dir:
            return None
        snapshot = Path(previous_run_dir) / "skill_snapshot.json"
        return snapshot if snapshot.is_file() else None

    def _resolve_previous_snapshot_path_from_meta(self, ctx: RunContext) -> Path | None:
        meta_path = ctx.run_dir / "experiment_meta.json"
        if not meta_path.is_file():
            return None
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Failed to load experiment meta for previous skill snapshot", exc_info=True)
            return None
        if not isinstance(payload, dict):
            return None

        snapshot_path = payload.get("previous_skill_snapshot_path")
        if isinstance(snapshot_path, str) and snapshot_path.strip():
            resolved = Path(snapshot_path)
            if not resolved.is_absolute():
                resolved = (ctx.run_dir / resolved).resolve()
            return resolved

        previous_run_dir = payload.get("previous_run_dir")
        if isinstance(previous_run_dir, str) and previous_run_dir.strip():
            resolved_run_dir = Path(previous_run_dir)
            if not resolved_run_dir.is_absolute():
                resolved_run_dir = (ctx.run_dir / resolved_run_dir).resolve()
            return resolved_run_dir / "skill_snapshot.json"
        return None

    def _extract_semantic_candidates_with_llm(
        self,
        report: dict[str, Any],
        *,
        won: bool,
        semantic: SemanticMemory,
        compressor: CompressorProtocol | None,
    ) -> list[str]:
        if compressor is None:
            return []

        lines = [
            "请从以下狼人杀对局记录中提炼 1-3 条可复用的策略经验。",
            "每条不超过 50 字，只输出策略经验列表，不要写流水账。",
            f"本局结果：{'胜利' if won else '失败'}",
        ]
        for episode in report.get("episodes", []):
            messages = episode.get("key_event_messages", []) + episode.get("decision_event_messages", [])
            if messages:
                lines.append(f"第{episode.get('round_number')}轮：" + "；".join(messages[:4]))

        try:
            response = compressor.call_llm_text("\n".join(lines), max_tokens=300)
        except Exception:
            logger.warning("Semantic candidate extraction via LLM failed", exc_info=True)
            return []

        candidates: list[str] = []
        for raw_line in response.splitlines():
            line = raw_line.strip().lstrip("-*0123456789.[] ")
            if line:
                candidates.append(line[:80])
        return semantic.deduplicate_candidates(candidates)

    def _extract_semantic_candidates_by_rules(
        self,
        report: dict[str, Any],
        *,
        won: bool,
        semantic: SemanticMemory,
        top_k: int,
    ) -> list[str]:
        candidates: list[str] = []
        for episode in report.get("episodes", []):
            round_number = episode.get("round_number")
            key_messages = episode.get("key_event_messages", [])
            decision_messages = episode.get("decision_event_messages", [])

            if key_messages:
                candidates.append(f"关键局势复盘：第{round_number}轮出现" + "；".join(key_messages[:2]))
            if decision_messages:
                candidates.append(f"决策经验：第{round_number}轮重点关注" + "；".join(decision_messages[:2]))
            if won and key_messages:
                candidates.append(f"胜利经验：第{round_number}轮保留对" + "；".join(key_messages[:1]) + "的持续跟踪")
            if not won and decision_messages:
                candidates.append(f"失败反思：第{round_number}轮不要过早依赖" + "；".join(decision_messages[:1]) + "形成判断")

        merged = semantic.merge_reflections(semantic.deduplicate_candidates(candidates))
        return merged[:top_k]
