#!/usr/bin/env python3
"""扫描历史 run 目录，补生成缺失的 leaderboard_entry.json 和 experiment_meta.json。

用法：
    python scripts/backfill_run_artifacts.py [--dry-run] [--runs-dir artifacts/runs]

输出：
    - 对每个 run 补写 leaderboard_entry.json 和 experiment_meta.json
    - 在 runs 目录下生成 backfill_report.md 清单
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 项目根目录
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from llm_werewolf.evaluation.leaderboard.entry_builder import (
    build_experiment_meta,
    infer_previous_run_dir,
    write_experiment_meta,
)
from llm_werewolf.evaluation.leaderboard.models import LeaderboardEntry


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _extract_model(manifest: dict[str, Any]) -> str:
    """从 manifest 的 roster 中提取使用的模型名。"""
    roster = manifest.get("context", {}).get("roster", {})
    models: set[str] = set()
    for player in roster.values():
        model = player.get("model") or player.get("ai_model") or ""
        if model and model != "human" and model != "demo":
            models.add(model)
    if len(models) == 1:
        return models.pop()
    if models:
        return "+".join(sorted(models))
    return "unknown"


def _count_games_from_events(events_path: Path) -> int:
    """从 events.jsonl 推断游戏局数（通过 GAME_STARTED 事件计数）。"""
    if not events_path.is_file():
        return 0
    count = 0
    for line in events_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
            if evt.get("event_type") in ("GAME_STARTED", "game_started"):
                count += 1
        except json.JSONDecodeError:
            continue
    return max(count, 1)  # 至少算 1 局


def _extract_winner_camp(manifest: dict[str, Any]) -> str | None:
    ctx = manifest.get("context", {})
    winner = ctx.get("winner_camp", "")
    return winner if winner else None


def _classify_run(run_dir: Path) -> tuple[str, list[str]]:
    """分类 run 目录：(status, reasons)。

    status: "usable" | "partial" | "deprecated"
    """
    reasons: list[str] = []
    manifest_path = run_dir / "post_game_manifest.json"
    events_path = run_dir / "events.jsonl"
    analysis_path = run_dir / "post_game_analysis.json"

    if not manifest_path.is_file():
        return "deprecated", ["缺少 post_game_manifest.json"]

    manifest = _load_json(manifest_path)

    # 检查是否有实际游戏数据
    games = manifest.get("games", [])
    if not games and not events_path.is_file():
        return "deprecated", ["无 games 数据且无 events.jsonl"]

    # 检查 PostGame 分析状态
    if analysis_path.is_file():
        analysis = _load_json(analysis_path)
        if analysis.get("mode") == "failed":
            reasons.append("PostGame 分析失败（LLM 复盘 404）")

    # 检查关键产物
    has_benefit = (run_dir / "benefit_scores.json").is_file()
    has_intention = (run_dir / "intention_scores.json").is_file()
    has_skills = (run_dir / "role_skills.json").is_file()
    has_camp = (run_dir / "camp_persuasion_summary.json").is_file()

    missing = []
    if not has_benefit:
        missing.append("benefit_scores.json")
    if not has_intention:
        missing.append("intention_scores.json")
    if not has_skills:
        missing.append("role_skills.json")
    if not has_camp:
        missing.append("camp_persuasion_summary.json")

    if missing:
        reasons.append(f"缺少产物: {', '.join(missing)}")

    if len(missing) >= 3:
        return "deprecated", reasons + ["关键产物缺失过多"]
    if missing or reasons:
        return "partial", reasons
    return "usable", ["所有关键产物齐全"]


def _build_leaderboard_entry_from_manifest(
    run_dir: Path,
) -> LeaderboardEntry | None:
    """从 manifest 和可用产物构建 LeaderboardEntry（尽力而为）。"""
    manifest_path = run_dir / "post_game_manifest.json"
    if not manifest_path.is_file():
        return None

    manifest = _load_json(manifest_path)
    ctx = manifest.get("context", {})

    # 提取基本信息
    model = _extract_model(manifest)
    prompt_version = ctx.get("prompt_version", "unknown")
    winner_camp = _extract_winner_camp(manifest)
    events_path = run_dir / "events.jsonl"
    total_games = _count_games_from_events(events_path)

    # 提取评分（如果存在）
    avg_benefit = 0.0
    if (run_dir / "benefit_scores.json").is_file():
        try:
            scores = _load_json(run_dir / "benefit_scores.json")
            if isinstance(scores, list) and scores:
                avg_benefit = sum(_safe_float(s.get("total_score", s.get("score", 0))) for s in scores) / len(scores)
            elif isinstance(scores, dict):
                avg_benefit = _safe_float(scores.get("avg_score", scores.get("total_score", 0)))
        except Exception:
            pass

    avg_intention = 0.0
    if (run_dir / "intention_scores.json").is_file():
        try:
            scores = _load_json(run_dir / "intention_scores.json")
            if isinstance(scores, list) and scores:
                avg_intention = sum(_safe_float(s.get("avg_score", s.get("score", 0))) for s in scores) / len(scores)
            elif isinstance(scores, dict):
                avg_intention = _safe_float(scores.get("avg_score", 0))
        except Exception:
            pass

    # MVP（如果有）
    avg_mvp = 0.0
    if (run_dir / "mvp_scores.json").is_file():
        try:
            scores = _load_json(run_dir / "mvp_scores.json")
            if isinstance(scores, list) and scores:
                avg_mvp = sum(_safe_float(s.get("mvp_score", s.get("score", 0))) for s in scores) / len(scores)
        except Exception:
            pass

    win_rate = 1.0 if winner_camp else 0.0

    entry = LeaderboardEntry(
        schema="leaderboard_entry_v1",
        version_id=run_dir.name,
        model=model,
        prompt_version=prompt_version,
        skill_version="baseline",
        scenario="unknown",
        games=total_games,
        completed_games=total_games,
        completion_rate=1.0,
        win_rate=win_rate,
        avg_rounds=0.0,
        avg_mvp_score=avg_mvp,
        avg_benefit_score=avg_benefit,
        avg_intention_score=avg_intention,
        information_leak_count=0,
        phase_order_violation_count=0,
        role_skill_violation_count=0,
        top_errors=[],
        source_run_dir=str(run_dir),
        notes=["backfilled from legacy run"],
    )
    return entry


def _write_entry(run_dir: Path, entry: LeaderboardEntry) -> Path:
    path = run_dir / "leaderboard_entry.json"
    path.write_text(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def backfill_run(
    run_dir: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """处理单个 run 目录，返回结果字典。"""
    status, reasons = _classify_run(run_dir)
    result: dict[str, Any] = {
        "run_dir": run_dir.name,
        "status": status,
        "reasons": reasons,
        "actions": [],
    }

    # 补 leaderboard_entry.json
    entry_path = run_dir / "leaderboard_entry.json"
    if not entry_path.is_file():
        entry = _build_leaderboard_entry_from_manifest(run_dir)
        if entry is not None:
            result["actions"].append("生成 leaderboard_entry.json")
            if not dry_run:
                _write_entry(run_dir, entry)
        else:
            result["actions"].append("无法构建 leaderboard_entry（数据不足）")

    # 补 experiment_meta.json
    meta_path = run_dir / "experiment_meta.json"
    if not meta_path.is_file():
        previous = infer_previous_run_dir(run_dir)
        result["actions"].append(f"生成 experiment_meta.json (previous={previous})")
        if not dry_run:
            write_experiment_meta(
                run_dir,
                version_id=run_dir.name,
                model="unknown",
                prompt_version="unknown",
                skill_version="baseline",
                notes=["backfilled"],
                previous_run_dir=previous,
            )

    return result


def generate_report(results: list[dict[str, Any]], output_path: Path) -> None:
    """生成 backfill_report.md。"""
    usable = [r for r in results if r["status"] == "usable"]
    partial = [r for r in results if r["status"] == "partial"]
    deprecated = [r for r in results if r["status"] == "deprecated"]

    lines = [
        "# 历史 Run 补全报告",
        "",
        f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## 概览",
        "",
        f"- [OK] 可直接纳入版本链: {len(usable)}",
        f"- [!!] 只能部分利用: {len(partial)}",
        f"- [--] 建议废弃: {len(deprecated)}",
        f"- 总计: {len(results)}",
        "",
    ]

    def _section(title: str, items: list[dict[str, Any]]) -> None:
        lines.append(f"## {title}")
        lines.append("")
        if not items:
            lines.append("(无)")
            lines.append("")
            return
        for r in items:
            lines.append(f"### {r['run_dir']}")
            for reason in r["reasons"]:
                lines.append(f"- {reason}")
            for action in r["actions"]:
                lines.append(f"- [done] {action}")
            lines.append("")

    _section("[OK] 可直接纳入版本链", usable)
    _section("[!!] 只能部分利用", partial)
    _section("[--] 建议废弃", deprecated)

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="补全历史 run 的 leaderboard 元数据")
    parser.add_argument("--runs-dir", type=Path, default=Path("artifacts/runs"))
    parser.add_argument("--dry-run", action="store_true", help="只分析不写入")
    args = parser.parse_args()

    runs_dir = args.runs_dir.resolve()
    if not runs_dir.is_dir():
        print(f"目录不存在: {runs_dir}")
        return

    run_dirs = sorted(
        [d for d in runs_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )
    print(f"扫描到 {len(run_dirs)} 个 run 目录")

    results: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        result = backfill_run(run_dir, dry_run=args.dry_run)
        results.append(result)
        icon = {"usable": "[OK]", "partial": "[!!]", "deprecated": "[--]"}[result["status"]]
        print(f"  {icon} {result['run_dir']}: {result['status']}")

    report_path = runs_dir / "backfill_report.md"
    generate_report(results, report_path)
    print(f"\n报告已写入: {report_path}")

    if args.dry_run:
        print("(dry-run 模式，未写入任何文件)")


if __name__ == "__main__":
    main()
