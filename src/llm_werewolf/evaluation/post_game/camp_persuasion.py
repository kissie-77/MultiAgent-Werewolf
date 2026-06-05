"""阵营匹配的投票意向说服分析（在 vote_swing 之上打标）。"""

from __future__ import annotations

import json
from typing import Any
from dataclasses import field, dataclass

from llm_werewolf.game_runtime.types.enums import Camp
from llm_werewolf.evaluation.post_game.run_context import (
    RunContext,
    target_id_to_camp,
    is_camp_aligned_vote_target,
)
from llm_werewolf.evaluation.core.vote_swing_analysis import (
    VoteSwingReport,
    analyze_path,
    load_speech_records,
    format_markdown_report,
)


@dataclass
class CampAlignedSwing:
    player_id: str
    player_name: str
    from_target_id: str | None
    to_target_id: str | None
    from_target_camp: str | None
    to_target_camp: str | None
    camp_aligned: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "from_target_id": self.from_target_id,
            "to_target_id": self.to_target_id,
            "from_target_camp": self.from_target_camp,
            "to_target_camp": self.to_target_camp,
            "camp_aligned": self.camp_aligned,
        }


@dataclass
class CampSpeechInfluence:
    speaker_id: str
    speaker_name: str
    speaker_camp: str | None
    round_number: int
    phase: str
    public_speech: str
    swing_count: int
    camp_aligned_swings: int
    camp_aligned_score: int
    matched_round_elimination: bool
    elimination_target_id: str | None = None
    elimination_drive_swings: int = 0
    swings: list[CampAlignedSwing] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "speaker_camp": self.speaker_camp,
            "round_number": self.round_number,
            "phase": self.phase,
            "public_speech": self.public_speech,
            "swing_count": self.swing_count,
            "camp_aligned_swings": self.camp_aligned_swings,
            "camp_aligned_score": self.camp_aligned_score,
            "matched_round_elimination": self.matched_round_elimination,
            "elimination_target_id": self.elimination_target_id,
            "elimination_drive_swings": self.elimination_drive_swings,
            "swings": [s.to_dict() for s in self.swings],
        }


@dataclass
class CampPersuasionReport:
    speeches: list[CampSpeechInfluence] = field(default_factory=list)
    winner_camp: str | None = None
    prompt_version: str = "v1"

    def to_dict(self) -> dict[str, Any]:
        ranked = sorted(self.speeches, key=lambda s: s.camp_aligned_score, reverse=True)
        return {
            "prompt_version": self.prompt_version,
            "winner_camp": self.winner_camp,
            "total_speeches": len(self.speeches),
            "total_camp_aligned_swings": sum(s.camp_aligned_swings for s in self.speeches),
            "top_positive_influence": [s.to_dict() for s in ranked[:15]],
            "speeches": [s.to_dict() for s in self.speeches],
        }


def _eliminations_by_round(ctx: RunContext) -> dict[int, str]:
    out: dict[int, str] = {}
    for event in ctx.events:
        if event.get("event_type") != "player_eliminated":
            continue
        rnd = int(event.get("round_number", 0))
        pid = str((event.get("data") or {}).get("player_id", ""))
        if pid:
            out[rnd] = pid
    return out


def _annotate_swings(
    raw_swings: list[dict[str, Any]], speaker_camp: str | None, ctx: RunContext
) -> list[CampAlignedSwing]:
    annotated: list[CampAlignedSwing] = []
    for swing in raw_swings:
        to_id = swing.get("to_target_id")
        from_id = swing.get("from_target_id")
        to_camp = target_id_to_camp(str(to_id) if to_id else None, ctx.roster)
        from_camp = target_id_to_camp(str(from_id) if from_id else None, ctx.roster)
        aligned = False
        if is_camp_aligned_vote_target(speaker_camp, to_camp):
            if from_camp != to_camp or to_camp != from_camp:
                aligned = True
        annotated.append(
            CampAlignedSwing(
                player_id=str(swing.get("player_id", "")),
                player_name=str(swing.get("player_name", "")),
                from_target_id=str(from_id) if from_id else None,
                to_target_id=str(to_id) if to_id else None,
                from_target_camp=from_camp,
                to_target_camp=to_camp,
                camp_aligned=aligned,
            )
        )
    return annotated


def _speaker_advocated_targets(ctx: RunContext) -> dict[tuple[str, int], str]:
    """发言者在当条 public 意向记录中自身主张的放逐目标。"""
    try:
        records = load_speech_records(ctx.run_dir)
    except (FileNotFoundError, ValueError):
        records = []
    out: dict[tuple[str, int], str] = {}
    for raw in records:
        if str(raw.get("channel", "")) not in {"", "public"}:
            continue
        speaker_id = str(raw.get("speaker_id", ""))
        rnd = int(raw.get("round_number", 0))
        if not speaker_id or not rnd:
            continue
        after = raw.get("after") or {}
        if not isinstance(after, dict):
            continue
        entry = after.get(speaker_id)
        if not isinstance(entry, dict):
            continue
        target_id = entry.get("target_id")
        if target_id:
            out[(speaker_id, rnd)] = str(target_id)
    return out


def _matched_elimination_for_speaker(
    *,
    speaker_camp: str | None,
    elim_target: str | None,
    elim_target_camp: str | None,
    camp_swings: list[CampAlignedSwing],
    drive_count: int,
    speaker_advocated_target: str | None = None,
) -> bool:
    """按阵营判断「发言是否推动当轮实际放逐且结果对发言方阵营有利」。

    好人侧误出同伴（如抗推预言家）不算 matched，即使有人意向摇摆指向最终出局者。
    终局全员已对齐、无 swing 但发言者意向即当轮出局者时仍算 matched。
    """
    if not elim_target:
        return False
    camp_favorable = False
    if speaker_camp == Camp.WEREWOLF.value:
        camp_favorable = elim_target_camp == Camp.VILLAGER.value
    elif speaker_camp == Camp.VILLAGER.value:
        camp_favorable = elim_target_camp == Camp.WEREWOLF.value
    else:
        return False
    if not camp_favorable:
        return False
    if drive_count > 0:
        return True
    return speaker_advocated_target == elim_target


def _persuasion_score_for_speech(
    *,
    aligned_count: int,
    matched_elim: bool,
    speaker_camp: str | None,
    drive_count: int,
    swing_to_final_vote: int = 0,
) -> int:
    """阵营感知的公开说服分。"""
    base = aligned_count * 10
    if matched_elim:
        base += 20
    if speaker_camp == Camp.VILLAGER.value:
        base += drive_count * 8 + swing_to_final_vote * 12
    elif speaker_camp == Camp.WEREWOLF.value:
        base += drive_count * 5
    return base


def build_camp_persuasion_report(
    ctx: RunContext, swing_report: VoteSwingReport | None = None
) -> CampPersuasionReport:
    if swing_report is None:
        swing_report = analyze_path(ctx.run_dir)

    elim_by_round = _eliminations_by_round(ctx)
    advocated_targets = _speaker_advocated_targets(ctx)
    report = CampPersuasionReport(winner_camp=ctx.winner_camp, prompt_version=ctx.prompt_version)

    for speech in swing_report.speech_influences:
        entry = ctx.roster.get(speech.speaker_id)
        speaker_camp = entry.camp if entry else None
        camp_swings = _annotate_swings(speech.swings, speaker_camp, ctx)
        aligned_count = sum(1 for s in camp_swings if s.camp_aligned)
        elim_target = elim_by_round.get(speech.round_number)
        elim_target_camp = target_id_to_camp(elim_target, ctx.roster) if elim_target else None
        drive_count = sum(1 for s in camp_swings if elim_target and s.to_target_id == elim_target)
        advocated = advocated_targets.get((speech.speaker_id, speech.round_number))
        matched_elim = _matched_elimination_for_speaker(
            speaker_camp=speaker_camp,
            elim_target=elim_target,
            elim_target_camp=elim_target_camp,
            camp_swings=camp_swings,
            drive_count=drive_count,
            speaker_advocated_target=advocated,
        )
        camp_score = _persuasion_score_for_speech(
            aligned_count=aligned_count,
            matched_elim=matched_elim,
            speaker_camp=speaker_camp,
            drive_count=drive_count,
        )

        report.speeches.append(
            CampSpeechInfluence(
                speaker_id=speech.speaker_id,
                speaker_name=speech.speaker_name,
                speaker_camp=speaker_camp,
                round_number=speech.round_number,
                phase=speech.phase,
                public_speech=speech.public_speech,
                swing_count=speech.swing_count,
                camp_aligned_swings=aligned_count,
                camp_aligned_score=camp_score,
                matched_round_elimination=matched_elim,
                elimination_target_id=elim_target,
                elimination_drive_swings=drive_count,
                swings=camp_swings,
            )
        )

    return report


def format_camp_markdown(report: CampPersuasionReport) -> str:
    lines = [
        "# Camp-Aligned Persuasion Analysis",
        "",
        f"- Prompt version (runtime): **{report.prompt_version}**",
        f"- Winner camp: **{report.winner_camp or 'unknown'}**",
        f"- Speeches: **{len(report.speeches)}**",
        "",
        "## Top camp-aligned influence",
        "",
    ]
    top = sorted(report.speeches, key=lambda s: s.camp_aligned_score, reverse=True)[:15]
    for idx, speech in enumerate(top, start=1):
        if speech.camp_aligned_score <= 0:
            continue
        lines.append(
            f"### {idx}. {speech.speaker_name} "
            f"({speech.speaker_camp or '?'}) · R{speech.round_number}"
        )
        lines.append(
            f"- Score: **{speech.camp_aligned_score}** "
            f"({speech.camp_aligned_swings}/{speech.swing_count} aligned swings)"
        )
        if speech.matched_round_elimination:
            lines.append("- Matched round elimination: **yes**")
        if speech.public_speech:
            excerpt = speech.public_speech.replace("\n", " ")[:180]
            lines.append(f"- Speech: {excerpt}")
        lines.append("")

    return "\n".join(lines)


def write_camp_persuasion_artifacts(
    ctx: RunContext, swing_report: VoteSwingReport | None = None
) -> CampPersuasionReport:
    report = build_camp_persuasion_report(ctx, swing_report)
    out = ctx.run_dir
    out.mkdir(parents=True, exist_ok=True)

    json_path = out / "camp_persuasion_summary.json"
    json_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path = out / "camp_persuasion_report.md"
    base_md = format_markdown_report(swing_report or analyze_path(ctx.run_dir))
    md_path.write_text(base_md + "\n\n---\n\n" + format_camp_markdown(report), encoding="utf-8")
    return report
