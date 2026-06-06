"""Bad Case 可视化报告——自动从对局中检测典型决策失误并生成结构化报告。

检测模式：
- 预言家验到狼人但未在次轮发言中公开
- 女巫有解药但未救被刀目标
- 女巫首夜自救（部分规则下为失误）
- 好人投票投到好人（且该轮有狼人候选）
- 狼人刀口选择了被守卫保护的目标（连续被挡刀）
- 预言家验过的目标未被投票淘汰
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext

# ─── Bad Case 检测器 ────────────────────────────────────────────────


def _detect_seer_silent_cases(ctx: RunContext) -> list[dict[str, Any]]:
    """预言家验到狼人但后续未公开查验结果。"""
    cases: list[dict[str, Any]] = []
    seer_checks: list[dict[str, Any]] = []
    speeches: list[dict[str, Any]] = []

    for event in ctx.events:
        etype = event.get("event_type", "")
        data = event.get("data") or {}
        if etype == "seer_checked":
            seer_checks.append(event)
        elif etype == "player_speech":
            speeches.append(event)

    for check in seer_checks:
        data = check.get("data") or {}
        result = data.get("result", "")
        if result != "werewolf":
            continue
        seer_id = data.get("player_id", "")
        target_id = data.get("target_id", "")
        check_round = check.get("round_number", 0)

        target_entry = ctx.roster.get(target_id)
        target_name = target_entry.player_name if target_entry else target_id

        mentioned = False
        for speech in speeches:
            s_data = speech.get("data") or {}
            if s_data.get("player_id") != seer_id:
                continue
            if speech.get("round_number", 0) <= check_round:
                continue
            content = str(s_data.get("content", ""))
            if target_name in content or target_id in content:
                mentioned = True
                break

        if not mentioned:
            cases.append({
                "kind": "seer_silent_on_wolf",
                "severity": "high",
                "round_number": check_round,
                "player_id": seer_id,
                "description": f"预言家第{check_round}轮验出 {target_name} 为狼人，但后续发言中未提及该查验结果",
                "suggestion": "预言家应在验出狼人后尽早公开信息引导好人归票",
                "evidence": {"target_id": target_id, "target_name": target_name},
            })
    return cases


# ─── APPEND_MARKER ──────────────────────────────────────────────────


def _detect_witch_no_save_cases(ctx: RunContext) -> list[dict[str, Any]]:
    """女巫有解药但未救被刀目标。"""
    cases: list[dict[str, Any]] = []
    kills: dict[int, str] = {}
    saves: set[int] = set()

    for event in ctx.events:
        etype = event.get("event_type", "")
        data = event.get("data") or {}
        rnd = event.get("round_number", 0)
        if etype == "werewolf_killed":
            kills[rnd] = data.get("target_id", "")
        elif etype == "witch_saved":
            saves.add(rnd)

    witch_id = None
    for pid, entry in ctx.roster.items():
        if entry.role_name == "Witch":
            witch_id = pid
            break

    if not witch_id:
        return cases

    has_used_save = False
    for rnd in sorted(kills.keys()):
        if rnd in saves:
            has_used_save = True
            continue
        if has_used_save:
            continue
        target_id = kills[rnd]
        target_entry = ctx.roster.get(target_id)
        target_name = target_entry.player_name if target_entry else target_id
        target_camp = target_entry.camp if target_entry else None

        if target_camp == "villager":
            cases.append({
                "kind": "witch_no_save",
                "severity": "medium",
                "round_number": rnd,
                "player_id": witch_id,
                "description": f"女巫第{rnd}轮持有解药但未救好人 {target_name}",
                "suggestion": "女巫在确认被刀者为好人时应优先使用解药，除非战略性留药",
                "evidence": {"target_id": target_id, "target_camp": target_camp},
            })
            break
    return cases


def _detect_villager_vote_friendly_fire(ctx: RunContext) -> list[dict[str, Any]]:
    """好人投票投到好人，且该轮有狼人候选被淘汰。"""
    cases: list[dict[str, Any]] = []

    for event in ctx.events:
        etype = event.get("event_type", "")
        if etype != "vote_result":
            continue
        data = event.get("data") or {}
        rnd = event.get("round_number", 0)
        votes = data.get("votes")
        executed = data.get("executed") or data.get("target_id")
        if not votes or not executed:
            continue

        executed_entry = ctx.roster.get(str(executed))
        executed_camp = executed_entry.camp if executed_entry else None

        if not isinstance(votes, dict):
            continue

        for target_id, voter_ids in votes.items():
            if not isinstance(voter_ids, list):
                continue
            target_entry = ctx.roster.get(target_id)
            target_camp = target_entry.camp if target_entry else None
            if target_camp != "villager":
                continue

            for voter_id in voter_ids:
                voter_entry = ctx.roster.get(voter_id)
                voter_camp = voter_entry.camp if voter_entry else None
                if voter_camp != "villager":
                    continue
                if target_id == str(executed):
                    continue

                wolf_candidates = [
                    tid for tid in votes
                    if ctx.roster.get(tid) and ctx.roster[tid].camp == "werewolf"
                ]
                if not wolf_candidates:
                    continue

                voter_name = voter_entry.player_name if voter_entry else voter_id
                target_name = target_entry.player_name if target_entry else target_id
                cases.append({
                    "kind": "friendly_fire_vote",
                    "severity": "medium",
                    "round_number": rnd,
                    "player_id": voter_id,
                    "description": (
                        f"好人 {voter_name} 第{rnd}轮投票投给好人 {target_name}，"
                        f"但该轮存在狼人候选"
                    ),
                    "suggestion": "好人应优先集中票数在可疑度最高的狼人候选上",
                    "evidence": {
                        "target_id": target_id,
                        "wolf_candidates": wolf_candidates,
                    },
                })
    return cases[:5]


def _detect_wolf_repeat_blocked(ctx: RunContext) -> list[dict[str, Any]]:
    """狼人连续多轮刀口被守卫挡住。"""
    cases: list[dict[str, Any]] = []
    guarded: dict[int, str] = {}
    kills: dict[int, str] = {}

    for event in ctx.events:
        etype = event.get("event_type", "")
        data = event.get("data") or {}
        rnd = event.get("round_number", 0)
        if etype == "guard_protected":
            guarded[rnd] = data.get("target_id", "")
        elif etype == "werewolf_killed":
            kills[rnd] = data.get("target_id", "")

    blocked_rounds = []
    for rnd, target in kills.items():
        if guarded.get(rnd) == target:
            blocked_rounds.append(rnd)

    if len(blocked_rounds) >= 2:
        cases.append({
            "kind": "wolf_repeat_blocked",
            "severity": "low",
            "round_number": blocked_rounds[-1],
            "player_id": None,
            "description": f"狼人在第{blocked_rounds}轮连续被守卫挡刀，缺乏目标多样性",
            "suggestion": "狼队应观察守卫行为模式，避免连续刀同类型目标",
            "evidence": {"blocked_rounds": blocked_rounds},
        })
    return cases


# ─── 汇总与输出 ─────────────────────────────────────────────────────


def build_bad_case_report(ctx: RunContext) -> dict[str, Any]:
    """构建 Bad Case 报告。返回包含所有检测到的失误案例的字典。"""
    all_cases: list[dict[str, Any]] = []
    all_cases.extend(_detect_seer_silent_cases(ctx))
    all_cases.extend(_detect_witch_no_save_cases(ctx))
    all_cases.extend(_detect_villager_vote_friendly_fire(ctx))
    all_cases.extend(_detect_wolf_repeat_blocked(ctx))

    all_cases.sort(key=lambda c: (
        {"high": 0, "medium": 1, "low": 2}.get(c.get("severity", "low"), 3),
        c.get("round_number", 0),
    ))

    return {
        "schema": "bad_case_report_v1",
        "winner_camp": ctx.winner_camp,
        "total_cases": len(all_cases),
        "severity_summary": {
            "high": sum(1 for c in all_cases if c["severity"] == "high"),
            "medium": sum(1 for c in all_cases if c["severity"] == "medium"),
            "low": sum(1 for c in all_cases if c["severity"] == "low"),
        },
        "cases": all_cases,
    }


def _format_markdown(payload: dict[str, Any]) -> str:
    """将 bad case 报告格式化为 Markdown。"""
    lines: list[str] = []
    lines.append("# Bad Case 分析报告\n")
    lines.append(f"**获胜阵营：** {payload.get('winner_camp', '未知')}")
    lines.append(f"**检出失误总数：** {payload['total_cases']}\n")

    summary = payload["severity_summary"]
    lines.append("## 严重程度分布\n")
    lines.append("| 严重 | 中等 | 轻微 |")
    lines.append("|------|------|------|")
    lines.append(f"| {summary['high']} | {summary['medium']} | {summary['low']} |\n")

    if not payload["cases"]:
        lines.append("*本局未检出典型决策失误，表现良好。*\n")
        return "\n".join(lines)

    lines.append("## 失误详情\n")
    for i, case in enumerate(payload["cases"], 1):
        severity_label = {"high": "严重", "medium": "中等", "low": "轻微"}.get(
            case["severity"], "未知"
        )
        lines.append(f"### Case {i} — [{severity_label}] 第{case['round_number']}轮\n")
        lines.append(f"**类型：** `{case['kind']}`")
        if case.get("player_id"):
            lines.append(f"**玩家：** {case['player_id']}")
        lines.append(f"**描述：** {case['description']}")
        lines.append(f"**改进建议：** {case['suggestion']}\n")

    return "\n".join(lines)


def write_bad_case_artifacts(ctx: RunContext) -> Path:
    """生成 Bad Case 报告并写入对局目录。"""
    payload = build_bad_case_report(ctx)
    json_path = ctx.run_dir / "bad_case_report.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = ctx.run_dir / "bad_case_report.md"
    md_path.write_text(_format_markdown(payload), encoding="utf-8")
    return json_path
