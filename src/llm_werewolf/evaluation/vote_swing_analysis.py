"""从 vote_intentions.jsonl 或事件日志进行投票摇摆/说服效果分析。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SpeechInfluence:
    """单条圆桌发言的说服影响。"""

    speaker_id: str
    speaker_name: str
    round_number: int
    phase: str
    channel: str
    public_speech: str
    swing_count: int
    swings: list[dict[str, Any]]
    influence_score: int
    before_summary: str = ""
    after_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "round_number": self.round_number,
            "phase": self.phase,
            "channel": self.channel,
            "public_speech": self.public_speech,
            "swing_count": self.swing_count,
            "swings": self.swings,
            "influence_score": self.influence_score,
            "before_summary": self.before_summary,
            "after_summary": self.after_summary,
        }


@dataclass
class PlayerPersuasionStats:
    """单名玩家的说服指标汇总。"""

    player_id: str
    player_name: str
    speeches_count: int = 0
    total_swings_caused: int = 0
    total_influence_score: int = 0

    @property
    def avg_swings_per_speech(self) -> float:
        if self.speeches_count == 0:
            return 0.0
        return self.total_swings_caused / self.speeches_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "speeches_count": self.speeches_count,
            "total_swings_caused": self.total_swings_caused,
            "total_influence_score": self.total_influence_score,
            "avg_swings_per_speech": round(self.avg_swings_per_speech, 3),
        }


@dataclass
class VoteSwingReport:
    """整局说服分析。"""

    speech_influences: list[SpeechInfluence] = field(default_factory=list)
    player_stats: dict[str, PlayerPersuasionStats] = field(default_factory=dict)
    total_speeches: int = 0
    total_swings: int = 0

    def to_dict(self) -> dict[str, Any]:
        ranked = sorted(
            self.player_stats.values(),
            key=lambda s: s.total_influence_score,
            reverse=True,
        )
        return {
            "total_speeches": self.total_speeches,
            "total_swings": self.total_swings,
            "speeches": [s.to_dict() for s in self.speech_influences],
            "player_ranking": [s.to_dict() for s in ranked],
        }


def _intentions_summary(intentions: dict[str, Any]) -> str:
    parts: list[str] = []
    for _pid, entry in sorted(intentions.items()):
        if not isinstance(entry, dict):
            continue
        name = entry.get("player_name") or entry.get("player_id") or "?"
        seat = entry.get("seat", 0)
        target = entry.get("target_name")
        if seat == 0 or not target:
            parts.append(f"{name}→无")
        else:
            parts.append(f"{name}→{target}")
    return ", ".join(parts)


def _influence_score(swing_count: int) -> int:
    """Foaster 风格基础分：每次意向变更 +10。"""
    return swing_count * 10


def analyze_speech_records(records: list[dict[str, Any]]) -> VoteSwingReport:
    """由发言关联意向记录构建说服报告。"""
    report = VoteSwingReport()
    for raw in records:
        if not str(raw.get("public_speech", "")).strip():
            continue
        speaker_id = str(raw.get("speaker_id", ""))
        speaker_name = str(raw.get("speaker_name", speaker_id))
        swings = list(raw.get("swings") or [])
        swing_count = int(raw.get("swing_count", len(swings)))
        influence = SpeechInfluence(
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            round_number=int(raw.get("round_number", 0)),
            phase=str(raw.get("phase", "")),
            channel=str(raw.get("channel", "")),
            public_speech=str(raw.get("public_speech", ""))[:500],
            swing_count=swing_count,
            swings=swings,
            influence_score=_influence_score(swing_count),
            before_summary=_intentions_summary(raw.get("before") or {}),
            after_summary=_intentions_summary(raw.get("after") or {}),
        )
        report.speech_influences.append(influence)
        report.total_speeches += 1
        report.total_swings += swing_count

        stats = report.player_stats.get(speaker_id)
        if stats is None:
            stats = PlayerPersuasionStats(
                player_id=speaker_id,
                player_name=speaker_name,
            )
            report.player_stats[speaker_id] = stats
        stats.speeches_count += 1
        stats.total_swings_caused += swing_count
        stats.total_influence_score += influence.influence_score

    report.speech_influences.sort(key=lambda s: (s.round_number, s.speaker_id))
    return report


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def load_speech_records(source: str | Path) -> list[dict[str, Any]]:
    """从 vote_intentions.jsonl、events.jsonl 或对局目录加载记录。"""
    path = Path(source)
    if path.is_file():
        if path.name == "vote_intentions.jsonl":
            return _read_jsonl(path)
        if path.name == "events.jsonl":
            return _records_from_events(_read_jsonl(path))
        msg = f"Unsupported file: {path}"
        raise ValueError(msg)

    if path.is_dir():
        intentions = path / "vote_intentions.jsonl"
        if intentions.is_file():
            return _read_jsonl(intentions)
        events = path / "events.jsonl"
        if events.is_file():
            return _records_from_events(_read_jsonl(events))
        msg = f"No vote_intentions.jsonl or events.jsonl in {path}"
        raise FileNotFoundError(msg)

    msg = f"Path not found: {path}"
    raise FileNotFoundError(msg)


def _records_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for event in events:
        if event.get("event_type") != "vote_intention_snapshot":
            continue
        data = event.get("data")
        if isinstance(data, dict):
            records.append(data)
    return records


def analyze_path(source: str | Path) -> VoteSwingReport:
    """加载并分析投票意向产物。"""
    return analyze_speech_records(load_speech_records(source))


def format_markdown_report(report: VoteSwingReport, *, title: str = "Vote Swing Analysis") -> str:
    """人类可读的说服报告。"""
    lines = [
        f"# {title}",
        "",
        f"- Speeches analyzed: **{report.total_speeches}**",
        f"- Total vote intention changes: **{report.total_swings}**",
        "",
        "## Player ranking (by influence score)",
        "",
        "| Player | Speeches | Swings caused | Influence | Avg swings/speech |",
        "|--------|----------|---------------|-----------|-------------------|",
    ]
    ranked = sorted(
        report.player_stats.values(),
        key=lambda s: s.total_influence_score,
        reverse=True,
    )
    for stats in ranked:
        lines.append(
            f"| {stats.player_name} | {stats.speeches_count} | "
            f"{stats.total_swings_caused} | {stats.total_influence_score} | "
            f"{stats.avg_swings_per_speech:.2f} |"
        )

    lines.extend(["", "## Top influential speeches", ""])
    top = sorted(
        report.speech_influences,
        key=lambda s: s.influence_score,
        reverse=True,
    )[:20]
    for idx, speech in enumerate(top, start=1):
        lines.append(
            f"### {idx}. {speech.speaker_name} "
            f"(R{speech.round_number} · {speech.phase} · {speech.channel})"
        )
        lines.append(f"- **Influence score**: {speech.influence_score} ({speech.swing_count} swings)")
        if speech.public_speech:
            excerpt = speech.public_speech.replace("\n", " ")[:200]
            lines.append(f"- **Speech**: {excerpt}")
        lines.append(f"- **Before**: {speech.before_summary or '—'}")
        lines.append(f"- **After**: {speech.after_summary or '—'}")
        if speech.swings:
            lines.append("- **Changes**:")
            for swing in speech.swings:
                name = swing.get("player_name", swing.get("player_id", "?"))
                from_name = swing.get("from_target_name") or "无"
                to_name = swing.get("to_target_name") or "无"
                lines.append(f"  - {name}: {from_name} → {to_name}")
        lines.append("")

    return "\n".join(lines)


def write_persuasion_artifacts(
    source: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    """分析源数据并写入 vote_swing_report.md 与 vote_swing_summary.json。"""
    report = analyze_path(source)
    out = Path(output_dir) if output_dir else Path(source)
    if out.is_file():
        out = out.parent
    out.mkdir(parents=True, exist_ok=True)

    md_path = out / "vote_swing_report.md"
    md_path.write_text(format_markdown_report(report), encoding="utf-8")

    json_path = out / "vote_swing_summary.json"
    json_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out
