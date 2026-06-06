"""Tests for externalized post-game prompt packages."""

from __future__ import annotations

from pathlib import Path

import pytest

from llm_werewolf.evaluation.post_game.coach_prompt_builder import build_semantic_extract_prompt
from llm_werewolf.evaluation.post_game.replay_prompt_builder import build_replay_prompt
from llm_werewolf.evaluation.registry.post_game_prompt_registry import (
    load_coach_semantic_extract_bundle,
    load_replay_prompt_bundle,
    render_template,
    resolve_latest_coach_version,
    resolve_latest_replay_version,
)


def test_replay_prompt_bundle_loads_from_files() -> None:
    bundle = load_replay_prompt_bundle(resolve_latest_replay_version())
    assert "赛后评测分析师" in bundle.system_prompt
    assert bundle.dimensions["persuasion"] == "公开说服（仅白天公开记录）"
    assert "summary_zh" in bundle.json_reminder
    assert "JSON" in bundle.plain_json_fallback


def test_coach_semantic_extract_bundle_loads() -> None:
    bundle = load_coach_semantic_extract_bundle(resolve_latest_coach_version())
    assert len(bundle.intro) >= 2
    assert "胜利" in bundle.result_win


def test_render_template_substitutes_placeholders() -> None:
    text = render_template("第{round_number}轮：{messages}", round_number=2, messages="A；B")
    assert text == "第2轮：A；B"


def test_build_semantic_extract_prompt_includes_episodes() -> None:
    report = {
        "episodes": [
            {
                "round_number": 1,
                "key_event_messages": ["1号发言"],
                "decision_event_messages": ["1号投给3号"],
            }
        ]
    }
    prompt = build_semantic_extract_prompt(report, won=True)
    assert "策略经验" in prompt
    assert "胜利" in prompt
    assert "第1轮" in prompt
    assert "1号发言" in prompt


def test_build_replay_prompt_includes_turning_points(tmp_path: Path) -> None:
    from llm_werewolf.evaluation.post_game.run_context import PlayerRosterEntry, RunContext

    ctx = RunContext(
        run_dir=tmp_path,
        winner_camp="villager",
        prompt_version="v1",
        game_result_text="好人胜",
        roster={"p1": PlayerRosterEntry("p1", "Alice", "Seer", "villager")},
        events=[
            {
                "event_type": "werewolf_killed",
                "round_number": 1,
                "data": {"target_id": "p1"},
            },
            {
                "event_type": "game_ended",
                "round_number": 2,
                "data": {},
            },
        ],
    )
    prompt = build_replay_prompt(ctx, mvp_payload={"data_quality": {"confidence": "high"}})
    assert "关键转折时间线" in prompt
    assert "第 1 夜" in prompt


def test_build_replay_prompt_uses_template_sections(tmp_path: Path) -> None:
    from llm_werewolf.evaluation.post_game.run_context import RunContext

    ctx = RunContext(
        run_dir=tmp_path,
        winner_camp="villager",
        prompt_version="v1",
        game_result_text="好人胜",
        events=[],
    )
    mvp_payload = {
        "mvp": {
            "player_id": "p1",
            "player_name": "Alice",
            "role_name": "Seer",
            "camp": "good",
            "mvp_total": 88,
        },
        "players": [
            {
                "player_id": "p1",
                "rank": 1,
                "player_name": "Alice",
                "mvp_total": 88,
                "breakdown_raw": {"a": 1},
                "golden_speech_candidates": [
                    {"kind": "speech", "round_number": 2, "excerpt": "我是预言家"},
                ],
            }
        ],
        "data_quality": {
            "has_vote_intentions": True,
            "has_wolf_team_channel": False,
            "confidence": "medium",
        },
    }
    prompt = build_replay_prompt(ctx, mvp_payload=mvp_payload)
    assert "分维度材料" in prompt
    assert "胜负阵营: villager" in prompt
    assert "输出要求" in prompt
    assert "prompt_role_key" in prompt
    assert "Alice" in prompt
    assert "MVP 规则评分" in prompt
    assert "我是预言家" in prompt
    assert "公开投票意向" in prompt
    assert "summary_zh" in prompt
