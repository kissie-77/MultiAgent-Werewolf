"""Assemble coach semantic-extraction prompts from externalized templates."""

from __future__ import annotations

from typing import Any

from llm_werewolf.evaluation.registry.post_game_prompt_registry import (
    render_template,
    load_coach_semantic_extract_bundle,
)


def build_semantic_extract_prompt(
    report: dict[str, Any],
    *,
    won: bool,
    prompt_version: str | None = None,
) -> str:
    bundle = load_coach_semantic_extract_bundle(prompt_version)
    lines = list(bundle.intro)
    lines.append(bundle.result_win if won else bundle.result_loss)
    for episode in report.get("episodes", []):
        messages = episode.get("key_event_messages", []) + episode.get("decision_event_messages", [])
        if not messages:
            continue
        lines.append(
            render_template(
                bundle.episode_line,
                round_number=episode.get("round_number", ""),
                messages="；".join(messages[:4]),
            )
        )
    return "\n".join(lines)
