"""增强版 leaderboard 汇总产物：active skill 清单、版本摘要、evolution overview。

不修改核心聚合逻辑（aggregator.py），只做产物增强。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(val: Any, digits: int = 2) -> str:
    try:
        return f"{float(val):.{digits}f}"
    except (TypeError, ValueError):
        return str(val) if val is not None else "-"


def collect_active_skills(runs_root: Path) -> list[dict[str, Any]]:
    """收集所有 run 目录下 skills/ 中 status=active 的 skill 卡片。"""
    active: list[dict[str, Any]] = []
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        skills_dir = run_dir / "skills"
        if not skills_dir.is_dir():
            continue
        for md_path in sorted(skills_dir.rglob("*.md")):
            text = md_path.read_text(encoding="utf-8")
            # 简单解析 frontmatter
            if not text.startswith("---"):
                continue
            end = text.find("---", 3)
            if end == -1:
                continue
            fm_text = text[3:end].strip()
            meta: dict[str, str] = {}
            for line in fm_text.splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip()
            if meta.get("status") != "active":
                continue
            active.append({
                "skill_id": meta.get("skill_id", md_path.stem),
                "role": meta.get("prompt_role_key", ""),
                "weight": float(meta.get("weight", "1.0")),
                "when_to_use": meta.get("when_to_use", ""),
                "source_run": meta.get("source_run", run_dir.name),
                "path": str(md_path.relative_to(runs_root)),
            })
    return active


def write_active_skill_summary(runs_root: Path, output_dir: Path) -> Path:
    """生成 active skill 清单 markdown。"""
    skills = collect_active_skills(runs_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Active Skill 清单",
        "",
        f"共 {len(skills)} 张 active skill 卡片",
        "",
        "| skill_id | role | weight | when_to_use | source_run |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for s in skills:
        wtu = s["when_to_use"][:40] + "..." if len(s["when_to_use"]) > 40 else s["when_to_use"]
        lines.append(f"| {s['skill_id']} | {s['role']} | {_fmt(s['weight'])} | {wtu} | {s['source_run']} |")

    path = output_dir / "active_skills.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_version_summaries(runs_root: Path, output_dir: Path) -> Path:
    """为每个 run 生成版本摘要 markdown。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries_dir = output_dir / "version_summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)

    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        entry_path = run_dir / "leaderboard_entry.json"
        meta_path = run_dir / "experiment_meta.json"
        snapshot_path = run_dir / "skill_snapshot.json"
        diff_path = run_dir / "skill_diff.json"

        lines = [f"# 版本摘要: {run_dir.name}", ""]

        # Leaderboard entry 信息
        if entry_path.is_file():
            entry = _load_json(entry_path)
            lines.extend([
                "## 基本信息",
                "",
                f"- 模型: {entry.get('model', 'unknown')}",
                f"- Prompt 版本: {entry.get('prompt_version', 'unknown')}",
                f"- Skill 版本: {entry.get('skill_version', 'baseline')}",
                f"- 游戏局数: {entry.get('games', 0)}",
                f"- 完成率: {_fmt(entry.get('completion_rate'))}",
                f"- 胜率: {_fmt(entry.get('win_rate'))}",
                f"- 平均 MVP 分: {_fmt(entry.get('avg_mvp_score'))}",
                f"- 平均收益分: {_fmt(entry.get('avg_benefit_score'))}",
                f"- 平均意图分: {_fmt(entry.get('avg_intention_score'))}",
                "",
            ])
        else:
            lines.extend(["## 基本信息", "", "（无 leaderboard_entry.json）", ""])

        # Experiment meta
        if meta_path.is_file():
            meta = _load_json(meta_path)
            prev = meta.get("previous_run_dir")
            if prev:
                lines.extend(["## 版本链", "", f"- 上一版: {prev}", ""])

        # Skill snapshot
        if snapshot_path.is_file():
            snapshot = _load_json(snapshot_path)
            skills = snapshot.get("skills", {})
            lines.extend([
                "## Skill 快照",
                "",
                f"- 共 {len(skills)} 张卡片",
                "",
            ])
            for sid, info in sorted(skills.items()):
                lines.append(f"  - `{sid}`: weight={_fmt(info.get('weight', 0))}, status={info.get('status', '?')}")

        # Skill diff
        if diff_path.is_file():
            diff = _load_json(diff_path)
            added = diff.get("added", [])
            removed = diff.get("removed", [])
            changed = diff.get("changed", [])
            if added or removed or changed:
                lines.extend(["## Skill 变更", ""])
                for s in added:
                    lines.append(f"  - [新增] {s.get('skill_id', '?')}")
                for s in removed:
                    lines.append(f"  - [移除] {s.get('skill_id', '?')}")
                for s in changed:
                    lines.append(f"  - [变更] {s.get('skill_id', '?')}")

        md_path = summaries_dir / f"{run_dir.name}.md"
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return summaries_dir


def write_evolution_overview(runs_root: Path, output_dir: Path) -> Path:
    """生成 evolution overview：跨版本趋势总览。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        entry_path = run_dir / "leaderboard_entry.json"
        if entry_path.is_file():
            entry = _load_json(entry_path)
            entry["_run_name"] = run_dir.name
            entries.append(entry)

    lines = [
        "# Evolution Overview",
        "",
        f"共 {len(entries)} 个版本",
        "",
        "## 胜率趋势",
        "",
        "| 版本 | 模型 | prompt | skill | 胜率 | MVP | 收益 | 意图 |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for e in entries:
        lines.append(
            f"| {e.get('_run_name', e.get('version_id', '?'))} | "
            f"{e.get('model', '?')} | {e.get('prompt_version', '?')} | "
            f"{e.get('skill_version', '?')} | {_fmt(e.get('win_rate'))} | "
            f"{_fmt(e.get('avg_mvp_score'))} | {_fmt(e.get('avg_benefit_score'))} | "
            f"{_fmt(e.get('avg_intention_score'))} |"
        )

    # 版本链
    lines.extend(["", "## 版本链", ""])
    for run_dir in sorted(runs_root.iterdir()):
        meta_path = run_dir / "experiment_meta.json"
        if meta_path.is_file():
            meta = _load_json(meta_path)
            prev = meta.get("previous_run_dir", "（无）")
            lines.append(f"- {run_dir.name} ← {prev}")

    path = output_dir / "evolution_overview.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
