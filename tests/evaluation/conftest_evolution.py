"""多轮 evolution fixture：模拟 3 轮版本迭代的完整产物。

用于测试 version chain / leaderboard / A-B 对比 / skill diff。
"""

from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _make_events(winner_camp: str = "werewolf") -> list[dict]:
    return [
        {
            "event_type": "GAME_STARTED",
            "round_number": 0,
            "phase": "setup",
            "message": "游戏开始",
            "data": {},
            "visible_to": None,
        },
        {
            "event_type": "WEREWOLF_KILLED",
            "round_number": 1,
            "phase": "night",
            "message": "狼人击杀了玩家5",
            "data": {"target_id": "player_5"},
            "visible_to": ["player_1", "player_4"],
        },
        {
            "event_type": "PLAYER_DIED",
            "round_number": 1,
            "phase": "day",
            "message": "玩家5死亡",
            "data": {"player_id": "player_5", "role": "Seer"},
            "visible_to": None,
        },
        {
            "event_type": "VOTE_RESULT",
            "round_number": 1,
            "phase": "day_voting",
            "message": "投票结果：玩家3被淘汰",
            "data": {"executed": "player_3", "votes": {"player_3": ["player_1", "player_4", "player_7"]}},
            "visible_to": None,
        },
        {
            "event_type": "GAME_ENDED",
            "round_number": 2,
            "phase": "ended",
            "message": f"{winner_camp}阵营获胜",
            "data": {"winner_camp": winner_camp},
            "visible_to": None,
        },
    ]


def _make_manifest(run_dir_name: str, winner_camp: str = "werewolf") -> dict:
    return {
        "context": {
            "run_dir": f"runs/{run_dir_name}",
            "prompt_version": "v2",
            "winner_camp": winner_camp,
            "winner_ids": ["player_1", "player_4", "player_7"],
            "roster": {
                "player_1": {"player_id": "player_1", "role_name": "Werewolf", "camp": "werewolf"},
                "player_4": {"player_id": "player_4", "role_name": "Werewolf", "camp": "werewolf"},
                "player_7": {"player_id": "player_7", "role_name": "Werewolf", "camp": "werewolf"},
                "player_2": {"player_id": "player_2", "role_name": "Villager", "camp": "villager"},
                "player_3": {"player_id": "player_3", "role_name": "Villager", "camp": "villager"},
                "player_5": {"player_id": "player_5", "role_name": "Seer", "camp": "villager"},
            },
        },
        "steps": {"completed": ["episodic", "scoring", "skill_extraction"], "failed": []},
    }


def _make_summary() -> dict:
    return {
        "total_games": 5,
        "completed_games": 5,
        "completion_rate": 1.0,
        "avg_rounds_per_game": 4.2,
        "information_leak_count": 0,
        "phase_order_violation_count": 0,
        "role_skill_violation_count": 0,
        "top_errors": [],
    }


def _make_skill_snapshot(version: int, *, weight_delta: float = 0.0) -> dict:
    """生成 skill 快照，weight 随版本递增模拟进化。"""
    base_weight = 1.0 + weight_delta
    return {
        "schema": "skill_snapshot_v1",
        "version": version,
        "skills": {
            "wolf_r1_night_knife_align": {
                "skill_id": "wolf_r1_night_knife_align",
                "role": "wolf",
                "description": "首夜统一刀口",
                "weight": round(base_weight + 0.1, 2),
                "status": "active",
            },
            "wolf_r2_suspicion_chain_push": {
                "skill_id": "wolf_r2_suspicion_chain_push",
                "role": "wolf",
                "description": "白天归票推动",
                "weight": round(base_weight, 2),
                "status": "active",
            },
            "prophet_night_r2_check": {
                "skill_id": "prophet_night_r2_check",
                "role": "prophet",
                "description": "第2轮查验决策",
                "weight": round(base_weight - 0.05, 2),
                "status": "draft",
            },
        },
    }


def _make_skill_diff(prev_version: int, curr_version: int) -> dict:
    """生成 skill diff：模拟新增/变更。"""
    added = []
    changed = []
    if curr_version >= 2:
        added.append({
            "skill_id": "guard_night_r1_protect",
            "role": "guard",
            "description": "首夜守护决策",
            "weight": 1.0,
            "status": "draft",
        })
    if curr_version >= 3:
        changed.append({
            "skill_id": "wolf_r1_night_knife_align",
            "old_weight": 1.1,
            "new_weight": 1.2,
            "old_status": "active",
            "new_status": "active",
        })
    return {
        "schema": "skill_diff_v1",
        "previous_version": prev_version,
        "current_version": curr_version,
        "added": added,
        "removed": [],
        "changed": changed,
    }


def _make_leaderboard_entry(
    version_id: str,
    *,
    win_rate: float = 0.6,
    mvp: float = 0.0,
    benefit: float = 0.0,
    intention: float = 0.0,
    model: str = "deepseek-v3",
    prompt_version: str = "v2",
    skill_version: str = "baseline",
) -> dict:
    return {
        "schema": "leaderboard_entry_v1",
        "version_id": version_id,
        "model": model,
        "prompt_version": prompt_version,
        "skill_version": skill_version,
        "scenario": "6p-standard",
        "games": 5,
        "completed_games": 5,
        "completion_rate": 1.0,
        "win_rate": win_rate,
        "avg_rounds": 4.2,
        "avg_mvp_score": mvp,
        "avg_benefit_score": benefit,
        "avg_intention_score": intention,
        "information_leak_count": 0,
        "phase_order_violation_count": 0,
        "role_skill_violation_count": 0,
        "top_errors": [],
        "source_run_dir": f"runs/{version_id}",
        "notes": [],
    }


def _make_experiment_meta(
    run_dir: str,
    *,
    version_id: str | None = None,
    previous_run_dir: str | None = None,
) -> dict:
    return {
        "schema": "experiment_meta_v1",
        "run_dir": run_dir,
        "version_id": version_id or run_dir.split("/")[-1],
        "model": "deepseek-v3",
        "prompt_version": "v2",
        "skill_version": "baseline",
        "scenario": "6p-standard",
        "notes": [],
        "previous_run_dir": previous_run_dir,
        "previous_skill_snapshot_path": None,
    }


def build_evolution_fixtures(root: Path) -> list[Path]:
    """构建 3 轮 evolution fixture，返回 3 个 run 目录路径。

    轮次设计：
    - v1: baseline，win_rate=0.6，初始 skill
    - v2: skill 进化（新增 guard skill），win_rate=0.7
    - v3: skill 进化（wolf skill 权重上升），win_rate=0.8
    """
    run_dirs: list[Path] = []
    versions = ["v1-baseline", "v2-skill-evolved", "v3-skill-matured"]
    win_rates = [0.6, 0.7, 0.8]
    weight_deltas = [0.0, 0.1, 0.2]
    prev_dirs: list[str | None] = [None, "v1-baseline", "v2-skill-evolved"]

    for i, (name, wr, wd, prev) in enumerate(zip(versions, win_rates, weight_deltas, prev_dirs)):
        run_dir = root / name
        run_dir.mkdir(parents=True, exist_ok=True)

        # events.jsonl
        events = _make_events("werewolf" if wr >= 0.5 else "villager")
        (run_dir / "events.jsonl").write_text(
            "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
            encoding="utf-8",
        )

        # manifest
        _write_json(run_dir / "post_game_manifest.json", _make_manifest(name))

        # summary
        _write_json(run_dir / "summary.json", _make_summary())

        # leaderboard_entry
        _write_json(
            run_dir / "leaderboard_entry.json",
            _make_leaderboard_entry(
                name,
                win_rate=wr,
                skill_version=f"v{i+1}",
            ),
        )

        # experiment_meta
        _write_json(
            run_dir / "experiment_meta.json",
            _make_experiment_meta(
                f"runs/{name}",
                version_id=name,
                previous_run_dir=prev,
            ),
        )

        # skill_snapshot
        _write_json(run_dir / "skill_snapshot.json", _make_skill_snapshot(i + 1, weight_delta=wd))

        # skill_diff
        if i > 0:
            _write_json(run_dir / "skill_diff.json", _make_skill_diff(i, i + 1))
        else:
            _write_json(run_dir / "skill_diff.json", {"schema": "skill_diff_v1", "added": [], "removed": [], "changed": []})

        # benefit_scores
        _write_json(run_dir / "benefit_scores.json", [
            {"player_id": "player_1", "total_score": 8.5 + i},
            {"player_id": "player_4", "total_score": 7.0 + i},
        ])

        # intention_scores
        _write_json(run_dir / "intention_scores.json", [
            {"player_id": "player_1", "avg_score": 0.7 + i * 0.1},
            {"player_id": "player_4", "avg_score": 0.6 + i * 0.1},
        ])

        # skill MD files (in skills/ subdirectory)
        skills_dir = run_dir / "skills"
        skills_dir.mkdir(exist_ok=True)
        snapshot = _make_skill_snapshot(i + 1, weight_delta=wd)
        for skill_id, info in snapshot["skills"].items():
            md_content = (
                f"---\n"
                f"skill_id: {skill_id}\n"
                f"prompt_role_key: {info['role']}\n"
                f"status: {info['status']}\n"
                f"weight: {info['weight']}\n"
                f"when_to_use: {info['description']}\n"
                f"---\n\n"
                f"# {skill_id}\n\n"
                f"## 内容\n\n测试 fixture\n"
            )
            _write_text(skills_dir / f"{skill_id}.md", md_content)

        run_dirs.append(run_dir)

    return run_dirs
