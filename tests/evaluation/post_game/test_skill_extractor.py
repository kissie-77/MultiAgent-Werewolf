"""Skill 生成规则与 MD 写入测试。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.post_game.skill_extractor import (
    build_role_skills,
    write_role_skills_artifacts,
)
from llm_werewolf.evaluation.post_game.skill_generation_rules import (
    evaluate_persuasion_speech,
    collect_skill_generation_candidates,
)
from llm_werewolf.evaluation.post_game.skill_md import render_skill_markdown
from llm_werewolf.evaluation.post_game.camp_persuasion import CampSpeechInfluence
from llm_werewolf.agent_team.skill_loader import format_role_skills_section, load_role_skills


def _fixture_events() -> list[dict]:
    return [
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
                "public_speech": "五号发言像狼，今天先投五号，大家跟票",
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
            "event_type": "player_eliminated",
            "round_number": 1,
            "phase": "day_voting",
            "data": {"player_id": "player_5", "role": "Guard"},
        },
        {
            "event_type": "player_eliminated",
            "round_number": 1,
            "phase": "day_voting",
            "data": {"player_id": "player_2", "role": "Werewolf"},
        },
        {
            "event_type": "game_ended",
            "round_number": 1,
            "phase": "ended",
            "data": {"winner_camp": "werewolf", "winner_ids": ["player_2"]},
        },
    ]


def test_render_skill_markdown_has_frontmatter() -> None:
    skill = {
        "skill_id": "wolf_test",
        "prompt_role_key": "wolf",
        "status": "draft",
        "source_run": "runs/test",
        "skill_card": {
            "title_zh": "测试 Skill",
            "when_to_use": "白天",
            "public_behavior": "明确票型",
            "avoid": "空泛",
        },
        "rationale": "测试依据",
    }
    md = render_skill_markdown(skill)
    assert md.startswith("---")
    assert "skill_id: wolf_test" in md
    assert "# 测试 Skill" in md


def test_persuasion_rule_rejects_short_speech() -> None:
    speech = CampSpeechInfluence(
        speaker_id="p1",
        speaker_name="A",
        speaker_camp="villager",
        round_number=1,
        phase="day",
        public_speech="嗯",
        swing_count=1,
        camp_aligned_swings=1,
        camp_aligned_score=10,
        matched_round_elimination=False,
    )
    result = evaluate_persuasion_speech(speech)
    assert not result.passed
    assert "insufficient_material" in result.reason


def test_persuasion_rule_rejects_no_influence() -> None:
    speech = CampSpeechInfluence(
        speaker_id="p1",
        speaker_name="A",
        speaker_camp="villager",
        round_number=1,
        phase="day",
        public_speech="这是一段足够长的发言但没有说服效果",
        swing_count=0,
        camp_aligned_swings=0,
        camp_aligned_score=0,
        matched_round_elimination=False,
    )
    result = evaluate_persuasion_speech(speech)
    assert not result.passed
    assert "insufficient_influence" in result.reason


def test_write_role_skills_only_generates_passed_candidates(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    from llm_werewolf.evaluation.post_game.vote_swing_analysis import _records_from_events

    records = _records_from_events(events)
    (tmp_path / "vote_intentions.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
        encoding="utf-8",
    )

    agent_root = tmp_path / "agent_skills"
    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)
    write_role_skills_artifacts(ctx, camp, agent_skills_root=agent_root)

    payload = json.loads((tmp_path / "role_skills.json").read_text(encoding="utf-8"))
    assert payload["extraction_mode"] == "generation_rules"
    assert payload["generation_rules"]["score_filter"] == "disabled"
    assert payload["skill_count"] == len(payload["skills"])
    assert payload["skill_count"] >= 1
    assert payload["skill_count"] < 7
    assert all(s["status"] == "draft" for s in payload["skills"])
    assert payload["skipped_identities"]
    assert (tmp_path / "skills").is_dir()
    assert list((tmp_path / "skills").glob("*.md"))


def test_build_role_skills_no_placeholder_for_all_roles(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    from llm_werewolf.evaluation.post_game.vote_swing_analysis import _records_from_events

    records = _records_from_events(events)
    (tmp_path / "vote_intentions.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
        encoding="utf-8",
    )
    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)
    candidates = collect_skill_generation_candidates(ctx, camp)
    assert len(candidates) >= 1
    payload = build_role_skills(ctx, camp)
    role_keys = {s["prompt_role_key"] for s in payload["skills"]}
    assert "wolf" in role_keys or len(role_keys) >= 1
    assert "prophet" not in role_keys or "prophet" in {c.prompt_role_key for c in candidates}


def test_night_action_generates_skill(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "seer_checked",
            "round_number": 1,
            "phase": "night",
            "message": "预言家查验",
            "data": {"player_id": "player_3", "target_id": "player_5", "result": "villager"},
        },
        {
            "event_type": "player_eliminated",
            "round_number": 1,
            "phase": "day_voting",
            "data": {"player_id": "player_3", "role": "Seer"},
        },
        {
            "event_type": "game_ended",
            "round_number": 1,
            "phase": "ended",
            "data": {"winner_camp": "villager", "winner_ids": []},
        },
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    ctx = load_run_context(tmp_path)
    from llm_werewolf.evaluation.post_game.run_context import PlayerRosterEntry

    ctx.roster["player_3"] = PlayerRosterEntry(
        player_id="player_3",
        player_name="预言家",
        role_name="Seer",
        camp="villager",
    )
    camp = build_camp_persuasion_report(ctx)
    payload = build_role_skills(ctx, camp)
    assert payload["skill_count"] == 1
    assert payload["skills"][0]["source_kind"] == "night_action"
    assert payload["skills"][0]["prompt_role_key"] == "prophet"


def test_skill_loader_reads_agent_library(tmp_path: Path, monkeypatch) -> None:
    from llm_werewolf.agent_team import skill_loader

    root = tmp_path / "skills"
    wolf_dir = root / "wolf"
    wolf_dir.mkdir(parents=True)
    (wolf_dir / "wolf_demo.md").write_text(
        "---\nskill_id: wolf_demo\nprompt_role_key: wolf\nstatus: draft\n---\n\n"
        "# 演示\n\n## 何时使用\n首夜\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    items = load_role_skills("wolf")
    assert len(items) == 1
    assert items[0]["skill_id"] == "wolf_demo"

    section = format_role_skills_section("wolf")
    assert "对局经验 Skill" in section
    assert "首夜" in section
