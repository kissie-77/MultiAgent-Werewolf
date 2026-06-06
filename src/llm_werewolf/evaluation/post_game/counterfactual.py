"""Rule-based counterfactual review for post-game reports."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from llm_werewolf.evaluation.post_game.run_context import RunContext


def build_counterfactual_report(ctx: RunContext) -> dict[str, Any]:
    cases = _vote_counterfactuals(ctx) + _night_action_counterfactuals(ctx)
    return {
        "schema": "counterfactual_report_v1",
        "winner_camp": ctx.winner_camp,
        "case_count": len(cases),
        "cases": cases[:8],
    }


def write_counterfactual_artifacts(ctx: RunContext) -> Path:
    payload = build_counterfactual_report(ctx)
    json_path = ctx.run_dir / "counterfactual_report.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = ctx.run_dir / "counterfactual_report.md"
    md_path.write_text(_format_markdown(payload), encoding="utf-8")
    return json_path


def _vote_counterfactuals(ctx: RunContext) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for event in ctx.events:
        if _event_type(event) != "vote_result":
            continue
        data = event.get("data") or {}
        executed = str(data.get("executed") or data.get("target_id") or "")
        votes = data.get("votes") if isinstance(data.get("votes"), dict) else {}
        if not executed or not votes:
            continue
        executed_votes = len(votes.get(executed) or [])
        runner_up, runner_up_votes = _runner_up(votes, executed)
        margin = executed_votes - runner_up_votes
        if margin <= 2:
            cases.append(
                {
                    "kind": "vote_swing",
                    "round_number": event.get("round_number"),
                    "phase": event.get("phase"),
                    "actual_action": f"{executed} was executed by vote",
                    "counterfactual": (
                        f"If {max(1, margin)} voter(s) moved from {executed} to "
                        f"{runner_up or 'another target'}, the exile target could change."
                    ),
                    "likely_effect": "Day execution pressure and camp tempo would likely shift.",
                    "confidence": "medium" if runner_up else "low",
                    "evidence": {"executed": executed, "margin": margin, "votes": votes},
                }
            )
    return cases


def _night_action_counterfactuals(ctx: RunContext) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for event in ctx.events:
        etype = _event_type(event)
        data = event.get("data") or {}
        target = str(data.get("target_id") or data.get("player_id") or "")
        if etype == "werewolf_killed" and target:
            cases.append(
                {
                    "kind": "night_target",
                    "round_number": event.get("round_number"),
                    "phase": event.get("phase"),
                    "actual_action": f"Werewolves targeted {target}",
                    "counterfactual": (
                        f"If the night target changed from {target} to a lower-value or protected seat, "
                        "the next day discussion and survival tempo could change."
                    ),
                    "likely_effect": "A different death pattern may alter trust chains and vote focus.",
                    "confidence": "low",
                    "evidence": {"target_id": target, "event_type": etype},
                }
            )
        elif etype == "seer_checked" and target:
            cases.append(
                {
                    "kind": "seer_check",
                    "round_number": event.get("round_number"),
                    "phase": event.get("phase"),
                    "actual_action": f"Seer checked {target}",
                    "counterfactual": (
                        f"If the seer checked another high-suspicion seat instead of {target}, "
                        "the public claim and voting basis could be stronger or weaker."
                    ),
                    "likely_effect": "Information value changes, especially if the checked player later becomes a vote focus.",
                    "confidence": "low",
                    "evidence": {"target_id": target, "result": data.get("result")},
                }
            )
    return cases


def _runner_up(votes: dict[str, Any], winner: str) -> tuple[str | None, int]:
    scored = sorted(
        ((target, len(voters or [])) for target, voters in votes.items() if target != winner),
        key=lambda item: item[1],
        reverse=True,
    )
    return scored[0] if scored else (None, 0)


def _event_type(event: dict[str, Any]) -> str:
    return str(event.get("event_type", "")).lower()


def _format_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Counterfactual Report",
        "",
        f"- Winner camp: `{payload.get('winner_camp')}`",
        f"- Cases: `{payload.get('case_count', 0)}`",
        "",
    ]
    if not payload.get("cases"):
        lines.append("No pivotal counterfactual cases were detected.")
        return "\n".join(lines) + "\n"

    for idx, case in enumerate(payload["cases"], start=1):
        lines.extend(
            [
                f"## Case {idx}: {case.get('kind')}",
                "",
                f"- Actual: {case.get('actual_action')}",
                f"- If changed: {case.get('counterfactual')}",
                f"- Likely effect: {case.get('likely_effect')}",
                f"- Confidence: `{case.get('confidence')}`",
                "",
            ]
        )
    return "\n".join(lines)
