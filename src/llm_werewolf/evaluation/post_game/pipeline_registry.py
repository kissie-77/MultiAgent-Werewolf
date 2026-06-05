"""PostGame pipeline step metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PostGameStepSpec:
    step_id: str
    artifacts: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    required: bool = False
    description: str = ""


POST_GAME_STEP_SPECS: tuple[PostGameStepSpec, ...] = (
    PostGameStepSpec("load_context", required=True, description="load run context"),
    PostGameStepSpec(
        "episodic", artifacts=("episodic_reports.json",), depends_on=("load_context",)
    ),
    PostGameStepSpec(
        "vote_swing",
        artifacts=("vote_swing_report.md", "vote_swing_summary.json"),
        depends_on=("load_context",),
    ),
    PostGameStepSpec(
        "camp_persuasion",
        artifacts=("camp_persuasion_report.md", "camp_persuasion_summary.json"),
        depends_on=("load_context",),
    ),
    PostGameStepSpec(
        "log_views",
        artifacts=("views/", "views_manifest.json"),
        depends_on=("camp_persuasion",),
    ),
    PostGameStepSpec(
        "intention_scores",
        artifacts=("intention_scores.json",),
        depends_on=("camp_persuasion",),
    ),
    PostGameStepSpec(
        "score_contexts",
        artifacts=("views/score_contexts/", "views/score_contexts/manifest.json"),
        depends_on=("camp_persuasion",),
    ),
    PostGameStepSpec(
        "mvp_scores",
        artifacts=("mvp_scores.json",),
        depends_on=("camp_persuasion", "intention_scores", "score_contexts"),
    ),
    PostGameStepSpec(
        "benefit_scores", artifacts=("benefit_scores.json",), depends_on=("mvp_scores",)
    ),
    PostGameStepSpec(
        "llm_replay",
        artifacts=("post_game_analysis.json", "post_game_report.md"),
        depends_on=("camp_persuasion", "mvp_scores"),
    ),
    PostGameStepSpec(
        "game_quality_report",
        artifacts=("game_quality_report.md", "game_quality_report.json"),
        depends_on=("load_context",),
    ),
    PostGameStepSpec(
        "counterfactual",
        artifacts=("counterfactual_report.json", "counterfactual_report.md"),
        depends_on=("load_context",),
    ),
    PostGameStepSpec(
        "prompt_proposals",
        artifacts=("prompt_proposals.json",),
        depends_on=("camp_persuasion",),
    ),
    PostGameStepSpec(
        "role_skills",
        artifacts=("role_skills.json", "skills/"),
        depends_on=("camp_persuasion",),
    ),
    PostGameStepSpec(
        "coach", artifacts=("coach_summary.json",), depends_on=("role_skills",)
    ),
)

POST_GAME_STEP_REGISTRY: dict[str, PostGameStepSpec] = {
    spec.step_id: spec for spec in POST_GAME_STEP_SPECS
}


def get_step_spec(step_id: str) -> PostGameStepSpec:
    try:
        return POST_GAME_STEP_REGISTRY[step_id]
    except KeyError as exc:
        msg = f"Unknown PostGame step: {step_id}"
        raise KeyError(msg) from exc


def step_artifacts(step_id: str) -> list[str]:
    return list(get_step_spec(step_id).artifacts)


def required_step_ids() -> frozenset[str]:
    return frozenset(spec.step_id for spec in POST_GAME_STEP_SPECS if spec.required)
