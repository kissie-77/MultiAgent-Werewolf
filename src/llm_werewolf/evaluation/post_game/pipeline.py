"""对局结束后统一执行的 PostGame 流水线（分步 try/except）。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.post_game.camp_persuasion import (
    CampPersuasionReport,
    write_camp_persuasion_artifacts,
)
from llm_werewolf.evaluation.post_game.game_quality_report import write_game_quality_report
from llm_werewolf.evaluation.post_game.log_views import write_log_views
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
from llm_werewolf.evaluation.post_game.skill_extractor import write_role_skills_artifacts
from llm_werewolf.evaluation.post_game.scoring.benefit import write_benefit_scores
from llm_werewolf.evaluation.post_game.scoring.intention import (
    build_intention_scores,
    write_intention_scores,
)
from llm_werewolf.evaluation.post_game.scoring.mvp import write_mvp_scores
from llm_werewolf.evaluation.post_game.scoring.score_contexts import write_score_contexts
from llm_werewolf.evaluation.post_game.vote_swing_analysis import write_persuasion_artifacts


@dataclass
class PostGameState:
    """步骤间共享状态。"""

    ctx: RunContext | None = None
    camp_report: CampPersuasionReport | None = None
    intention_payload: dict[str, Any] | None = None
    score_ctx_manifest: dict[str, Any] | None = None
    benefit_payload: dict[str, Any] | None = None
    mvp_payload: dict[str, Any] | None = None
    llm_analysis: dict[str, Any] | None = None


@dataclass
class PostGameResult:
    run_dir: Path
    artifacts: list[str] = field(default_factory=list)
    skipped_llm: bool = False
    error: str | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_dir": str(self.run_dir),
            "artifacts": self.artifacts,
            "skipped_llm": self.skipped_llm,
            "error": self.error,
            "steps": self.steps,
        }


def _merge_artifacts(result: PostGameResult, names: list[str]) -> None:
    for name in names:
        if name not in result.artifacts:
            result.artifacts.append(name)


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
    errors: list[str] = []

    def _ctx() -> RunContext:
        if state.ctx is None:
            msg = "run_context 未加载"
            raise RuntimeError(msg)
        return state.ctx

    # --- 1. 上下文（必需）---
    def _load_ctx() -> RunContext:
        return load_run_context(
            result.run_dir,
            engine=engine,
            game_result_text=game_result_text,
            prompt_version=prompt_version,
        )

    loaded = run_step(
        steps,
        "load_context",
        lambda: setattr(state, "ctx", _load_ctx()) or state.ctx,
        required=True,
    )
    if loaded is None:
        write_pipeline_steps(result.run_dir, steps)
        result.steps = [s.to_dict() for s in steps]
        result.error = "load_context failed"
        return result

    # --- 2. 说服摇摆 ---
    run_step(
        steps,
        "vote_swing",
        lambda: write_persuasion_artifacts(_ctx().run_dir),
        artifacts=["vote_swing_report.md", "vote_swing_summary.json"],
    )
    _merge_artifacts(result, ["vote_swing_report.md", "vote_swing_summary.json"])

    # --- 3. 阵营说服 ---
    camp = run_step(
        steps,
        "camp_persuasion",
        lambda: write_camp_persuasion_artifacts(_ctx()),
        artifacts=["camp_persuasion_report.md", "camp_persuasion_summary.json"],
    )
    if camp is not None:
        state.camp_report = camp
        _merge_artifacts(result, ["camp_persuasion_report.md", "camp_persuasion_summary.json"])
    else:
        errors.append("camp_persuasion")

    # --- 4. 日志视图（人读）---
    if state.camp_report is not None:

        def _views() -> None:
            write_log_views(_ctx(), state.camp_report)

        run_step(steps, "log_views", _views, artifacts=["views/", "views_manifest.json"])
        _merge_artifacts(result, ["views/", "views_manifest.json"])
    else:
        skip_step(steps, "log_views", "camp_persuasion 未成功")

    # --- 5–8. 打分与 MVP ---
    if state.camp_report is not None:
        cr = state.camp_report

        def _intention() -> dict[str, Any]:
            write_intention_scores(_ctx(), cr)
            return build_intention_scores(_ctx(), cr)

        intention = run_step(
            steps,
            "intention_scores",
            _intention,
            artifacts=["intention_scores.json"],
        )
        if intention is not None:
            state.intention_payload = intention
            _merge_artifacts(result, ["intention_scores.json"])

        def _score_ctx() -> dict[str, Any]:
            return write_score_contexts(_ctx())

        manifest = run_step(
            steps,
            "score_contexts",
            _score_ctx,
            artifacts=["views/score_contexts/", "views/score_contexts/manifest.json"],
        )
        if manifest is not None:
            state.score_ctx_manifest = manifest
            _merge_artifacts(result, ["views/score_contexts/", "views/score_contexts/manifest.json"])

        def _benefit() -> dict[str, Any]:
            return write_benefit_scores(
                _ctx(),
                cr,
                intention_by_player=(state.intention_payload or {}).get("by_player"),
            )

        benefit = run_step(steps, "benefit_scores", _benefit, artifacts=["benefit_scores.json"])
        if benefit is not None:
            state.benefit_payload = benefit
            _merge_artifacts(result, ["benefit_scores.json"])

        def _mvp() -> dict[str, Any]:
            path = write_mvp_scores(
                _ctx(),
                cr,
                intention_payload=state.intention_payload,
                score_context_manifest=state.score_ctx_manifest,
                benefit_payload=state.benefit_payload,
            )
            return json.loads(path.read_text(encoding="utf-8"))

        mvp = run_step(steps, "mvp_scores", _mvp, artifacts=["mvp_scores.json"])
        if mvp is not None:
            state.mvp_payload = mvp
            _merge_artifacts(result, ["mvp_scores.json"])
    else:
        for sid in ("intention_scores", "score_contexts", "mvp_scores", "benefit_scores"):
            skip_step(steps, sid, "camp_persuasion 未成功")

    # --- 9. LLM 复盘（可选）---
    llm_notes: str | None = None
    if skip_llm:
        skip_step(steps, "llm_replay", "skip_llm=True")
        result.skipped_llm = True
    elif state.mvp_payload is not None:

        async def _llm() -> dict[str, Any]:
            cfg = Path(config_path) if config_path else None
            assert state.camp_report is not None
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
            errors.append("llm_replay")
            result.skipped_llm = True
    else:
        skip_step(steps, "llm_replay", "mvp_scores 未成功")

    # --- 10. 对局质量报告 ---
    def _quality_report() -> None:
        write_game_quality_report(
            _ctx(),
            state.mvp_payload,
            steps=[s.to_dict() for s in steps],
            llm_analysis=state.llm_analysis,
        )

    run_step(
        steps,
        "game_quality_report",
        _quality_report,
        artifacts=["game_quality_report.md", "game_quality_report.json"],
    )
    _merge_artifacts(result, ["game_quality_report.md", "game_quality_report.json"])

    # --- 11–12. 提案与 Skill ---
    if state.camp_report is not None:

        def _proposals() -> str:
            path = write_prompt_proposals(
                _ctx(),
                state.camp_report,
                llm_notes=llm_notes,
                mvp_payload=state.mvp_payload,
                llm_analysis=state.llm_analysis,
            )
            return path.name

        name = run_step(steps, "prompt_proposals", _proposals, artifacts=["prompt_proposals.json"])
        if name:
            _merge_artifacts(result, [name])

        def _skills() -> None:
            write_role_skills_artifacts(
                _ctx(),
                state.camp_report,
                mvp_payload=state.mvp_payload,
            )

        run_step(
            steps,
            "role_skills",
            _skills,
            artifacts=["role_skills.json", "skills/"],
        )
        _merge_artifacts(result, ["role_skills.json", "skills/"])
    else:
        skip_step(steps, "prompt_proposals", "camp_persuasion 未成功")
        skip_step(steps, "role_skills", "camp_persuasion 未成功")

    # --- manifest ---
    failed = [s for s in steps if s.status == "failed"]
    if failed:
        result.error = "; ".join(f"{s.step_id}: {s.error}" for s in failed[:3])
    elif errors:
        result.error = "partial: " + ", ".join(errors)

    manifest_path = result.run_dir / "post_game_manifest.json"

    def _manifest() -> Path:
        write_pipeline_steps(result.run_dir, steps)
        result.steps = [s.to_dict() for s in steps]
        payload = {
            "context": _ctx().to_dict(),
            "pipeline": result.to_dict(),
            "steps_summary": {
                "total": len(steps),
                "ok": sum(1 for s in steps if s.status == "ok"),
                "failed": sum(1 for s in steps if s.status == "failed"),
                "skipped": sum(1 for s in steps if s.status == "skipped"),
            },
        }
        manifest_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest_path

    run_step(
        steps,
        "post_game_manifest",
        _manifest,
        artifacts=["post_game_manifest.json", "post_game_steps.json"],
    )
    _merge_artifacts(result, ["post_game_manifest.json", "post_game_steps.json"])
    result.steps = [s.to_dict() for s in steps]

    return result


def run_post_game_pipeline_sync(
    run_dir: str | Path,
    **kwargs: Any,
) -> PostGameResult:
    import asyncio
    import concurrent.futures

    coro = run_post_game_pipeline(run_dir, **kwargs)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()
