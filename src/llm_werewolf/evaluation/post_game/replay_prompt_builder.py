"""Assemble replay analyst user prompts from externalized templates + run artifacts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from llm_werewolf.evaluation.post_game.turning_points import build_turning_points
from llm_werewolf.evaluation.registry.post_game_prompt_registry import (
    ReplayPromptBundle,
    render_template,
    load_replay_prompt_bundle,
)

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext


def _read_context_file(run_dir: Path, rel_path: str, *, max_chars: int = 5000) -> str:
    path = run_dir / rel_path
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")[:max_chars]


def build_replay_prompt(
    ctx: RunContext,
    *,
    mvp_payload: dict[str, Any] | None = None,
    dimension_context_paths: dict[str, str] | None = None,
    prompt_version: str | None = None,
) -> str:
    bundle = load_replay_prompt_bundle(prompt_version)
    return _assemble_replay_user_prompt(
        ctx,
        bundle,
        mvp_payload=mvp_payload or {},
        dimension_context_paths=dimension_context_paths or {},
    )


def _assemble_replay_user_prompt(
    ctx: RunContext,
    bundle: ReplayPromptBundle,
    *,
    mvp_payload: dict[str, Any],
    dimension_context_paths: dict[str, str],
) -> str:
    template = bundle.user_template
    paths = dimension_context_paths or mvp_payload.get("dimension_context_paths") or {}

    sections: list[str] = []
    intro = template.get("intro") or []
    if isinstance(intro, list):
        sections.extend(str(line) for line in intro)
    sections.append("")

    meta = template.get("meta") or {}
    if isinstance(meta, dict):
        sections.append(
            render_template(
                str(meta.get("winner_camp", "胜负阵营: {winner_camp}")),
                winner_camp=ctx.winner_camp,
            )
        )
        sections.append(
            render_template(
                str(meta.get("prompt_version", "Prompt 版本: {prompt_version}")),
                prompt_version=ctx.prompt_version,
            )
        )
        sections.append(
            render_template(
                str(meta.get("game_result", "结果说明: {game_result_text}")),
                game_result_text=ctx.game_result_text or "（无）",
            )
        )

    turning_points = build_turning_points(ctx)
    if turning_points:
        sections.extend(["", str(template.get("timeline_section_title", "")), ""])
        sections.extend(turning_points)

    sections.extend(["", str(template.get("mvp_section_title", "")), ""])

    mvp = mvp_payload.get("mvp")
    if mvp:
        sections.append(
            render_template(
                str(template.get("mvp_line", "")),
                player_name=mvp.get("player_name", ""),
                role_name=mvp.get("role_name", ""),
                camp=mvp.get("camp", ""),
                mvp_total=mvp.get("mvp_total", ""),
            )
        )
    for row in (mvp_payload.get("players") or [])[:5]:
        sections.append(
            render_template(
                str(template.get("player_rank_line", "")),
                rank=row.get("rank", ""),
                player_name=row.get("player_name", ""),
                mvp_total=row.get("mvp_total", ""),
                breakdown_raw=row.get("breakdown_raw", ""),
            )
        )

    golden: list[dict[str, Any]] = []
    if mvp and mvp.get("player_id"):
        for player in mvp_payload.get("players") or []:
            if player.get("player_id") == mvp.get("player_id"):
                golden = player.get("golden_speech_candidates") or []
                break
    if golden:
        sections.extend(["", str(template.get("golden_section_title", "")), ""])
        for item in golden[:5]:
            excerpt = str(item.get("excerpt", ""))[:200]
            sections.append(
                render_template(
                    str(template.get("golden_line", "")),
                    kind=item.get("kind", ""),
                    round_number=item.get("round_number", ""),
                    excerpt=excerpt,
                )
            )

    dimension_focus = template.get("dimension_focus") or {}
    focus_prefix = str(template.get("dimension_focus_prefix", ""))
    for dim, title in bundle.dimensions.items():
        rel = paths.get(dim)
        if not rel:
            continue
        body = _read_context_file(ctx.run_dir, rel)
        if not body.strip():
            continue
        sections.extend([
            "",
            render_template(str(template.get("dimension_title", "")), title=title),
            render_template(str(template.get("dimension_source", "")), rel_path=rel),
        ])
        if isinstance(dimension_focus, dict) and dim in dimension_focus:
            sections.append(f"{focus_prefix}{dimension_focus[dim]}")
        sections.append("")
        sections.append(body)

    dq = mvp_payload.get("data_quality") or {}
    data_quality = template.get("data_quality") or {}
    sections.extend(["", str(template.get("data_quality_title", "")), ""])
    if isinstance(data_quality, dict):
        sections.append(
            render_template(
                str(data_quality.get("vote_intentions", "")),
                has_vote_intentions=dq.get("has_vote_intentions"),
            )
        )
        sections.append(
            render_template(
                str(data_quality.get("wolf_channel", "")),
                has_wolf_team_channel=dq.get("has_wolf_team_channel"),
            )
        )
        sections.append(
            render_template(
                str(data_quality.get("confidence", "")),
                confidence=dq.get("confidence"),
            )
        )

    output_instructions = template.get("output_instructions") or []
    if isinstance(output_instructions, list):
        sections.append("")
        sections.extend(str(line) for line in output_instructions)

    return "\n".join(sections)
