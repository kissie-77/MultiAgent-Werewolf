"""增强版 leaderboard 汇总产物：active skill 清单、版本摘要、evolution overview。

不修改核心聚合逻辑（aggregator.py），只做产物增强。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from llm_werewolf.agent_team.skill_support.skill_markdown import parse_frontmatter

if TYPE_CHECKING:
    from pathlib import Path


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
            meta, _body = parse_frontmatter(text)
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
    """生成 active skill 清单 markdown + json。"""
    skills = collect_active_skills(runs_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON 产物
    json_payload = {
        "schema": "active_skills_v1",
        "total": len(skills),
        "skills": skills,
    }
    json_path = output_dir / "active_skills.json"
    json_path.write_text(
        json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdown 产物
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

    md_path = output_dir / "active_skills.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path


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


def write_version_manifest(run_dir: Path) -> Path | None:
    """为单个 run 目录生成 version_manifest.json。

    汇总该版本的关键元数据，方便快速了解"这一轮是什么配置"。
    """
    entry_path = run_dir / "leaderboard_entry.json"
    meta_path = run_dir / "experiment_meta.json"
    snapshot_path = run_dir / "skill_snapshot.json"
    manifest_path = run_dir / "post_game_manifest.json"

    if not entry_path.is_file():
        return None

    entry = _load_json(entry_path)
    meta = _load_json(meta_path) if meta_path.is_file() else {}

    # 统计 active skill 数量
    active_skill_count = 0
    if snapshot_path.is_file():
        snapshot = _load_json(snapshot_path)
        active_skill_count = sum(
            1 for s in snapshot.get("skills", {}).values()
            if s.get("status") == "active"
        )

    # 从 post_game_manifest 提取场景信息
    scenario = entry.get("scenario", "unknown")
    games = entry.get("games", 0)

    payload = {
        "schema": "version_manifest_v1",
        "version_id": entry.get("version_id", run_dir.name),
        "previous_run_dir": meta.get("previous_run_dir"),
        "prompt_version": entry.get("prompt_version", "unknown"),
        "skill_version": entry.get("skill_version", "baseline"),
        "model": entry.get("model", "unknown"),
        "active_skill_count": active_skill_count,
        "scenario": scenario,
        "games": games,
        "completion_rate": entry.get("completion_rate", 0.0),
        "win_rate": entry.get("win_rate", 0.0),
        "avg_mvp_score": entry.get("avg_mvp_score", 0.0),
        "avg_benefit_score": entry.get("avg_benefit_score", 0.0),
        "avg_intention_score": entry.get("avg_intention_score", 0.0),
    }

    out_path = run_dir / "version_manifest.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def write_all_version_manifests(runs_root: Path) -> list[Path]:
    """为所有 run 目录生成 version_manifest.json。"""
    paths: list[Path] = []
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        p = write_version_manifest(run_dir)
        if p is not None:
            paths.append(p)
    return paths


def _collect_version_data(runs_root: Path) -> list[dict[str, Any]]:
    """收集所有 run 的版本数据（从 version_manifest 或 leaderboard_entry）。"""
    versions: list[dict[str, Any]] = []
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        vm_path = run_dir / "version_manifest.json"
        if vm_path.is_file():
            versions.append(_load_json(vm_path))
        else:
            entry_path = run_dir / "leaderboard_entry.json"
            if entry_path.is_file():
                versions.append(_load_json(entry_path))
    return versions


def write_evolution_summary(runs_root: Path, output_dir: Path) -> Path:
    """生成 evolution_summary.md：多轮进化总览报告。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    versions = _collect_version_data(runs_root)

    lines = [
        "# Evolution Summary",
        "",
        f"共 {len(versions)} 个版本",
        "",
    ]

    if not versions:
        lines.append("（无版本数据）")
    else:
        # 表格
        lines.extend([
            "## 版本列表",
            "",
            "| 版本 | 模型 | prompt | skill | 场景 | 局数 | 胜率 | 完成率 | MVP | 收益 | 意图 | active skills |",
            "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for v in versions:
            lines.append(
                f"| {v.get('version_id', '?')} | {v.get('model', '?')} | "
                f"{v.get('prompt_version', '?')} | {v.get('skill_version', '?')} | "
                f"{v.get('scenario', '?')} | {v.get('games', 0)} | "
                f"{_fmt(v.get('win_rate'))} | {_fmt(v.get('completion_rate'))} | "
                f"{_fmt(v.get('avg_mvp_score'))} | {_fmt(v.get('avg_benefit_score'))} | "
                f"{_fmt(v.get('avg_intention_score'))} | {v.get('active_skill_count', '?')} |"
            )

        # 初始版 vs 终局版结论
        first = versions[0]
        last = versions[-1]
        lines.extend([
            "",
            "## 初始版 vs 终局版",
            "",
            f"| 指标 | 初始版 ({first.get('version_id', '?')}) | 终局版 ({last.get('version_id', '?')}) | 变化 |",
            "| --- | ---: | ---: | ---: |",
        ])
        for metric, label in [
            ("win_rate", "胜率"),
            ("completion_rate", "完成率"),
            ("avg_mvp_score", "MVP"),
            ("avg_benefit_score", "收益"),
            ("avg_intention_score", "意图"),
            ("active_skill_count", "active skills"),
        ]:
            fv = first.get(metric, 0)
            lv = last.get(metric, 0)
            try:
                delta = float(lv) - float(fv)
                sign = "+" if delta > 0 else ""
                delta_str = f"{sign}{_fmt(delta)}"
            except (TypeError, ValueError):
                delta_str = "-"
            lines.append(f"| {label} | {_fmt(fv)} | {_fmt(lv)} | {delta_str} |")

    path = output_dir / "evolution_summary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_evolution_trend(runs_root: Path, output_dir: Path) -> tuple[Path, Path]:
    """生成 evolution_trend.json + evolution_trend.md。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    versions = _collect_version_data(runs_root)

    # JSON 产物
    trend_data = {
        "schema": "evolution_trend_v1",
        "total_versions": len(versions),
        "versions": [
            {
                "version_id": v.get("version_id", "?"),
                "win_rate": v.get("win_rate", 0.0),
                "completion_rate": v.get("completion_rate", 0.0),
                "avg_mvp_score": v.get("avg_mvp_score", 0.0),
                "avg_benefit_score": v.get("avg_benefit_score", 0.0),
                "avg_intention_score": v.get("avg_intention_score", 0.0),
                "active_skill_count": v.get("active_skill_count", 0),
                "games": v.get("games", 0),
            }
            for v in versions
        ],
    }
    json_path = output_dir / "evolution_trend.json"
    json_path.write_text(
        json.dumps(trend_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdown 产物
    lines = [
        "# Evolution Trend",
        "",
        "## 胜率趋势",
        "",
        "| 版本 | 胜率 | 完成率 | MVP | 收益 | 意图 | active skills |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for v in trend_data["versions"]:
        lines.append(
            f"| {v['version_id']} | {_fmt(v['win_rate'])} | {_fmt(v['completion_rate'])} | "
            f"{_fmt(v['avg_mvp_score'])} | {_fmt(v['avg_benefit_score'])} | "
            f"{_fmt(v['avg_intention_score'])} | {v['active_skill_count']} |"
        )

    # 趋势判断
    if len(versions) >= 2:
        first_wr = versions[0].get("win_rate", 0)
        last_wr = versions[-1].get("win_rate", 0)
        try:
            if float(last_wr) > float(first_wr) + 0.05:
                lines.extend(["", "**趋势：胜率显著提升**"])
            elif float(last_wr) < float(first_wr) - 0.05:
                lines.extend(["", "**趋势：胜率下降**"])
            else:
                lines.extend(["", "**趋势：胜率基本持平**"])
        except (TypeError, ValueError):
            pass

    md_path = output_dir / "evolution_trend.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return json_path, md_path
