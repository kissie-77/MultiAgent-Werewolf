"""对局结束后统一执行的 PostGame 流水线。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.log_views import write_log_views
from llm_werewolf.evaluation.post_game.camp_persuasion import (
    write_camp_persuasion_artifacts,
)
from llm_werewolf.evaluation.post_game.coach.coach import Coach
from llm_werewolf.evaluation.post_game.episodic_bridge import write_episodic_artifacts
from llm_werewolf.evaluation.post_game.prompt_proposal import write_prompt_proposals
from llm_werewolf.evaluation.post_game.replay_agent import run_llm_replay, write_post_game_analysis
from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import write_role_skills_artifacts
from llm_werewolf.evaluation.scoring.benefit import write_benefit_scores
from llm_werewolf.evaluation.scoring.intention import build_intention_scores, write_intention_scores
from llm_werewolf.evaluation.core.vote_swing_analysis import write_persuasion_artifacts

logger = logging.getLogger(__name__)


@dataclass
class PostGameResult:
    run_dir: Path
    artifacts: list[str] = field(default_factory=list)
    skipped_llm: bool = False
    error: str | None = None
    stage_errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None and not self.stage_errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_dir": str(self.run_dir),
            "artifacts": self.artifacts,
            "skipped_llm": self.skipped_llm,
            "error": self.error,
            "stage_errors": self.stage_errors,
            "ok": self.ok,
        }


async def run_post_game_pipeline(
    run_dir: str | Path,
    *,
    engine: Any | None = None,
    game_result_text: str | None = None,
    config_path: str | Path | None = None,
    prompt_version: str = "v2",
    skip_llm: bool = False,
) -> PostGameResult:
    """在一局结束后自动运行：说服 → 视图 → 打分 → LLM 复盘 → 双 JSON + Skill MD。"""
    result = PostGameResult(run_dir=Path(run_dir))
    ctx = None
    camp_report = None

    try:
        ctx = load_run_context(
            result.run_dir,
            engine=engine,
            game_result_text=game_result_text,
            prompt_version=prompt_version,
        )

        try:
            write_episodic_artifacts(ctx, engine=engine)
            result.artifacts.append("episodic_reports.json")
        except Exception as exc:
            result.stage_errors["episodic"] = str(exc)
            logger.warning("PostGame episodic export failed: %s", exc)

        write_persuasion_artifacts(ctx.run_dir)
        result.artifacts.extend(["vote_swing_report.md", "vote_swing_summary.json"])

        camp_report = write_camp_persuasion_artifacts(ctx)
        result.artifacts.extend(["camp_persuasion_report.md", "camp_persuasion_summary.json"])

        write_log_views(ctx, camp_report)
        result.artifacts.extend(["views/", "views_manifest.json"])

        write_intention_scores(ctx, camp_report)
        intention_payload = build_intention_scores(ctx, camp_report)
        write_benefit_scores(
            ctx,
            camp_report,
            intention_by_player=intention_payload.get("by_player"),
        )
        result.artifacts.extend(["intention_scores.json", "benefit_scores.json"])

        public_digest = ""
        swing_digest = ""
        public_path = ctx.run_dir / "views" / "public_digest.md"
        swing_path = ctx.run_dir / "views" / "swing_digest.json"
        if public_path.is_file():
            public_digest = public_path.read_text(encoding="utf-8")
        if swing_path.is_file():
            swing_digest = swing_path.read_text(encoding="utf-8")

        llm_notes: str | None = None
        if not skip_llm:
            try:
                cfg = Path(config_path) if config_path else None
                analysis = await run_llm_replay(
                    ctx,
                    camp_report,
                    config_path=cfg,
                    public_digest=public_digest,
                    swing_digest=swing_digest,
                )
                write_post_game_analysis(ctx, analysis)
                result.artifacts.extend(["post_game_analysis.json", "post_game_report.md"])
                result.skipped_llm = analysis.get("mode") == "skipped"
                if analysis.get("mode") == "llm":
                    suggestions = analysis.get("prompt_suggestions") or []
                    llm_notes = "; ".join(suggestions) if suggestions else analysis.get("summary_zh")
            except Exception as exc:
                result.stage_errors["llm_replay"] = str(exc)
                result.skipped_llm = True
                logger.warning("PostGame LLM replay failed: %s", exc)
        else:
            result.skipped_llm = True

        proposal_path = write_prompt_proposals(ctx, camp_report, llm_notes=llm_notes)
        result.artifacts.append(proposal_path.name)

        role_skills_path = write_role_skills_artifacts(ctx, camp_report)
        result.artifacts.extend(["role_skills.json", "skills/"])

        try:
            skills_payload = json.loads(role_skills_path.read_text(encoding="utf-8"))
            coach = Coach()
            coach_result = coach.enrich_skills_with_episodes(
                ctx,
                list(skills_payload.get("skills") or []),
                engine=engine,
            )
            role_skills_path.write_text(
                json.dumps(skills_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            coach.write_coach_artifacts(
                ctx,
                camp_report,
                skills_payload,
                engine=engine,
                coach_result=coach_result,
            )
            result.artifacts.append("coach_summary.json")
        except Exception as exc:
            result.stage_errors["coach"] = str(exc)
            logger.warning("PostGame coach/episodic enrich failed: %s", exc)

        from llm_werewolf.agent_team.skill_support import skill_loader

        skill_loader.list_role_skill_files.cache_clear()

    except Exception as exc:
        result.error = str(exc)
        logger.exception("PostGame pipeline failed: %s", exc)

    manifest = result.run_dir / "post_game_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "context": ctx.to_dict() if ctx is not None else None,
                "pipeline": result.to_dict(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    result.artifacts.append("post_game_manifest.json")

    return result


def run_post_game_pipeline_sync(
    run_dir: str | Path,
    **kwargs: Any,
) -> PostGameResult:
    import asyncio

    return asyncio.run(run_post_game_pipeline(run_dir, **kwargs))
