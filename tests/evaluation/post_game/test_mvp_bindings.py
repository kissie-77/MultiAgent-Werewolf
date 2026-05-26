"""MVP 金句 → Prompt 提案 / Skill 卡片绑定测试。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
from llm_werewolf.evaluation.post_game.prompt_proposal import build_prompt_proposals
from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.post_game.skill_extractor import build_role_skills


def _write_minimal_run(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "vote_intention_snapshot",
            "round_number": 1,
            "phase": "day_discussion",
            "data": {
                "round_number": 1,
                "phase": "day_discussion",
                "channel": "public",
                "speaker_id": "player_2",
                "speaker_name": "B",
                "public_speech": "五号像狼，今天全票出五号，理由是他上轮划水",
                "before": {
                    "player_1": {
                        "player_id": "player_1",
                        "player_name": "A",
                        "seat": 0,
                        "target_id": None,
                    },
                },
                "after": {
                    "player_1": {
                        "player_id": "player_1",
                        "player_name": "A",
                        "seat": 5,
                        "target_id": "player_5",
                    },
                },
                "swings": [
                    {
                        "player_id": "player_1",
                        "player_name": "A",
                        "from_seat": 0,
                        "to_seat": 5,
                        "from_target_id": None,
                        "to_target_id": "player_5",
                    },
                ],
                "swing_count": 1,
            },
        },
        {
            "event_type": "game_ended",
            "round_number": 1,
            "phase": "ended",
            "data": {"winner_camp": "werewolf", "winner_ids": ["player_2"]},
        },
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    mvp = {
        "schema": "mvp_scores_v2",
        "mvp": {"player_id": "player_2", "player_name": "B"},
        "dimension_context_paths": {
            "persuasion": "views/score_contexts/persuasion.md",
            "wolf_night": "views/score_contexts/wolf_night.md",
        },
        "players": [
            {
                "player_id": "player_2",
                "player_name": "B",
                "role_name": "Werewolf",
                "prompt_role_key": "werewolf",
                "camp": "werewolf",
                "rank": 1,
                "golden_speech_candidates": [
                    {
                        "kind": "public_persuasion",
                        "round_number": 1,
                        "phase": "day_discussion",
                        "excerpt": "五号像狼，今天全票出五号，理由是他上轮划水",
                        "score": 18.5,
                        "matched_elimination": True,
                    },
                ],
            },
        ],
        "wolf_night_analysis": {
            "speeches": [
                {
                    "speaker_id": "player_2",
                    "speaker_name": "B",
                    "round_number": 1,
                    "phase": "night",
                    "public_speech": "今晚刀五号，女巫没药就抗推他",
                    "speech_total": 22.0,
                    "plan_clarity": 0.8,
                },
            ],
        },
    }
    (tmp_path / "mvp_scores.json").write_text(
        json.dumps(mvp, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_prompt_proposals_bind_mvp_golden_quotes(tmp_path: Path) -> None:
    _write_minimal_run(tmp_path)
    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)
    payload = build_prompt_proposals(ctx, camp)

    assert payload["proposal_source"] == "mvp_golden_quotes"
    assert payload["mvp_player_id"] == "player_2"
    prop = payload["proposals"][0]
    assert prop["kind"] == "mvp_golden_speech"
    assert prop["mvp_binding"]["is_overall_mvp_player"] is True
    assert "五号像狼" in prop["suggested_patch"]["text_zh"]
    assert prop.get("background")
    assert prop.get("applicable_scenario")
    assert len(prop.get("citations", [])) >= 2


def test_llm_suggestions_in_prompt_proposals(tmp_path: Path) -> None:
    _write_minimal_run(tmp_path)
    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)
    analysis = {
        "mode": "llm",
        "summary_zh": "狼人发言推动票型一致",
        "prompt_suggestions": ["白天先报清票型再展开理由"],
        "risks": ["空泛发言"],
    }
    payload = build_prompt_proposals(ctx, camp, llm_analysis=analysis)
    kinds = {p["kind"] for p in payload["proposals"]}
    assert "llm_suggestion" in kinds
    llm_prop = next(p for p in payload["proposals"] if p["kind"] == "llm_suggestion")
    assert "票型" in llm_prop["suggested_patch"]["text_zh"]


def test_role_skills_include_background_and_citations(tmp_path: Path) -> None:
    _write_minimal_run(tmp_path)
    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)
    payload = build_role_skills(ctx, camp)

    assert payload["schema"] == "role_skills_v2"
    assert payload["skill_count"] >= 1

    with_ctx = [s for s in payload["skills"] if s.get("citations")]
    assert with_ctx, "至少一条 Skill 应带 citations"
    card = with_ctx[0]["skill_card"]
    assert card.get("background")
    assert card.get("applicable_scenario") or card.get("when_to_use")

    wolf = [s for s in payload["skills"] if s["source_kind"] == "wolf_night_plan"]
    if wolf:
        assert wolf[0]["skill_card"].get("background")
        assert "狼队" in wolf[0]["skill_card"]["applicable_scenario"]
