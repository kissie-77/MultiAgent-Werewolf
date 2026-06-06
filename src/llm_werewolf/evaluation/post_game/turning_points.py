"""从 events 提取对局关键转折（规则叙事，不依赖 LLM）。"""

from __future__ import annotations

from llm_werewolf.game_runtime.types.enums import Camp
from llm_werewolf.evaluation.post_game.run_context import RunContext, target_id_to_camp


def _player_label(ctx: RunContext, player_id: str | None) -> str:
    if not player_id:
        return "未知"
    entry = ctx.roster.get(player_id)
    if entry:
        role = entry.role_name or "?"
        return f"{entry.player_name}（{role}）"
    return player_id


def _camp_label(camp: str | None) -> str:
    if camp == Camp.WEREWOLF.value:
        return "狼人"
    if camp == Camp.VILLAGER.value:
        return "好人"
    return camp or "未知"


def build_turning_points(ctx: RunContext) -> list[str]:
    """按时间顺序生成关键转折 bullet。"""
    lines: list[str] = []
    kills: dict[int, str] = {}
    eliminations: dict[int, str] = {}
    saves: dict[int, str] = {}
    poisons: dict[int, str] = {}
    checks: dict[int, tuple[str, str | None]] = {}

    for event in ctx.events:
        etype = str(event.get("event_type", ""))
        rnd = int(event.get("round_number", 0))
        data = event.get("data") or {}
        if etype == "werewolf_killed":
            target = str(data.get("target_id", ""))
            if target:
                kills[rnd] = target
        elif etype == "player_eliminated":
            pid = str(data.get("player_id", ""))
            if pid:
                eliminations[rnd] = pid
        elif etype == "witch_saved":
            target = str(data.get("target_id", ""))
            if target:
                saves[rnd] = target
        elif etype in {"witch_poison_used", "witch_poisoned"}:
            target = str(data.get("target_id", ""))
            if target:
                poisons[rnd] = target
        elif etype == "seer_checked":
            target = str(data.get("target_id", ""))
            result = data.get("result")
            if target:
                checks[rnd] = (target, str(result) if result is not None else None)

    rounds = sorted(set(kills) | set(eliminations) | set(saves) | set(poisons) | set(checks))
    for rnd in rounds:
        if rnd in kills:
            pid = kills[rnd]
            lines.append(
                f"- **第 {rnd} 夜**：狼刀 {_player_label(ctx, pid)}（{_camp_label(target_id_to_camp(pid, ctx.roster))}）"
            )
        if rnd in saves:
            pid = saves[rnd]
            lines.append(f"- **第 {rnd} 夜**：女巫救 {_player_label(ctx, pid)}")
        if rnd in poisons:
            pid = poisons[rnd]
            lines.append(
                f"- **第 {rnd} 夜**：女巫毒 {_player_label(ctx, pid)}"
                f"（{_camp_label(target_id_to_camp(pid, ctx.roster))}）"
            )
        if rnd in checks:
            target, result = checks[rnd]
            result_zh = "狼人" if result in {"werewolf", "wolf"} else "好人" if result else "未知"
            lines.append(
                f"- **第 {rnd} 夜**：预言家验 {_player_label(ctx, target)} → **{result_zh}**"
            )
        if rnd in eliminations:
            pid = eliminations[rnd]
            lines.append(
                f"- **第 {rnd} 天投票**：放逐 {_player_label(ctx, pid)}"
                f"（{_camp_label(target_id_to_camp(pid, ctx.roster))}）"
            )

    if ctx.winner_camp:
        lines.append(f"- **终局**：{_camp_label(ctx.winner_camp)}阵营获胜")

    speech_failures = sum(
        1
        for e in ctx.events
        if e.get("event_type") == "error" or "发言失败" in str(e.get("message", ""))
    )
    if speech_failures:
        lines.append(f"- **异常**：记录到 {speech_failures} 次发言/决策失败，评分样本可能不完整")

    return lines


def build_rule_summary_zh(ctx: RunContext) -> str:
    """LLM 失败时的规则复盘摘要。"""
    points = build_turning_points(ctx)
    if not points:
        return "本局事件不足，无法生成规则转折摘要。"
    body = "\n".join(points)
    return f"本局关键转折（规则提取）：\n{body}"
