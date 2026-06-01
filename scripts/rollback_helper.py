#!/usr/bin/env python3
"""回滚辅助脚本：列出可回滚版本，读取某版本的 active skill 集，生成回滚候选说明。

用法：
    python scripts/rollback_helper.py list [--runs-dir artifacts/runs]
    python scripts/rollback_helper.py show <version_id> [--runs-dir artifacts/runs]
    python scripts/rollback_helper.py candidate <target_version_id> [--runs-dir artifacts/runs]

不修改主版本切换逻辑，只做信息查询和候选生成。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _reconfigure_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass


def list_versions(runs_root: Path) -> list[dict[str, Any]]:
    """列出所有可回滚版本及其关键信息。"""
    versions: list[dict[str, Any]] = []
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        entry_path = run_dir / "leaderboard_entry.json"
        meta_path = run_dir / "experiment_meta.json"
        snapshot_path = run_dir / "skill_snapshot.json"

        if not entry_path.is_file():
            continue

        entry = _load_json(entry_path)
        meta = _load_json(meta_path) if meta_path.is_file() else {}

        active_count = 0
        total_count = 0
        if snapshot_path.is_file():
            snapshot = _load_json(snapshot_path)
            skills = snapshot.get("skills", {})
            total_count = len(skills)
            active_count = sum(1 for s in skills.values() if s.get("status") == "active")

        versions.append({
            "version_id": entry.get("version_id", run_dir.name),
            "run_dir": run_dir.name,
            "model": entry.get("model", "unknown"),
            "prompt_version": entry.get("prompt_version", "unknown"),
            "skill_version": entry.get("skill_version", "baseline"),
            "win_rate": entry.get("win_rate", 0.0),
            "games": entry.get("games", 0),
            "active_skill_count": active_count,
            "total_skill_count": total_count,
            "previous_run_dir": meta.get("previous_run_dir"),
        })
    return versions


def show_version(runs_root: Path, version_id: str) -> dict[str, Any] | None:
    """显示某个版本的详细信息，包括 active skill 集。"""
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        entry_path = run_dir / "leaderboard_entry.json"
        if not entry_path.is_file():
            continue
        entry = _load_json(entry_path)
        if entry.get("version_id") != version_id and run_dir.name != version_id:
            continue

        result: dict[str, Any] = {
            "version_id": entry.get("version_id", run_dir.name),
            "run_dir": str(run_dir),
            "leaderboard_entry": entry,
        }

        meta_path = run_dir / "experiment_meta.json"
        if meta_path.is_file():
            result["experiment_meta"] = _load_json(meta_path)

        snapshot_path = run_dir / "skill_snapshot.json"
        if snapshot_path.is_file():
            snapshot = _load_json(snapshot_path)
            skills = snapshot.get("skills", {})
            result["active_skills"] = {
                sid: info for sid, info in skills.items()
                if info.get("status") == "active"
            }
            result["all_skills"] = skills

        return result
    return None


def generate_rollback_candidate(
    runs_root: Path, target_version_id: str
) -> dict[str, Any] | None:
    """生成回滚候选说明：回滚到目标版本后，哪些 skill 会被恢复/替换。"""
    target = show_version(runs_root, target_version_id)
    if target is None:
        return None

    # 找当前最新版本
    versions = list_versions(runs_root)
    if not versions:
        return None
    current = versions[-1]

    current_detail = show_version(runs_root, current["version_id"])
    if current_detail is None:
        return None

    target_skills = target.get("active_skills", {})
    current_skills = current_detail.get("active_skills", {})

    target_ids = set(target_skills.keys())
    current_ids = set(current_skills.keys())

    restored = target_ids - current_ids
    removed = current_ids - target_ids
    kept = target_ids & current_ids

    # 权重变更
    weight_changes: list[dict[str, Any]] = []
    for sid in kept:
        tw = target_skills[sid].get("weight", 0)
        cw = current_skills[sid].get("weight", 0)
        if abs(tw - cw) > 0.01:
            weight_changes.append({
                "skill_id": sid,
                "current_weight": cw,
                "target_weight": tw,
            })

    return {
        "target_version": target_version_id,
        "current_version": current["version_id"],
        "summary": {
            "restored_count": len(restored),
            "removed_count": len(removed),
            "kept_count": len(kept),
            "weight_changed_count": len(weight_changes),
        },
        "restored_skills": sorted(restored),
        "removed_skills": sorted(removed),
        "weight_changes": weight_changes,
        "target_snapshot_path": str(Path(target["run_dir"]) / "skill_snapshot.json"),
    }


def cmd_list(args: argparse.Namespace) -> None:
    versions = list_versions(args.runs_dir)
    if not versions:
        print("无可回滚版本")
        return
    print(f"共 {len(versions)} 个可回滚版本:\n")
    for v in versions:
        prev = v["previous_run_dir"] or "（无）"
        print(
            f"  {v['version_id']:30s}  win={v['win_rate']:.2f}  "
            f"skills={v['active_skill_count']}/{v['total_skill_count']}  "
            f"prev={prev}"
        )


def cmd_show(args: argparse.Namespace) -> None:
    result = show_version(args.runs_dir, args.version_id)
    if result is None:
        print(f"未找到版本: {args.version_id}")
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_candidate(args: argparse.Namespace) -> None:
    result = generate_rollback_candidate(args.runs_dir, args.version_id)
    if result is None:
        print(f"未找到版本: {args.version_id}")
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    _reconfigure_stdout()

    parser = argparse.ArgumentParser(description="回滚辅助工具")
    parser.add_argument("--runs-dir", type=Path, default=Path("artifacts/runs"))
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="列出可回滚版本")

    show_p = sub.add_parser("show", help="显示某版本详情")
    show_p.add_argument("version_id", help="版本 ID 或 run 目录名")

    cand_p = sub.add_parser("candidate", help="生成回滚候选说明")
    cand_p.add_argument("version_id", help="目标回滚版本 ID")

    args = parser.parse_args()
    if args.command == "list":
        cmd_list(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "candidate":
        cmd_candidate(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
