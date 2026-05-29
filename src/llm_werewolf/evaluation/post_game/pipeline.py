"""对局结束后统一执行的 PostGame 流水线（分步 try/except）。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.log_views import write_log_views
from llm_werewolf.evaluation.post_game.camp_persuasion import (
    CampPersuasionReport,
    write_camp_persuasion_artifacts,
)
from llm_werewolf.evaluation.post_game.coach.coach import Coach
from llm_werewolf.evaluation.post_game.episodic_bridge import write_episodic_artifacts
from llm_werewolf.evaluation.post_game.game_quality_report import write_game_quality_report
from llm_werewolf.evaluation.post_game.pipeline_steps import (
    StepRecord,
    run_step,
    run_step_async,
    skip_step,
    write_pipeline_steps,
)
from llm_werewolf.evaluation.post_game.prompt_proposal import write_prompt_proposals
from llm_werewolf.evaluation.post_game.replay_agent import run_llm_replay, write_post_game_analysis
from llm_werewolf.evaluation.post_game.run_context import RunContext, load_run_context
from llm_werewolf.evaluation.post_game.scoring.mvp import write_mvp_scores
from llm_werewolf.evaluation.post_game.scoring.score_contexts import write_score_contexts
from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import (
    write_role_skills_artifacts,
)
from llm_werewolf.evaluation.core.vote_swing_analysis import write_persuasion_artifacts
from llm_werewolf.evaluation.scoring.benefit import write_benefit_scores
from llm_werewolf.evaluation.scoring.intention import build_intention_scores, write_intention_scores

logger = logging.getLogger(__name__)

_REQUIRED_STEPS = frozenset({"load_context"})


@dataclass
class PostGameState:
    ctx: RunContext | None = None
    camp_report: CampPersuasionReport | None = None
    intention_payload: dict[str, Any] | None = None
    score_ctx_manifest: dict[str, Any] | None = None
    mvp_payload: dict[str, Any] | None = None
    llm_analysis: dict[str, Any] | None = None


@dataclass
class PostGameResult:
    run_dir: Path
    artifacts: list[str] = field(default_factory=list)
    skipped_llm: bool = False
    error: str | None = None
    stage_errors: dict[str, str] = field(default_factory=dict)
    steps: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """仅必需步骤失败时视为整体失败；可选步骤失败记入 stage_errors。"""
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_dir": str(self.run_dir),
            "artifacts": self.artifacts,
            "skipped_llm": self.skipped_llm,
            "error": self.error,
            "stage_errors": self.stage_errors,
            "steps": self.steps,
            "ok": self.ok,
        }


def _merge_artifacts(result: PostGameResult, names: list[str]) -> None:
    for name in names:
        if name not in result.artifacts:
            result.artifacts.append(name)


def _sync_stage_errors(result: PostGameResult, steps: list[StepRecord]) -> None:
    for record in steps:
        if record.status == "failed":
            result.stage_errors[record.step_id] = record.error or "failed"


def _on_step_done(
    result: PostGameResult,
    steps: list[StepRecord],
    step_id: str,
    value: Any,
    artifacts: list[str],
) -> Any:
    if value is not None:
        _merge_artifacts(result, artifacts)
    return value


async def run_post_game_pipeline(
    run_dir: str | Path,
    *,
    engine: Any | None = None,
    game_result_text: str | None = None,
    config_path: str | Path | None = None,
    prompt_version: str = "v2",
    skip_llm: bool = False,
) -> PostGameResult:
    """分步执行 PostGame；单步失败不中断后续可独立步骤。"""
    result = PostGameResult(run_dir=Path(run_dir))
    steps: list[StepRecord] = []
    state = PostGameState()

    def _ctx() -> RunContext:
        if state.ctx is None:
            msg = "run_context 未加载"
            raise RuntimeError(msg)
        return state.ctx

    loaded = run_step(
        steps,
        "load_context",
        lambda: setattr(state, "ctx", load_run_context(
            result.run_dir,
            engine=engine,
            game_result_text=game_result_text,
            prompt_version=prompt_version,
        )) or state.ctx,
        required=True,
    )
    if loaded is None:
        _sync_stage_errors(result, steps)
        write_pipeline_steps(result.run_dir, steps)
        result.steps = [s.to_dict() for s in steps]
        result.error = "load_context failed"
        return result

    _on_step_done(
        result,
        steps,
        "load_context",
        loaded,
        [],
    )

    _on_step_done(
        result,
        steps,
        "episodic",
        run_step(
            steps,
            "episodic",
            lambda: write_episodic_artifacts(_ctx(), engine=engine),
            artifacts=["episodic_reports.json"],
        ),
        ["episodic_reports.json"],
    )

    _on_step_done(
        result,
        steps,
        "vote_swing",
        run_step(
            steps,
            "vote_swing",
            lambda: write_persuasion_artifacts(_ctx().run_dir),
            artifacts=["vote_swing_report.md", "vote_swing_summary.json"],
        ),
        ["vote_swing_report.md", "vote_swing_summary.json"],
    )

    camp = run_step(
        steps,
        "camp_persuasion",
        lambda: write_camp_persuasion_artifacts(_ctx()),
        artifacts=["camp_persuasion_report.md", "camp_persuasion_summary.json"],
    )
    if camp is not None:
        state.camp_report = camp
        _merge_artifacts(
            result,
            ["camp_persuasion_report.md", "camp_persuasion_summary.json"],
        )

    if state.camp_report is not None:
        _on_step_done(
            result,
            steps,
            "log_views",
            run_step(
                steps,
                "log_views",
                lambda: write_log_views(_ctx(), state.camp_report),
                artifacts=["views/", "views_manifest.json"],
            ),
            ["views/", "views_manifest.json"],
        )
    else:
        skip_step(steps, "log_views", "camp_persuasion 未成功")

    if state.camp_report is not None:
        cr = state.camp_report

        intention = run_step(
            steps,
            "intention_scores",
            lambda: (
                write_intention_scores(_ctx(), cr),
                build_intention_scores(_ctx(), cr),
            )[1],
            artifacts=["intention_scores.json"],
        )
        if intention is not None:
            state.intention_payload = intention
            _merge_artifacts(result, ["intention_scores.json"])

        manifest = run_step(
            steps,
            "score_contexts",
            lambda: write_score_contexts(_ctx()),
            artifacts=["views/score_contexts/", "views/score_contexts/manifest.json"],
        )
        if manifest is not None:
            state.score_ctx_manifest = manifest
            _merge_artifacts(
                result,
                ["views/score_contexts/", "views/score_contexts/manifest.json"],
            )

        mvp = run_step(
            steps,
            "mvp_scores",
            lambda: json.loads(
                write_mvp_scores(
                    _ctx(),
                    cr,
                    intention_payload=state.intention_payload,
                    score_context_manifest=state.score_ctx_manifest,
                ).read_text(encoding="utf-8")
            ),
            artifacts=["mvp_scores.json"],
        )
        if mvp is not None:
            state.mvp_payload = mvp
            _merge_artifacts(result, ["mvp_scores.json"])

        if state.mvp_payload is not None:
            _on_step_done(
                result,
                steps,
                "benefit_scores",
                run_step(
                    steps,
                    "benefit_scores",
                    lambda: write_benefit_scores(
                        _ctx(),
                        cr,
                        intention_by_player=(state.intention_payload or {}).get("by_player"),
                        mvp_payload=state.mvp_payload,
                    ),
                    artifacts=["benefit_scores.json"],
                ),
                ["benefit_scores.json"],
            )
        else:
            skip_step(steps, "benefit_scores", "mvp_scores 未成功")
    else:
        for sid in ("intention_scores", "score_contexts", "mvp_scores", "benefit_scores"):
            skip_step(steps, sid, "camp_persuasion 未成功")

    llm_notes: str | None = None
    if skip_llm:
        skip_step(steps, "llm_replay", "skip_llm=True")
        result.skipped_llm = True
    elif state.mvp_payload is not None and state.camp_report is not None:

        async def _llm() -> dict[str, Any]:
            cfg = Path(config_path) if config_path else None
            return await run_llm_replay(
                _ctx(),
                state.camp_report,
                config_path=cfg,
                mvp_payload=state.mvp_payload,
                dimension_context_paths=state.mvp_payload.get("dimension_context_paths"),
            )

        analysis = await run_step_async(
            steps,
            "llm_replay",
            _llm,
            artifacts=["post_game_analysis.json", "post_game_report.md"],
        )
        if analysis is not None:
            state.llm_analysis = analysis
            write_post_game_analysis(_ctx(), analysis)
            result.skipped_llm = analysis.get("mode") == "skipped"
            _merge_artifacts(result, ["post_game_analysis.json", "post_game_report.md"])
            if analysis.get("mode") == "llm":
                suggestions = analysis.get("prompt_suggestions") or []
                llm_notes = "; ".join(suggestions) if suggestions else analysis.get("summary_zh")
        else:
            result.skipped_llm = True
    else:
        skip_step(steps, "llm_replay", "mvp_scores 未成功")

    _on_step_done(
        result,
        steps,
        "game_quality_report",
        run_step(
            steps,
            "game_quality_report",
            lambda: write_game_quality_report(
                _ctx(),
                state.mvp_payload,
                steps=[s.to_dict() for s in steps],
                llm_analysis=state.llm_analysis,
            ),
            artifacts=["game_quality_report.md", "game_quality_report.json"],
        ),
        ["game_quality_report.md", "game_quality_report.json"],
    )

    if state.camp_report is not None:
        name = run_step(
            steps,
            "prompt_proposals",
            lambda: write_prompt_proposals(
                _ctx(),
                state.camp_report,
                llm_notes=llm_notes,
                mvp_payload=state.mvp_payload,
            ).name,
            artifacts=["prompt_proposals.json"],
        )
        if name:
            _merge_artifacts(result, [name])

        _on_step_done(
            result,
            steps,
            "role_skills",
            run_step(
                steps,
                "role_skills",
                lambda: write_role_skills_artifacts(_ctx(), state.camp_report),
                artifacts=["role_skills.json", "skills/"],
            ),
            ["role_skills.json", "skills/"],
        )

        def _coach() -> None:
            role_skills_path = _ctx().run_dir / "role_skills.json"
            skills_payload = json.loads(role_skills_path.read_text(encoding="utf-8"))
            coach = Coach()
            coach_result = coach.enrich_skills_with_episodes(
                _ctx(),
                list(skills_payload.get("skills") or []),
                engine=engine,
            )
            role_skills_path.write_text(
                json.dumps(skills_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            coach.write_coach_artifacts(
                _ctx(),
                state.camp_report,
                skills_payload,
                engine=engine,
                coach_result=coach_result,
            )

        _on_step_done(
            result,
            steps,
            "coach",
            run_step(steps, "coach", _coach, artifacts=["coach_summary.json"]),
            ["coach_summary.json"],
        )
    else:
        skip_step(steps, "prompt_proposals", "camp_persuasion 未成功")
        skip_step(steps, "role_skills", "camp_persuasion 未成功")
        skip_step(steps, "coach", "camp_persuasion 未成功")

    from llm_werewolf.agent_team.skill_support import skill_loader

    skill_loader.list_role_skill_files.cache_clear()

    _sync_stage_errors(result, steps)
    write_pipeline_steps(result.run_dir, steps)
    result.steps = [s.to_dict() for s in steps]

    failed = [s for s in steps if s.status == "failed"]
    critical = [s for s in failed if s.step_id in _REQUIRED_STEPS]
    if critical:
        result.error = "; ".join(f"{s.step_id}: {s.error}" for s in critical[:3])

    manifest_path = result.run_dir / "post_game_manifest.json"
    steps_summary = json.loads(
        (result.run_dir / "post_game_steps.json").read_text(encoding="utf-8")
    ).get("summary")
    manifest_path.write_text(
        json.dumps(
            {
                "context": _ctx().to_dict(),
                "pipeline": result.to_dict(),
                "steps_summary": steps_summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _merge_artifacts(result, ["post_game_manifest.json", "post_game_steps.json"])

    return result


def run_post_game_pipeline_sync(
    run_dir: str | Path,
    **kwargs: Any,
) -> PostGameResult:
    import asyncio
    import concurrent.futures

    def _run() -> PostGameResult:
        return asyncio.run(run_post_game_pipeline(run_dir, **kwargs))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _run()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(_run).result()
