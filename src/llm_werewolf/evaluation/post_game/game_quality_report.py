"""对局质量报告：基于 MVP 分、金句与分维度证据生成人读报告。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from datetime import datetime, timezone

from llm_werewolf.evaluation.post_game.turning_points import build_turning_points

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext

_CAMP_LABELS = {"werewolf": "狼人阵营", "villager": "好人阵营", "neutral": "中立"}


def _camp_label(camp: str | None) -> str:
    if not camp:
        return "未知"
    return _CAMP_LABELS.get(camp, camp)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _format_breakdown(row: dict[str, Any]) -> str:
    raw = row.get("breakdown_raw") or {}
    norm = row.get("breakdown_norm") or {}
    parts = []
    for key, label in (
        ("persuasion", "公开说服"),
        ("wolf_night", "狼队夜间"),
        ("strategy", "策略执行"),
        ("outcome", "结果贡献"),
    ):
        if raw.get(key, 0) or norm.get(key, 0):
            parts.append(f"{label} 原始{raw.get(key, 0)}/归一{norm.get(key, 0)}")
    return "；".join(parts) if parts else "—"


def _mvp_highlights(mvp: dict[str, Any] | None) -> list[str]:
    lines: list[str] = []
    if not mvp:
        return ["- 未能评定 MVP（缺少投票意向或事件数据）。"]

    lines.append(
        f"- **{mvp.get('player_name')}**（{mvp.get('role_name')}，{_camp_label(mvp.get('camp'))}）"
        f" — 综合分 **{mvp.get('mvp_total')}**（全场第 1，可为任意阵营）"
    )
    lines.append(f"- 得分构成：{_format_breakdown(mvp)}")

    golden = mvp.get("golden_speech_candidates") or []
    if golden:
        lines.append("")
        lines.append("### 金句与关键发言")
        for g in golden[:5]:
            kind = "公开说服" if g.get("kind") == "public_persuasion" else "狼队夜间"
            lines.append(
                f"- **[{kind}]** 第 {g.get('round_number')} 轮："
                f"「{(g.get('excerpt') or '')[:300]}」"
            )
            if g.get("matched_elimination"):
                lines.append("  - 与当轮放逐方向一致")
            if g.get("kill_match_bonus"):
                lines.append(f"  - 夜间计划与刀口相关（加分 {g.get('kill_match_bonus')}）")

    evidence = mvp.get("top_evidence") or []
    if evidence:
        lines.append("")
        lines.append("### 策略/结果证据")
        for ev in evidence:
            why = ev.get("why", "")
            excerpt = ev.get("excerpt")
            line = f"- {ev.get('kind', 'evidence')}: {why}"
            if excerpt:
                line += f" — 「{excerpt}」"
            lines.append(line)

    return lines


def _ranking_table(players: list[dict[str, Any]], *, limit: int = 9) -> list[str]:
    lines = [
        "",
        "| 排名 | 玩家 | 身份 | 阵营 | 综合分 | 说服(归一) | 狼夜 | 策略 | 结果 |",
        "|------|------|------|------|--------|------------|------|------|------|",
    ]
    for row in players[:limit]:
        raw = row.get("breakdown_raw") or {}
        norm = row.get("breakdown_norm") or {}
        lines.append(
            f"| {row.get('rank')} | {row.get('player_name')} | {row.get('role_name', '—')} "
            f"| {_camp_label(row.get('camp'))} | **{row.get('mvp_total')}** "
            f"| {norm.get('persuasion', 0)} | {norm.get('wolf_night', 0)} "
            f"| {norm.get('strategy', 0)} | {norm.get('outcome', 0)} |"
        )
        _ = raw
    return lines


def _mvp_ranking_notes(
    players: list[dict[str, Any]], swing_ranking: list[dict[str, Any]] | None
) -> list[str]:
    if not swing_ranking:
        return []
    swing_top = swing_ranking[0] if swing_ranking else None
    mvp_row = players[0] if players else None
    if not swing_top or not mvp_row:
        return []
    if swing_top.get("player_id") == mvp_row.get("player_id"):
        return []
    return [
        "",
        "### 评分与摇摆排名差异",
        f"- 投票摇摆最高：**{swing_top.get('player_name')}**（influence {swing_top.get('total_influence_score')}）",
        f"- MVP 第 1：**{mvp_row.get('player_name')}**（综合 {mvp_row.get('mvp_total')}）",
        "- 差异通常来自狼夜/策略/结果维度或阵营感知说服规则。",
    ]


def _pipeline_steps_section(steps: list[dict[str, Any]]) -> list[str]:
    if not steps:
        return []
    lines = ["", "## 复盘流水线状态", ""]
    ok = sum(1 for s in steps if s.get("status") == "ok")
    failed = sum(1 for s in steps if s.get("status") == "failed")
    skipped = sum(1 for s in steps if s.get("status") == "skipped")
    lines.append(f"- 成功 **{ok}** 步，失败 **{failed}** 步，跳过 **{skipped}** 步")
    lines.append("")
    lines.append("| 步骤 | 状态 | 耗时(ms) | 说明 |")
    lines.append("|------|------|----------|------|")
    for s in steps:
        err = (s.get("error") or "")[:80]
        note = err if s.get("status") == "failed" else ", ".join(s.get("artifacts") or [])[:60]
        lines.append(
            f"| `{s.get('step_id')}` | {s.get('status')} | {s.get('duration_ms', 0):.0f} | {note or '—'} |"
        )
    return lines


def build_game_quality_report(
    ctx: RunContext,
    mvp_payload: dict[str, Any] | None,
    *,
    steps: list[dict[str, Any]] | None = None,
    llm_analysis: dict[str, Any] | None = None,
    benefit_payload: dict[str, Any] | None = None,
    swing_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mvp_payload = mvp_payload or {}
    players = mvp_payload.get("players") or []
    mvp = mvp_payload.get("mvp")
    camp_mvp = mvp_payload.get("camp_mvp") or {}
    dq = mvp_payload.get("data_quality") or {}
    wolf = mvp_payload.get("wolf_night_analysis") or {}

    sections_md: list[str] = [
        "# 对局质量报告",
        "",
        f"- 生成时间：{datetime.now(timezone.utc).isoformat()}",
        f"- 对局目录：`{ctx.run_dir}`",
        f"- Prompt 版本：**{ctx.prompt_version}**",
        f"- 胜负：**{_camp_label(ctx.winner_camp)}** 胜",
        "",
        "## 1. 数据质量与评分置信度",
        "",
        f"- 投票意向数据：{'有' if dq.get('has_vote_intentions') else '无'}",
        f"- 狼队夜间频道：{'有' if dq.get('has_wolf_team_channel') else '无'}",
        f"- 分析发言条数：{dq.get('speech_count', 0)}",
        f"- 完整白天轮数：{dq.get('distinct_day_rounds', '—')}",
        f"- 置信度：**{dq.get('confidence', 'unknown')}**",
    ]
    for note in dq.get("limitations") or []:
        sections_md.append(f"- 局限：{note}")
    sections_md.extend([
        "",
        "说明：公开说服维度依赖 `vote_intentions` 中 `channel=public` 记录；"
        "狼队维度依赖 `channel=wolf_team` 或狼队可见 `player_discussion`。",
        "",
        "## 2. 关键转折（规则）",
        "",
    ])
    sections_md.extend(build_turning_points(ctx) or ["- 无足够事件生成转折链。"])
    sections_md.extend(["", "## 3. 全场 MVP", ""])
    sections_md.extend(_mvp_highlights(mvp))

    if camp_mvp:
        sections_md.extend(["", "## 4. 阵营 MVP", ""])
        for camp, row in camp_mvp.items():
            if isinstance(row, dict):
                sections_md.append(
                    f"- **{_camp_label(camp)}**：{row.get('player_name')} "
                    f"（{row.get('role_name')}，分 {row.get('mvp_total')}）"
                )

    sections_md.extend(["", "## 5. 玩家综合排名", ""])
    sections_md.extend(_ranking_table(players))
    sections_md.extend(_mvp_ranking_notes(players, (swing_summary or {}).get("player_ranking")))

    top_wolf_speeches = wolf.get("speeches") or []
    if top_wolf_speeches:
        sections_md.extend(["", "## 6. 狼队夜间讨论亮点", ""])
        for sp in top_wolf_speeches[:5]:
            name = sp.get("speaker_name")
            if not name and sp.get("speaker_id"):
                entry = ctx.roster.get(str(sp.get("speaker_id")))
                name = entry.player_name if entry else sp.get("speaker_id")
            sections_md.append(
                f"- **{name or '未知'}** R{sp.get('round_number')} "
                f"（计划{sp.get('plan_clarity')}/跟随{sp.get('teammate_follow')}/刀口{sp.get('kill_match_bonus')}）"
            )
            excerpt = (sp.get("public_speech") or "")[:240]
            if excerpt:
                sections_md.append(f"  - 「{excerpt}」")

    llm_mode = (llm_analysis or {}).get("mode")
    summary_zh = (llm_analysis or {}).get("summary_zh")
    if llm_mode == "llm" and summary_zh:
        sections_md.extend(["", "## 7. LLM 复盘摘要", ""])
        sections_md.append(str(summary_zh))
        suggestions = llm_analysis.get("prompt_suggestions") or []
        if suggestions:
            sections_md.append("")
            sections_md.append("**Prompt 方向建议：**")
            for s in suggestions:
                sections_md.append(f"- {s}")
    elif summary_zh:
        sections_md.extend(["", "## 7. 复盘摘要", ""])
        sections_md.append(str(summary_zh))

    sections_md.extend(["", "## 8. 后续调优入口", ""])
    sections_md.append("- **Prompt 金句**：见 `prompt_proposals.json`（由 MVP 公开说服片段提炼）")
    sections_md.append("- **策略 Skill**：见 `role_skills.json` 与 `skills/`（含场景与证据引用）")
    sections_md.append("- **分维度原始材料**：`views/score_contexts/`（禁止混用全局 events）")
    dim_paths = mvp_payload.get("dimension_context_paths") or {}
    for dim, rel in dim_paths.items():
        sections_md.append(f"  - `{dim}` → `{rel}`")

    sections_md.extend(_pipeline_steps_section(steps or []))

    return {
        "schema": "game_quality_report_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(ctx.run_dir),
        "winner_camp": ctx.winner_camp,
        "mvp_player_id": mvp.get("player_id") if mvp else None,
        "data_quality": dq,
        "markdown": "\n".join(sections_md) + "\n",
        "benefit_ref": benefit_payload.get("schema") if benefit_payload else None,
    }


def write_game_quality_report(
    ctx: RunContext,
    mvp_payload: dict[str, Any] | None,
    *,
    steps: list[dict[str, Any]] | None = None,
    llm_analysis: dict[str, Any] | None = None,
) -> Path:
    benefit = _load_json(ctx.run_dir / "benefit_scores.json")
    swing_summary = _load_json(ctx.run_dir / "vote_swing_summary.json")
    payload = build_game_quality_report(
        ctx,
        mvp_payload,
        steps=steps,
        llm_analysis=llm_analysis,
        benefit_payload=benefit,
        swing_summary=swing_summary,
    )
    md_path = ctx.run_dir / "game_quality_report.md"
    md_path.write_text(payload["markdown"], encoding="utf-8")

    json_path = ctx.run_dir / "game_quality_report.json"
    json_payload = {k: v for k, v in payload.items() if k != "markdown"}
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path
