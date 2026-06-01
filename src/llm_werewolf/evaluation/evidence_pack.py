"""Build a grading evidence pack from existing evaluation artifacts.

The pack is intentionally read-only: it summarizes evidence that already exists
under eval/evolution run directories without changing runtime Agent behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvidencePackPaths:
    json_path: Path
    markdown_path: Path


def build_evidence_pack(
    *,
    eval_root: str | Path,
    output_dir: str | Path,
    evolution_root: str | Path | None = None,
    exclude_frontend: bool = True,
) -> EvidencePackPaths:
    """Write JSON and Markdown grading evidence summaries."""
    eval_base = Path(eval_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema": "grading_evidence_pack_v1",
        "scope": "non_frontend" if exclude_frontend else "full_project",
        "eval_root": str(eval_base),
        "evolution_root": str(evolution_root) if evolution_root is not None else None,
        "score_estimate": _score_estimate(exclude_frontend=exclude_frontend),
        "rubric_items": _rubric_items(eval_base, evolution_root),
        "information_isolation": summarize_information_isolation(eval_base),
        "evolution": summarize_evolution(evolution_root),
        "rollback": summarize_rollback_candidates(evolution_root),
        "next_actions": _next_actions(),
    }

    json_path = out / "grading_evidence_pack.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    markdown_path = out / "grading_evidence_pack.md"
    markdown_path.write_text(_format_markdown(payload), encoding="utf-8")

    return EvidencePackPaths(json_path=json_path, markdown_path=markdown_path)


def summarize_information_isolation(eval_root: str | Path) -> dict[str, Any]:
    """Aggregate InformationIsolationChecker results from game checks."""
    root = Path(eval_root)
    check_files = sorted(root.rglob("checks.json")) if root.exists() else []
    games_with_checks = 0
    leak_count = 0
    critical_leaks = 0
    examples: list[dict[str, Any]] = []

    for path in check_files:
        checks = _load_json_list(path)
        if checks is None:
            continue
        games_with_checks += 1
        for check in checks:
            if check.get("checker") != "InformationIsolationChecker":
                continue
            if check.get("passed", False):
                continue
            leak_count += 1
            if check.get("severity") == "critical":
                critical_leaks += 1
            if len(examples) < 5:
                examples.append(
                    {
                        "game_dir": str(path.parent),
                        "message": check.get("message", ""),
                        "data": check.get("data", {}),
                    }
                )

    status = "pass" if games_with_checks > 0 and leak_count == 0 else "needs_evidence"
    if leak_count > 0:
        status = "fail"

    return {
        "status": status,
        "games_with_checks": games_with_checks,
        "information_leak_count": leak_count,
        "critical_leak_count": critical_leaks,
        "checker": "InformationIsolationChecker",
        "evidence_files": [str(path) for path in check_files[:20]],
        "examples": examples,
    }


def summarize_evolution(evolution_root: str | Path | None) -> dict[str, Any]:
    """Summarize evolution-cycle evidence from an evolution output root."""
    if evolution_root is None:
        return {
            "status": "needs_evidence",
            "reason": "No evolution_root was provided.",
        }

    root = Path(evolution_root)
    summary_path = root / "evolution_summary.json"
    matrix_path = root / "evolution_matrix_summary.json"
    summary = _load_json_dict(summary_path) if summary_path.is_file() else {}
    matrix = _load_json_dict(matrix_path) if matrix_path.is_file() else {}

    rounds = summary.get("rounds") if isinstance(summary.get("rounds"), list) else []
    prompt_chain = (
        summary.get("prompt_version_chain")
        if isinstance(summary.get("prompt_version_chain"), list)
        else []
    )
    ab_report_path = summary.get("ab_report_path")
    ab_report = _load_json_dict(Path(str(ab_report_path))) if ab_report_path else {}

    versions = _collect_leaderboard_versions(root)
    first = versions[0] if versions else {}
    last = versions[-1] if versions else {}
    games_total = sum(int(v.get("games", 0) or 0) for v in versions)
    win_delta = _float(last.get("win_rate")) - _float(first.get("win_rate")) if versions else 0.0

    has_prompt_loop = any(item.get("prompt_version_changed") for item in prompt_chain)
    has_skill_manifests = any((Path(str(r.get("run_dir", ""))) / "version_manifest.json").is_file() for r in rounds)
    has_ab = bool(ab_report)
    significant = bool(ab_report.get("win_rate_significant")) if ab_report else False

    if rounds and has_ab and games_total >= 20 and significant and win_delta > 0:
        status = "strong"
    elif rounds and has_ab:
        status = "engineering_ready"
    else:
        status = "needs_evidence"

    return {
        "status": status,
        "round_count": len(rounds),
        "versions": versions,
        "games_total": games_total,
        "initial_version": first.get("version_id"),
        "final_version": last.get("version_id"),
        "win_rate_delta": win_delta,
        "has_prompt_loop": has_prompt_loop,
        "has_skill_version_manifests": has_skill_manifests,
        "has_ab_report": has_ab,
        "ab_report_path": ab_report_path,
        "win_rate_p_value": ab_report.get("win_rate_p_value"),
        "win_rate_significant": significant,
        "matrix_summary_path": str(matrix_path) if matrix else None,
    }


def summarize_rollback_candidates(evolution_root: str | Path | None) -> dict[str, Any]:
    """Report whether version manifests are enough to support rollback selection."""
    if evolution_root is None:
        return {"status": "needs_evidence", "version_count": 0, "versions": []}

    root = Path(evolution_root)
    manifests = sorted(root.rglob("version_manifest.json")) if root.exists() else []
    versions: list[dict[str, Any]] = []
    for path in manifests:
        payload = _load_json_dict(path)
        if not payload:
            continue
        active_skills = payload.get("active_skills")
        active_count = 0
        if isinstance(active_skills, dict):
            active_count = sum(len(items) for items in active_skills.values() if isinstance(items, list))
        versions.append(
            {
                "version_id": payload.get("version_id", path.parent.name),
                "manifest_path": str(path),
                "prompt_version": payload.get("prompt_version"),
                "active_skill_count": active_count,
                "has_model_config": isinstance(payload.get("model_config"), dict),
                "has_memory_runtime_params": isinstance(payload.get("memory_runtime_params"), dict),
            }
        )

    status = "ready" if versions else "needs_evidence"
    return {
        "status": status,
        "version_count": len(versions),
        "versions": versions,
    }


def _rubric_items(eval_root: Path, evolution_root: str | Path | None) -> list[dict[str, Any]]:
    isolation = summarize_information_isolation(eval_root)
    evolution = summarize_evolution(evolution_root)
    rollback = summarize_rollback_candidates(evolution_root)
    return [
        {
            "item": "单 Agent 能力",
            "status": "implemented",
            "evidence": [
                "agent_team/agents 提供角色 Agent 构建入口",
                "strategy/prompts 提供 prompt 版本",
                "agent_team/memory 与 skill_support 提供记忆和 skill 注入",
            ],
            "remaining_gap": "需要用更多真实对局证明各角色策略质量，而不只是机制存在。",
        },
        {
            "item": "多 Agent 协作与系统设计",
            "status": "implemented",
            "evidence": [
                "game_runtime 承担回合、夜间行动、发言、投票、胜负流转",
                "evaluation/core/checkers.py 覆盖角色动作、异步阶段、胜负一致性、信息隔离",
            ],
            "remaining_gap": "建议保留固定场景的 checks/report 作为答辩证据。",
        },
        {
            "item": "信息隔离",
            "status": isolation["status"],
            "evidence": [
                f"已汇总 {isolation['games_with_checks']} 局 checks.json",
                f"InformationIsolationChecker 泄漏数：{isolation['information_leak_count']}",
            ],
            "remaining_gap": "如果 games_with_checks 为 0，需要先跑 werewolf-eval 生成检查产物。",
        },
        {
            "item": "评测与复盘",
            "status": "implemented",
            "evidence": [
                "evaluation/post_game 生成赛后复盘、评分、skill/prompt 候选",
                "evaluation/leaderboard 生成排行榜和 A/B 显著性报告",
                "counterfactual_report.json/md 生成规则型反事实推演",
            ],
            "remaining_gap": "当前反事实是规则型关键行动分析，后续可升级为完整替代时间线模拟。",
        },
        {
            "item": "自进化闭环",
            "status": evolution["status"],
            "evidence": [
                f"evolution round 数：{evolution.get('round_count', 0)}",
                f"总局数：{evolution.get('games_total', 0)}",
                f"A/B 显著性：{evolution.get('win_rate_significant', False)}",
            ],
            "remaining_gap": "满分档需要初始版 vs 终局版 20 局以上且胜率显著提升的真实证据。",
        },
        {
            "item": "版本回溯",
            "status": rollback["status"],
            "evidence": [
                f"可读 version_manifest 数：{rollback['version_count']}",
                "manifest 包含 prompt_version、active_skills、memory_runtime_params、model_config",
            ],
            "remaining_gap": "如果要更强，可以再把恢复命令接成一键 CLI，而不只做候选/manifest。",
        },
        {
            "item": "Few-shot / 思维链",
            "status": "implemented",
            "evidence": [
                "strategy/prompts/v2/text/agent_base.md 包含显式 few-shot 示例",
                "复杂局面要求 private_thought 内部推理，public_speech 只给公开理由",
            ],
            "remaining_gap": "如果要更强，可以给每个角色单独补角色专属 few-shot。",
        },
        {
            "item": "文档完整度",
            "status": "implemented",
            "evidence": [
                "docs/ 下有架构、评测、记忆、报告文档",
                "CONTRIBUTING.md 补充贡献规则、命令和 review checklist",
            ],
            "remaining_gap": "英文 README 可作为后续加分项继续补。",
        },
    ]


def _score_estimate(*, exclude_frontend: bool) -> dict[str, Any]:
    return {
        "scope": "除前端" if exclude_frontend else "全项目",
        "estimated_total": "86-88/100" if exclude_frontend else "视前端完成度另计",
        "best_primary_track": "进阶 B：评测 + 复盘",
        "track_b_estimate": "88/100 左右",
        "track_c_estimate": "84-86/100",
        "note": "自进化工程闭环已具备，但满分档仍需要真实 20 局以上显著提升证据。",
    }


def _next_actions() -> list[str]:
    return [
        "固定 scenario/model/prompt/skill 参数，跑初始版 vs 终局版至少 20 局。",
        "保留 A/B 报告里的 p-value、Wilson CI、significant 字段作为自进化证据。",
        "把 InformationIsolationChecker 的 0 泄漏报告放进答辩材料。",
        "补一份反事实推演报告，说明关键投票或夜间行动如果改变会怎样。",
    ]


def _format_markdown(payload: dict[str, Any]) -> str:
    score = payload["score_estimate"]
    lines = [
        "# 评分标准对照证据包",
        "",
        f"- 评估范围：{score['scope']}",
        f"- 估分：{score['estimated_total']}",
        f"- 建议主打方向：{score['best_primary_track']}",
        f"- B 方向估分：{score['track_b_estimate']}",
        f"- C 方向估分：{score['track_c_estimate']}",
        f"- 说明：{score['note']}",
        "",
        "## 评分项对照",
        "",
        "| 评分项 | 状态 | 证据 | 剩余缺口 |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload["rubric_items"]:
        evidence = "<br>".join(str(x) for x in item.get("evidence", []))
        lines.append(
            f"| {item['item']} | `{item['status']}` | {evidence} | {item['remaining_gap']} |"
        )

    isolation = payload["information_isolation"]
    evolution = payload["evolution"]
    rollback = payload["rollback"]
    lines.extend(
        [
            "",
            "## 关键信号",
            "",
            f"- 信息隔离：`{isolation['status']}`，检查局数 `{isolation['games_with_checks']}`，泄漏 `{isolation['information_leak_count']}`。",
            f"- 自进化：`{evolution['status']}`，轮数 `{evolution.get('round_count', 0)}`，总局数 `{evolution.get('games_total', 0)}`，显著性 `{evolution.get('win_rate_significant', False)}`。",
            f"- 版本回溯：`{rollback['status']}`，可读版本 manifest `{rollback['version_count']}` 个。",
            "",
            "## 下一步",
            "",
        ]
    )
    lines.extend(f"- {action}" for action in payload["next_actions"])
    return "\n".join(lines) + "\n"


def _collect_leaderboard_versions(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("leaderboard_entry.json")):
        payload = _load_json_dict(path)
        if not payload:
            continue
        entries.append(
            {
                "version_id": payload.get("version_id", path.parent.name),
                "run_dir": str(path.parent),
                "games": int(payload.get("games", 0) or 0),
                "completed_games": int(payload.get("completed_games", 0) or 0),
                "completion_rate": _float(payload.get("completion_rate")),
                "win_rate": _float(payload.get("win_rate")),
                "prompt_version": payload.get("prompt_version"),
                "skill_version": payload.get("skill_version"),
            }
        )
    return entries


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_json_list(path: Path) -> list[dict[str, Any]] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, list):
        return None
    return [item for item in payload if isinstance(item, dict)]


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
