"""Skill 生成规则与 MD 写入测试。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.post_game.run_context import load_run_context
from llm_werewolf.evaluation.post_game.camp_persuasion import (
    CampSpeechInfluence,
    build_camp_persuasion_report,
)
from llm_werewolf.agent_team.skill_support.skill_loader import (
    load_role_skills,
    format_role_skills_section,
)
from llm_werewolf.evaluation.post_game.skill_generation.skill_md import render_skill_markdown
from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import (
    build_role_skills,
    write_role_skills_artifacts,
)
from llm_werewolf.evaluation.post_game.skill_generation.skill_generation_rules import (
    evaluate_persuasion_speech,
    collect_skill_generation_candidates,
)


def _role_skill_dir(root: Path, role: str, version: str = "v1") -> Path:
    path = root / role / version
    path.mkdir(parents=True, exist_ok=True)
    return path


def _fixture_events() -> list[dict]:
    return [
        {
            "event_type": "role_acting",
            "round_number": 1,
            "phase": "night",
            "data": {"player_id": "player_2", "role": "Werewolf", "player_name": "B"},
        },
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
                    }
                },
                "after": {
                    "player_1": {
                        "player_id": "player_1",
                        "player_name": "A",
                        "seat": 5,
                        "target_id": "player_5",
                    }
                },
                "swings": [
                    {
                        "player_id": "player_1",
                        "player_name": "A",
                        "from_seat": 0,
                        "to_seat": 5,
                        "from_target_id": None,
                        "to_target_id": "player_5",
                    }
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
        "source_run": "artifacts/runs/test",
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
    from llm_werewolf.evaluation.post_game.run_context import RunContext

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
    ctx = RunContext(run_dir=Path("."))
    result = evaluate_persuasion_speech(speech, ctx)
    assert not result.passed
    assert "insufficient_material" in result.reason


def test_persuasion_rule_rejects_no_influence() -> None:
    from llm_werewolf.evaluation.post_game.run_context import RunContext

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
    ctx = RunContext(run_dir=Path("."))
    result = evaluate_persuasion_speech(speech, ctx)
    assert not result.passed
    assert "did not help" in result.reason


def test_write_role_skills_only_generates_passed_candidates(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    from llm_werewolf.evaluation.core.vote_swing_analysis import _records_from_events

    records = _records_from_events(events)
    (tmp_path / "vote_intentions.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8"
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
    assert all(s["status"] in {"draft", "active", "deprecated"} for s in payload["skills"])
    assert any(s["status"] == "active" for s in payload["skills"])
    assert payload["skipped_identities"]
    assert (tmp_path / "skills").is_dir()
    assert list((tmp_path / "skills").glob("*.md"))


def test_build_role_skills_no_placeholder_for_all_roles(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    from llm_werewolf.evaluation.core.vote_swing_analysis import _records_from_events

    records = _records_from_events(events)
    (tmp_path / "vote_intentions.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8"
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
            "data": {"player_id": "player_3", "target_id": "player_5", "result": "werewolf"},
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
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    ctx = load_run_context(tmp_path)
    from llm_werewolf.evaluation.post_game.run_context import PlayerRosterEntry

    ctx.roster["player_3"] = PlayerRosterEntry(
        player_id="player_3", player_name="预言家", role_name="Seer", camp="villager"
    )
    camp = build_camp_persuasion_report(ctx)
    payload = build_role_skills(ctx, camp)
    assert payload["skill_count"] == 1
    assert payload["skills"][0]["source_kind"] == "night_action"
    assert payload["skills"][0]["prompt_role_key"] == "prophet"


def test_night_action_dedupes_same_role_event_type(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "seer_checked",
            "round_number": 1,
            "phase": "night",
            "data": {"player_id": "player_3", "target_id": "player_5", "result": "villager"},
        },
        {
            "event_type": "seer_checked",
            "round_number": 2,
            "phase": "night",
            "data": {"player_id": "player_3", "target_id": "player_1", "result": "werewolf"},
        },
        {
            "event_type": "game_ended",
            "round_number": 2,
            "phase": "ended",
            "data": {"winner_camp": "villager", "winner_ids": []},
        },
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    ctx = load_run_context(tmp_path)
    from llm_werewolf.evaluation.post_game.run_context import PlayerRosterEntry

    ctx.roster["player_3"] = PlayerRosterEntry(
        player_id="player_3", player_name="预言家", role_name="Seer", camp="villager"
    )
    camp = build_camp_persuasion_report(ctx)
    payload = build_role_skills(ctx, camp)
    assert payload["skill_count"] == 1
    assert payload["skills"][0]["evidence"]["target_id"] == "player_1"


def test_skill_card_has_role_strategy_content(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "seer_checked",
            "round_number": 1,
            "phase": "night",
            "data": {"player_id": "player_3", "target_id": "player_5", "result": "werewolf"},
        },
        {
            "event_type": "game_ended",
            "round_number": 1,
            "phase": "ended",
            "data": {"winner_camp": "villager", "winner_ids": []},
        },
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    ctx = load_run_context(tmp_path)
    from llm_werewolf.evaluation.post_game.run_context import PlayerRosterEntry

    ctx.roster["player_3"] = PlayerRosterEntry(
        player_id="player_3", player_name="预言家", role_name="Seer", camp="villager"
    )
    camp = build_camp_persuasion_report(ctx)
    payload = build_role_skills(ctx, camp)
    card = payload["skills"][0]["skill_card"]
    assert len(card["public_behavior"]) > 40
    assert "①" in card["public_behavior"]
    assert "避免" in card["avoid"] or "①" in card["avoid"]
    md = render_skill_markdown(payload["skills"][0])
    assert "## 本局决策" in md


def test_reference_skills_from_local_run(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "player_eliminated",
            "round_number": 1,
            "phase": "day_voting",
            "data": {"player_id": "player_6", "role": "Seer"},
        },
        {
            "event_type": "player_eliminated",
            "round_number": 1,
            "phase": "day_voting",
            "data": {"player_id": "player_12", "role": "WolfKing"},
        },
        {
            "event_type": "player_eliminated",
            "round_number": 1,
            "phase": "day_voting",
            "data": {"player_id": "player_4", "role": "Guard"},
        },
        {
            "event_type": "seer_checked",
            "round_number": 1,
            "phase": "night",
            "data": {"player_id": "player_6", "target_id": "player_12", "result": "werewolf"},
        },
        {
            "event_type": "guard_protected",
            "round_number": 1,
            "phase": "night",
            "data": {"player_id": "player_4", "target_id": "player_6"},
        },
        {
            "event_type": "werewolf_killed",
            "round_number": 1,
            "phase": "night",
            "data": {"target_id": "player_4"},
        },
        {
            "event_type": "player_discussion",
            "round_number": 1,
            "phase": "night",
            "data": {
                "player_id": "player_1",
                "speech": "首夜建议刀四号，偏神职位。",
                "role": "Werewolf",
            },
        },
        {
            "event_type": "game_ended",
            "round_number": 1,
            "phase": "ended",
            "data": {"winner_camp": "werewolf", "winner_ids": []},
        },
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    from llm_werewolf.evaluation.post_game.skill_generation.reference_skills import (
        build_reference_skills,
    )

    skills = build_reference_skills(tmp_path)
    roles = {s["prompt_role_key"] for s in skills}
    assert "prophet" in roles
    assert "guard" in roles
    assert "wolf" in roles
    prophet = next(s for s in skills if s["prompt_role_key"] == "prophet")
    assert "狼人" in prophet["skill_card"]["public_behavior"]
    assert prophet["status"] == "active"
    assert all(len(s["skill_card"]["public_behavior"]) > 40 for s in skills)


def test_skill_loader_reads_agent_library(tmp_path: Path, monkeypatch) -> None:
    from llm_werewolf.agent_team.skill_support import skill_loader

    root = tmp_path / "skills"
    wolf_dir = _role_skill_dir(root, "wolf")
    (wolf_dir / "wolf_demo.md").write_text(
        "---\nskill_id: wolf_demo\nprompt_role_key: wolf\nstatus: active\n---\n\n"
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


def test_skill_loader_sorts_by_weight_descending(tmp_path: Path, monkeypatch) -> None:
    from llm_werewolf.agent_team.skill_support import skill_loader

    root = tmp_path / "skills"
    wolf_dir = _role_skill_dir(root, "wolf")

    (wolf_dir / "low.md").write_text(
        "---\nskill_id: low\nprompt_role_key: wolf\nstatus: active\nweight: 0.5\n---\n\n# 低权重\n",
        encoding="utf-8",
    )
    (wolf_dir / "high.md").write_text(
        "---\nskill_id: high\nprompt_role_key: wolf\nstatus: active\nweight: 2.0\n---\n\n# 高权重\n",
        encoding="utf-8",
    )
    (wolf_dir / "mid.md").write_text(
        "---\nskill_id: mid\nprompt_role_key: wolf\nstatus: active\nweight: 1.0\n---\n\n# 中权重\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    items = load_role_skills("wolf", max_skills=10)
    assert len(items) == 3
    assert items[0]["skill_id"] == "high"
    assert items[1]["skill_id"] == "mid"
    assert items[2]["skill_id"] == "low"


def test_skill_loader_defaults_weight_to_one(tmp_path: Path, monkeypatch) -> None:
    from llm_werewolf.agent_team.skill_support import skill_loader

    root = tmp_path / "skills"
    wolf_dir = _role_skill_dir(root, "wolf")

    (wolf_dir / "no_weight.md").write_text(
        "---\nskill_id: no_weight\nprompt_role_key: wolf\nstatus: active\n---\n\n# 无权重\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    items = load_role_skills("wolf")
    assert len(items) == 1
    assert items[0]["weight"] == 1.0


def test_skill_loader_reads_when_to_use_from_frontmatter(
    tmp_path: Path, monkeypatch
) -> None:
    from llm_werewolf.agent_team.skill_support import skill_loader

    root = tmp_path / "skills"
    prophet_dir = _role_skill_dir(root, "prophet")
    (prophet_dir / "prophet_demo.md").write_text(
        "---\nskill_id: prophet_demo\nprompt_role_key: prophet\nstatus: active\n"
        "when_to_use: 第1轮夜间，面临同类技能抉择且信息边界与当时一致时\n---\n\n"
        "# 预言家有效查验决策\n\n"
        "## 提取依据\n"
        "具体内容\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    items = load_role_skills("prophet")
    section = format_role_skills_section("prophet")

    assert len(items) == 1
    assert items[0]["description"].endswith("的情况下，使用该 skill")
    assert items[0]["description"] in section


def test_semantic_memory_updates_skill_markdown_weight(tmp_path: Path, monkeypatch) -> None:
    from llm_werewolf.agent_team.skill_support import skill_loader
    from llm_werewolf.agent_team.memory.semantic_memory import SemanticMemory

    root = tmp_path / "skills"
    wolf_dir = _role_skill_dir(root, "wolf")
    skill_path = wolf_dir / "wolf_demo.md"
    skill_path.write_text(
        "---\n"
        "skill_id: wolf_demo\n"
        "prompt_role_key: wolf\n"
        "status: active\n"
        "weight: 1.0\n"
        "win_count: 0\n"
        "use_count: 0\n"
        "---\n\n"
        "# Demo\n\n## 何时使用\n首夜优先统一刀口\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    memory = SemanticMemory()
    memory.update_after_game("wolf", won=True, used_card_ids=["wolf_demo"])

    text = skill_path.read_text(encoding="utf-8")
    assert "weight: 1.10" in text
    assert "win_count: 1" in text
    assert "use_count: 1" in text
    assert "updated_at:" in text


def test_is_trusted_source_run_rejects_pytest_paths() -> None:
    from llm_werewolf.agent_team.skill_support.skill_loader import is_trusted_source_run

    assert is_trusted_source_run("runs/12p-doubao-20260526-143527")
    assert not is_trusted_source_run("/tmp/pytest-of-user/test0/run")
    assert not is_trusted_source_run("artifacts/runs/local")


def test_is_eligible_for_agent_library_requires_quality_and_trusted_run() -> None:
    from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import (
        is_eligible_for_agent_library,
    )

    assert is_eligible_for_agent_library({
        "status": "draft",
        "source_run": "runs/demo",
        "quality_gate": {"passed": True},
    })
    assert not is_eligible_for_agent_library({
        "status": "draft",
        "source_run": "runs/demo",
        "quality_gate": {"passed": False},
    })
    assert not is_eligible_for_agent_library({
        "status": "draft",
        "source_run": "/private/var/pytest-of-x",
        "quality_gate": {"passed": True},
    })


def test_build_role_skills_activates_winning_camp_skills(tmp_path: Path) -> None:
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    from llm_werewolf.evaluation.core.vote_swing_analysis import _records_from_events

    records = _records_from_events(events)
    (tmp_path / "vote_intentions.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8"
    )
    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)

    payload = build_role_skills(ctx, camp)

    assert payload["skills"]
    wolf_skill = next(skill for skill in payload["skills"] if skill["camp"] == "werewolf")
    assert wolf_skill["status"] == "active"
    assert wolf_skill["weight"] >= 1.1
    assert wolf_skill["win_count"] >= 1


def test_load_role_skills_excludes_draft_by_default(tmp_path: Path, monkeypatch) -> None:
    from llm_werewolf.agent_team.skill_support import skill_loader

    root = tmp_path / "skills"
    role_dir = _role_skill_dir(root, "wolf")
    (role_dir / "active.md").write_text(
        "---\nskill_id: active\nprompt_role_key: wolf\nstatus: active\n---\n\n# A\n",
        encoding="utf-8",
    )
    (role_dir / "draft.md").write_text(
        "---\nskill_id: draft\nprompt_role_key: wolf\nstatus: draft\n---\n\n# D\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    items = load_role_skills("wolf")
    assert len(items) == 1
    assert items[0]["skill_id"] == "active"


def test_load_role_skills_excludes_deprecated(tmp_path: Path, monkeypatch) -> None:
    from llm_werewolf.agent_team.skill_support import skill_loader

    root = tmp_path / "skills"
    role_dir = _role_skill_dir(root, "wolf")
    (role_dir / "active.md").write_text(
        "---\nskill_id: active\nprompt_role_key: wolf\nstatus: active\n---\n\n# A\n",
        encoding="utf-8",
    )
    (role_dir / "deprecated.md").write_text(
        "---\nskill_id: deprecated\nprompt_role_key: wolf\nstatus: deprecated\n---\n\n# D\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    items = load_role_skills("wolf", include_draft=True, max_skills=10)
    assert len(items) == 1
    assert items[0]["skill_id"] == "active"


def test_build_system_prompt_includes_active_skills(tmp_path: Path, monkeypatch) -> None:
    from llm_werewolf.agent_team.agents.factory import build_system_prompt
    from llm_werewolf.agent_team.skill_support import skill_loader

    root = tmp_path / "skills"
    wolf_dir = _role_skill_dir(root, "wolf")
    (wolf_dir / "wolf_demo.md").write_text(
        "---\nskill_id: wolf_demo\nprompt_role_key: wolf\nstatus: active\n---\n\n"
        "# Demo\n\n## 何时使用\n首夜统一刀口\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    prompt = build_system_prompt(3, "Werewolf", "default")
    assert "对局经验 Skill" in prompt
    assert "wolf_demo" in prompt
    assert "首夜统一刀口" in prompt


# ── skill 状态流转测试 ──────────────────────────────────────────────


def test_update_skill_status_activates_on_high_weight() -> None:
    """weight >= 1.05 时，draft skill 应升为 active。"""
    from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import _update_skill_status

    skill = {"status": "draft", "weight": 1.10}
    _update_skill_status(skill)
    assert skill["status"] == "active"


def test_update_skill_status_deprecates_active_on_low_weight() -> None:
    """active skill 且 weight <= 0.95 时，应降为 deprecated。"""
    from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import _update_skill_status

    skill = {"status": "active", "weight": 0.90}
    _update_skill_status(skill)
    assert skill["status"] == "deprecated"


def test_update_skill_status_keeps_draft_in_middle_range() -> None:
    """draft skill 且 weight 在 (0.95, 1.05) 之间时，保持 draft。"""
    from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import _update_skill_status

    skill = {"status": "draft", "weight": 1.0}
    _update_skill_status(skill)
    assert skill["status"] == "draft"


def test_update_skill_status_keeps_active_in_middle_range() -> None:
    """active skill 且 weight 在 (0.95, 1.05) 之间时，保持 active。"""
    from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import _update_skill_status

    skill = {"status": "active", "weight": 1.0}
    _update_skill_status(skill)
    assert skill["status"] == "active"


def test_update_skill_status_does_not_deprecate_draft() -> None:
    """draft skill 即使 weight 很低也不降为 deprecated（只有 active 才会降）。"""
    from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import _update_skill_status

    skill = {"status": "draft", "weight": 0.50}
    _update_skill_status(skill)
    assert skill["status"] == "draft"


def test_update_skill_status_skips_skipped() -> None:
    """skipped 状态不做任何变更。"""
    from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import _update_skill_status

    skill = {"status": "skipped", "weight": 5.0}
    _update_skill_status(skill)
    assert skill["status"] == "skipped"


def test_update_skill_status_normalizes_unknown_status() -> None:
    """未知状态应被规范化为 draft。"""
    from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import _update_skill_status

    skill = {"status": "something_weird", "weight": 1.0}
    _update_skill_status(skill)
    assert skill["status"] == "draft"


def test_winning_skill_promotes_draft_to_active(tmp_path: Path) -> None:
    """对局结束后，获胜阵营的 draft skill 应被激活为 active。"""
    events = _fixture_events()
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8"
    )
    from llm_werewolf.evaluation.core.vote_swing_analysis import _records_from_events

    records = _records_from_events(events)
    (tmp_path / "vote_intentions.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8"
    )
    ctx = load_run_context(tmp_path)
    camp = build_camp_persuasion_report(ctx)

    payload = build_role_skills(ctx, camp)

    wolf_skills = [s for s in payload["skills"] if s["camp"] == "werewolf"]
    assert len(wolf_skills) > 0
    for skill in wolf_skills:
        assert skill["status"] == "active"
        assert skill["weight"] >= 1.05


def test_load_role_skills_include_draft_excludes_deprecated(
    tmp_path: Path, monkeypatch
) -> None:
    """include_draft=True 时加载 active + draft，但仍然排除 deprecated。"""
    from llm_werewolf.agent_team.skill_support import skill_loader

    root = tmp_path / "skills"
    role_dir = _role_skill_dir(root, "wolf")
    (role_dir / "a.md").write_text(
        "---\nskill_id: a\nprompt_role_key: wolf\nstatus: active\n---\n\n# A\n",
        encoding="utf-8",
    )
    (role_dir / "d.md").write_text(
        "---\nskill_id: d\nprompt_role_key: wolf\nstatus: draft\n---\n\n# D\n",
        encoding="utf-8",
    )
    (role_dir / "x.md").write_text(
        "---\nskill_id: x\nprompt_role_key: wolf\nstatus: deprecated\n---\n\n# X\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    items = load_role_skills("wolf", include_draft=True, max_skills=10)
    ids = [s["skill_id"] for s in items]
    assert "a" in ids
    assert "d" in ids
    assert "x" not in ids


def test_full_lifecycle_draft_active_deprecated(
    tmp_path: Path, monkeypatch
) -> None:
    """完整生命周期：draft → active（高权重）→ deprecated（低权重）。"""
    from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import _update_skill_status

    # 初始 draft
    skill = {"status": "draft", "weight": 1.0}
    _update_skill_status(skill)
    assert skill["status"] == "draft"

    # 模拟获胜，权重上升 → 激活
    skill["weight"] = 1.10
    _update_skill_status(skill)
    assert skill["status"] == "active"

    # 模拟连续失败，权重下降 → 废弃
    skill["weight"] = 0.90
    _update_skill_status(skill)
    assert skill["status"] == "deprecated"


def test_deprecated_skill_not_in_prompt(
    tmp_path: Path, monkeypatch
) -> None:
    """deprecated skill 不会出现在系统 prompt 中。"""
    from llm_werewolf.agent_team.agents.factory import build_system_prompt
    from llm_werewolf.agent_team.skill_support import skill_loader

    root = tmp_path / "skills"
    wolf_dir = _role_skill_dir(root, "wolf")
    (wolf_dir / "good.md").write_text(
        "---\nskill_id: good\nprompt_role_key: wolf\nstatus: active\n---\n\n# Good Skill\n",
        encoding="utf-8",
    )
    (wolf_dir / "old.md").write_text(
        "---\nskill_id: old\nprompt_role_key: wolf\nstatus: deprecated\n---\n\n# Old Skill\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    prompt = build_system_prompt(3, "Werewolf", "default")
    assert "good" in prompt
    assert "old" not in prompt


def test_find_matching_library_skill_by_when_to_use() -> None:
    from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import (
        find_matching_library_skill,
    )

    candidate = {"skill_card": {"when_to_use": "白天讨论时先归票可疑位"}}
    existing = [
        {
            "skill_id": "wolf_existing",
            "when_to_use": "白天讨论时先归票可疑位",
            "path": Path("wolf_existing.md"),
        }
    ]
    assert find_matching_library_skill(candidate, existing) is not None
    assert find_matching_library_skill(
        {"skill_card": {"when_to_use": "完全无关的场景"}},
        existing,
    ) is None


def test_merge_matching_when_to_use_updates_weight_without_version_bump(tmp_path: Path) -> None:
    from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import (
        write_skill_markdown_files,
    )

    agent_root = tmp_path / "library"
    wolf_dir = _role_skill_dir(agent_root, "wolf")
    existing_path = wolf_dir / "wolf_existing.md"
    existing_path.write_text(
        """---
skill_id: wolf_existing
prompt_role_key: wolf
status: active
weight: 1.0
when_to_use: 白天讨论时先归票可疑位
use_count: 0
---
# Existing

## 公开行为
旧行为
""",
        encoding="utf-8",
    )

    candidate = {
        "skill_id": "wolf_new_candidate",
        "prompt_role_key": "wolf",
        "status": "active",
        "source_run": "runs/demo-game",
        "quality_gate": {"passed": True},
        "weight": 1.1,
        "skill_card": {
            "title_zh": "新候选",
            "when_to_use": "白天讨论时先归票可疑位",
            "public_behavior": "补充新证据",
            "avoid": "",
        },
        "rationale": "本局验证",
    }

    write_skill_markdown_files(
        [candidate],
        run_skills_dir=tmp_path / "run_skills",
        agent_skills_root=agent_root,
    )

    assert candidate["library_action"] == "merged"
    assert candidate["merged_into_skill_id"] == "wolf_existing"
    assert not (agent_root / "wolf" / "v2").exists()
    updated = existing_path.read_text(encoding="utf-8")
    assert "weight: 1.15" in updated
    assert "补充新证据" in updated
    assert "旧行为" in updated


def test_new_when_to_use_creates_next_version(tmp_path: Path) -> None:
    from llm_werewolf.evaluation.post_game.skill_generation.skill_extractor import (
        write_skill_markdown_files,
    )

    agent_root = tmp_path / "library"
    wolf_dir = _role_skill_dir(agent_root, "wolf")
    (wolf_dir / "wolf_existing.md").write_text(
        """---
skill_id: wolf_existing
prompt_role_key: wolf
status: active
weight: 1.0
when_to_use: 已有场景
---
# Existing
""",
        encoding="utf-8",
    )

    candidate = {
        "skill_id": "wolf_brand_new",
        "prompt_role_key": "wolf",
        "status": "active",
        "source_run": "runs/demo-game",
        "quality_gate": {"passed": True},
        "weight": 1.1,
        "skill_card": {
            "title_zh": "全新 Skill",
            "when_to_use": "完全不同的使用场景",
            "public_behavior": "新策略",
            "avoid": "",
        },
    }

    write_skill_markdown_files(
        [candidate],
        run_skills_dir=tmp_path / "run_skills",
        agent_skills_root=agent_root,
    )

    assert candidate["library_action"] == "created"
    assert (agent_root / "wolf" / "v2" / "wolf_brand_new.md").is_file()
    assert (agent_root / "wolf" / "v2" / "wolf_existing.md").is_file()
