"""从 mvp_scores.json 提取金句、局面背景与引用元数据。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from llm_werewolf.evaluation.post_game.run_context import RunContext
from llm_werewolf.game_runtime.prompts.manager import PromptManager

_CAMP_LABELS = {"werewolf": "狼人阵营", "villager": "好人阵营", "neutral": "中立"}


@dataclass
class GoldenQuote:
    """MVP 体系认定的可引用发言/计划片段。"""

    player_id: str
    player_name: str
    role_name: str | None
    prompt_role_key: str
    camp: str | None
    round_number: int
    phase: str
    kind: str  # public_persuasion | wolf_night_plan
    excerpt: str
    score: float = 0.0
    mvp_rank: int | None = None
    is_overall_mvp: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "role_name": self.role_name,
            "prompt_role_key": self.prompt_role_key,
            "camp": self.camp,
            "round_number": self.round_number,
            "phase": self.phase,
            "kind": self.kind,
            "excerpt": self.excerpt,
            "score": self.score,
            "mvp_rank": self.mvp_rank,
            "is_overall_mvp": self.is_overall_mvp,
            **self.extra,
        }


def load_mvp_payload(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / "mvp_scores.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _role_key(role_name: str | None) -> str:
    if not role_name:
        return "villager"
    return PromptManager.get_prompt_role_key(role_name)


def iter_golden_quotes(
    mvp_payload: dict[str, Any] | None,
    ctx: RunContext,
) -> list[GoldenQuote]:
    """汇总全场金句；MVP 玩家条目优先，按 score 降序。"""
    if not mvp_payload:
        return []

    mvp_player_id = (mvp_payload.get("mvp") or {}).get("player_id")
    quotes: list[GoldenQuote] = []

    for row in mvp_payload.get("players") or []:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("player_id", ""))
        is_mvp = pid == mvp_player_id
        for g in row.get("golden_speech_candidates") or []:
            if not isinstance(g, dict):
                continue
            excerpt = str(g.get("excerpt", "")).strip()
            if len(excerpt) < 8:
                continue
            entry = ctx.roster.get(pid)
            quotes.append(
                GoldenQuote(
                    player_id=pid,
                    player_name=str(row.get("player_name", entry.player_name if entry else pid)),
                    role_name=row.get("role_name") or (entry.role_name if entry else None),
                    prompt_role_key=str(row.get("prompt_role_key") or _role_key(entry.role_name if entry else None)),
                    camp=row.get("camp") or (entry.camp if entry else None),
                    round_number=int(g.get("round_number", 0)),
                    phase=str(g.get("phase", "day_discussion")),
                    kind=str(g.get("kind", "public_persuasion")),
                    excerpt=excerpt,
                    score=float(g.get("score", 0)),
                    mvp_rank=int(row.get("rank", 0)) if row.get("rank") else None,
                    is_overall_mvp=is_mvp,
                    extra={
                        k: g[k]
                        for k in (
                            "matched_elimination",
                            "kill_match_bonus",
                            "camp_aligned_swings",
                        )
                        if k in g
                    },
                )
            )

    quotes.sort(
        key=lambda q: (
            0 if q.is_overall_mvp else 1,
            -(q.score),
            q.mvp_rank or 99,
        ),
    )
    return quotes


def iter_wolf_night_plans(
    mvp_payload: dict[str, Any] | None,
    ctx: RunContext,
    *,
    min_speech_total: float = 12.0,
) -> Iterator[GoldenQuote]:
    """从 MVP 狼夜分析提取策略向候选（非公开发言 Skill）。"""
    if not mvp_payload:
        return
    for row in mvp_payload.get("wolf_night_analysis", {}).get("speeches") or []:
        if not isinstance(row, dict):
            continue
        total = float(row.get("speech_total", 0))
        if total < min_speech_total:
            continue
        excerpt = str(row.get("public_speech", "")).strip()
        if len(excerpt) < 8:
            continue
        pid = str(row.get("speaker_id", ""))
        entry = ctx.roster.get(pid)
        yield GoldenQuote(
            player_id=pid,
            player_name=str(row.get("speaker_name", entry.player_name if entry else pid)),
            role_name=entry.role_name if entry else None,
            prompt_role_key=_role_key(entry.role_name if entry else None),
            camp=entry.camp if entry else "werewolf",
            round_number=int(row.get("round_number", 0)),
            phase=str(row.get("phase", "night")),
            kind="wolf_night_plan",
            excerpt=excerpt,
            score=total,
            extra={
                "plan_clarity": row.get("plan_clarity"),
                "teammate_follow": row.get("teammate_follow"),
                "kill_match_bonus": row.get("kill_match_bonus"),
                "kill_target_id": row.get("kill_target_id"),
            },
        )


def build_situational_background(ctx: RunContext, quote: GoldenQuote) -> str:
    """局面背景：轮次、阶段、胜负、阵营与当时通道。"""
    camp_label = _CAMP_LABELS.get(quote.camp or "", quote.camp or "未知")
    winner = _CAMP_LABELS.get(ctx.winner_camp or "", ctx.winner_camp or "未知")
    channel = "狼队私密频道" if quote.kind == "wolf_night_plan" else "公开讨论"
    lines = [
        f"对局目录 `{ctx.run_dir.name}`，第 {quote.round_number} 轮「{quote.phase}」{channel}。",
        f"发言者 {quote.player_name}（{quote.role_name or '未知身份'}，{camp_label}）。",
        f"本局胜负：{winner} 胜。",
    ]
    if quote.is_overall_mvp:
        lines.append("该玩家为本场规则层 MVP（可为败方）。")
    if quote.extra.get("matched_elimination"):
        lines.append("当轮发言后与放逐票型方向一致。")
    if quote.extra.get("kill_match_bonus"):
        lines.append("狼队夜间发言与当晚刀口计划一致或相关。")
    return " ".join(lines)


def build_applicable_scenario(quote: GoldenQuote) -> str:
    """适用场景：供 Skill / Prompt 提案复用。"""
    if quote.kind == "wolf_night_plan":
        return (
            f"第 {quote.round_number} 夜狼队开会阶段，需要提出清晰刀口/抗推计划、"
            f"协调队友意向时；场上仍为标准狼人杀夜间信息边界。"
        )
    return (
        f"第 {quote.round_number} 轮白天公开讨论，需要给出明确票型倾向、"
        f"用当前可见信息说服同阵营或摇摆中立位时。"
    )


def build_citations(
    ctx: RunContext,
    quote: GoldenQuote,
    mvp_payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """结构化引用，指向 run 内文件与分维度上下文。"""
    dim = "wolf_night" if quote.kind == "wolf_night_plan" else "persuasion"
    dim_paths = (mvp_payload or {}).get("dimension_context_paths") or {}
    rel_ctx = dim_paths.get(dim, f"views/score_contexts/{dim}.md")

    refs: list[dict[str, Any]] = [
        {
            "ref_id": f"run:{ctx.run_dir.name}",
            "type": "run_directory",
            "path": str(ctx.run_dir),
            "label": "本局产物根目录",
        },
        {
            "ref_id": f"mvp_scores:{quote.player_id}:r{quote.round_number}",
            "type": "mvp_golden_quote",
            "path": str(ctx.run_dir / "mvp_scores.json"),
            "label": "MVP 金句条目",
            "quote": quote.excerpt[:500],
        },
        {
            "ref_id": f"score_context:{dim}",
            "type": "score_context",
            "path": str(ctx.run_dir / rel_ctx),
            "label": f"评分维度上下文（{dim}）",
        },
    ]
    if quote.kind == "public_persuasion":
        refs.append({
            "ref_id": f"vote_intentions:r{quote.round_number}",
            "type": "vote_intention_record",
            "path": str(ctx.run_dir / "vote_intentions.jsonl"),
            "label": "投票意向记录",
        })
    return refs
