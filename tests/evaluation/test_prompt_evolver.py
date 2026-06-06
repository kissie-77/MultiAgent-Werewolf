import json
from pathlib import Path

from llm_werewolf.evaluation.evolution.prompt_evolver import evolve_prompt_from_run
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.strategy.registry.role_prompt_registry import register_role_prompt_search_root


def _evolved_wolf_version(result) -> str:
    assert result.changed_prompt_roles is not None
    return result.changed_prompt_roles["wolf"]["after"]


def test_evolve_prompt_from_run_generates_runtime_readable_version(tmp_path: Path) -> None:
    run_dir = tmp_path / "v1_initial"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir.joinpath("prompt_proposals.json").write_text(
        json.dumps(
            {
                "schema": "prompt_proposals_v3",
                "prompt_version_base": "v1",
                "proposal_count": 2,
                "proposals": [
                    {
                        "proposal_id": "demo_rule",
                        "prompt_role_key": "wolf",
                        "target_variable": "v2.role.wolf",
                        "status": "draft",
                        "kind": "positive_persuasion",
                        "priority": 1,
                        "confidence_score": 0.91,
                        "evidence": {"matched_round_elimination": True},
                        "suggested_patch": {
                            "section": "vote_closing",
                            "target_field": "phase_strategies.vote_closing",
                            "action": "update_rule",
                            "text_zh": "测试采纳建议：归票时必须给出单一目标和备选回查。",
                        },
                    },
                    {
                        "proposal_id": "demo_example",
                        "prompt_role_key": "wolf",
                        "target_variable": "v2.role.wolf",
                        "status": "draft",
                        "kind": "mvp_golden_quote",
                        "priority": 2,
                        "confidence_score": 0.88,
                        "evidence": {"matched_elimination": True},
                        "suggested_patch": {
                            "section": "examples",
                            "target_field": "examples",
                            "action": "promote_quote_to_example",
                            "text_zh": "测试金句：我今天先归3号，明天回查跟票最慢的人。",
                        },
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    output_root = tmp_path / "prompt_versions"
    result = evolve_prompt_from_run(
        run_dir,
        base_prompt_version="v1",
        output_root=output_root,
    )
    register_role_prompt_search_root(output_root)

    assert result.applied_count == 2
    assert _evolved_wolf_version(result) == "v2"
    assert result.new_version_dir is not None
    assert (run_dir / "applied_prompt_proposals.json").is_file()
    assert (run_dir / "prompt_version_diff.json").is_file()
    assert (run_dir / "prompt_evidence_ledger.json").is_file()
    assert (
        (run_dir / "new_prompt_version.txt").read_text(encoding="utf-8")
        == result.new_prompt_version
    )

    wolf = PromptManager.get_role_strategy_config(
        "wolf",
        prompt_version=_evolved_wolf_version(result),
    )
    assert "vote_closing: 测试采纳建议" in wolf["phase_strategies"]
    assert "测试金句" in wolf["examples"]


def test_evolve_prompt_from_run_keeps_version_when_no_applicable_proposals(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "v1_initial"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir.joinpath("prompt_proposals.json").write_text(
        json.dumps(
            {
                "schema": "prompt_proposals_v3",
                "proposals": [
                    {
                        "proposal_id": "ignored",
                        "target_variable": "v2.role.wolf",
                        "status": "rejected",
                        "kind": "positive_persuasion",
                        "priority": 1,
                        "confidence_score": 0.95,
                        "suggested_patch": {
                            "section": "vote_closing",
                            "target_field": "phase_strategies.vote_closing",
                            "action": "update_rule",
                            "text_zh": "不会采纳",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = evolve_prompt_from_run(
        run_dir,
        base_prompt_version="v1",
        output_root=tmp_path / "prompt_versions",
    )

    assert result.applied_count == 0
    assert result.new_prompt_version == "v1"
    applied = json.loads(
        (run_dir / "applied_prompt_proposals.json").read_text(encoding="utf-8")
    )
    assert applied["skipped_reason"] == "no_applicable_prompt_proposals"
    ledger = json.loads(
        (run_dir / "prompt_evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert ledger["schema"] == "prompt_evidence_ledger_v1"


def test_evolve_prompt_from_run_appends_forbidden_rule_to_role_card(tmp_path: Path) -> None:
    run_dir = tmp_path / "v1_initial"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir.joinpath("prompt_proposals.json").write_text(
        json.dumps(
            {
                "schema": "prompt_proposals_v3",
                "prompt_version_base": "v1",
                "proposal_count": 1,
                "proposals": [
                    {
                        "proposal_id": "bad_case_wolf",
                        "prompt_role_key": "wolf",
                        "target_variable": "v2.role.wolf",
                        "status": "draft",
                        "kind": "bad_case_rule",
                        "priority": 1,
                        "confidence_score": 0.84,
                        "suggested_patch": {
                            "section": "forbidden_actions",
                            "target_field": "forbidden_actions",
                            "action": "add_forbidden_rule",
                            "text_zh": "禁止白天只报座位号或极短结论；发言至少包含目标、依据、以及后续回查方向中的两项。",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    output_root = tmp_path / "prompt_versions"
    result = evolve_prompt_from_run(
        run_dir,
        base_prompt_version="v1",
        output_root=output_root,
    )
    register_role_prompt_search_root(output_root)

    assert result.applied_count == 1
    wolf = PromptManager.get_role_strategy_config(
        "wolf",
        prompt_version=_evolved_wolf_version(result),
    )
    assert "禁止白天只报座位号或极短结论" in wolf["forbidden_actions"]


def test_evolve_prompt_replaces_same_family_forbidden_rule(tmp_path: Path) -> None:
    run_dir = tmp_path / "v1_initial"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir.joinpath("prompt_proposals.json").write_text(
        json.dumps(
            {
                "schema": "prompt_proposals_v3",
                "prompt_version_base": "v1",
                "proposal_count": 1,
                "proposals": [
                    {
                        "proposal_id": "replace_forbidden_rule",
                        "prompt_role_key": "wolf",
                        "target_variable": "v2.role.wolf",
                        "status": "draft",
                        "kind": "bad_case_rule",
                        "priority": 1,
                        "confidence_score": 0.84,
                        "suggested_patch": {
                            "section": "forbidden_actions",
                            "target_field": "forbidden_actions",
                            "action": "add_forbidden_rule",
                            "text_zh": "禁止白天只报座位号；发言时至少补齐目标、依据和次日回查中的两项。",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    output_root = tmp_path / "prompt_versions"
    result = evolve_prompt_from_run(
        run_dir,
        base_prompt_version="v1",
        output_root=output_root,
    )
    register_role_prompt_search_root(output_root)

    wolf = PromptManager.get_role_strategy_config(
        "wolf",
        prompt_version=_evolved_wolf_version(result),
    )
    assert "禁止白天只报座位号" in wolf["forbidden_actions"]
    assert wolf["forbidden_actions"].count("座位号") == 1


def test_evolve_prompt_replaces_same_family_example(tmp_path: Path) -> None:
    run_dir = tmp_path / "v1_initial"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir.joinpath("prompt_proposals.json").write_text(
        json.dumps(
            {
                "schema": "prompt_proposals_v3",
                "prompt_version_base": "v1",
                "proposal_count": 1,
                "proposals": [
                    {
                        "proposal_id": "replace_example",
                        "prompt_role_key": "wolf",
                        "target_variable": "v2.role.wolf",
                        "status": "draft",
                        "kind": "mvp_golden_quote",
                        "priority": 1,
                        "confidence_score": 0.9,
                        "evidence": {"matched_elimination": True},
                        "suggested_patch": {
                            "section": "examples",
                            "target_field": "examples",
                            "action": "promote_quote_to_example",
                            "text_zh": "新版归票示例：我今天先归3号，明天优先回查最后跟票的玩家。",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    output_root = tmp_path / "prompt_versions"
    result = evolve_prompt_from_run(
        run_dir,
        base_prompt_version="v1",
        output_root=output_root,
    )
    register_role_prompt_search_root(output_root)

    wolf = PromptManager.get_role_strategy_config(
        "wolf",
        prompt_version=_evolved_wolf_version(result),
    )
    assert "新版归票示例" in wolf["examples"]
    assert wolf["examples"].count("归票") == 1


def test_evolve_prompt_skips_positive_without_matched_elimination(tmp_path: Path) -> None:
    run_dir = tmp_path / "v1_initial"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir.joinpath("prompt_proposals.json").write_text(
        json.dumps(
            {
                "schema": "prompt_proposals_v3",
                "prompt_version_base": "v1",
                "proposal_count": 1,
                "proposals": [
                    {
                        "proposal_id": "high_conf_no_match",
                        "prompt_role_key": "wolf",
                        "target_variable": "v2.role.wolf",
                        "status": "draft",
                        "kind": "positive_persuasion",
                        "priority": 1,
                        "confidence_score": 0.91,
                        "evidence": {"matched_round_elimination": False},
                        "suggested_patch": {
                            "section": "vote_closing",
                            "target_field": "phase_strategies.vote_closing",
                            "action": "update_rule",
                            "text_zh": "高置信但未 matched 的规则不应采纳。",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = evolve_prompt_from_run(
        run_dir,
        base_prompt_version="v1",
        output_root=tmp_path / "prompt_versions",
    )

    assert result.applied_count == 0


def test_evolve_prompt_skips_low_confidence_proposals(tmp_path: Path) -> None:
    run_dir = tmp_path / "v1_initial"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir.joinpath("prompt_proposals.json").write_text(
        json.dumps(
            {
                "schema": "prompt_proposals_v3",
                "prompt_version_base": "v1",
                "proposal_count": 1,
                "proposals": [
                    {
                        "proposal_id": "low_confidence_rule",
                        "prompt_role_key": "wolf",
                        "target_variable": "v2.role.wolf",
                        "status": "draft",
                        "kind": "positive_persuasion",
                        "priority": 1,
                        "confidence_score": 0.42,
                        "suggested_patch": {
                            "section": "vote_closing",
                            "target_field": "phase_strategies.vote_closing",
                            "action": "update_rule",
                            "text_zh": "低置信度规则：这里不该被自动采纳。",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = evolve_prompt_from_run(
        run_dir,
        base_prompt_version="v1",
        output_root=tmp_path / "prompt_versions",
    )

    assert result.applied_count == 0
    applied = json.loads(
        (run_dir / "applied_prompt_proposals.json").read_text(encoding="utf-8")
    )
    assert applied["skipped_reason"] == "no_applicable_prompt_proposals"
    assert applied["skipped_low_confidence"][0]["proposal_id"] == "low_confidence_rule"
    ledger = json.loads(
        (run_dir / "prompt_evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert ledger["entries"][0]["status"] == "skipped_low_confidence"


def test_evolve_prompt_uses_history_support_to_raise_confidence(tmp_path: Path) -> None:
    history_dir = tmp_path / "v0_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_dir.joinpath("prompt_proposals.json").write_text(
        json.dumps(
            {
                "schema": "prompt_proposals_v3",
                "proposals": [
                    {
                        "proposal_id": "history_rule",
                        "prompt_role_key": "wolf",
                        "target_variable": "v2.role.wolf",
                        "status": "draft",
                        "kind": "positive_persuasion",
                        "priority": 1,
                        "confidence_score": 0.5,
                        "suggested_patch": {
                            "section": "vote_closing",
                            "target_field": "phase_strategies.vote_closing",
                            "action": "update_rule",
                            "text_zh": "历史支持规则：归票时要给出单一目标和次日回查。",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    run_dir = tmp_path / "v1_initial"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir.joinpath("prompt_proposals.json").write_text(
        json.dumps(
            {
                "schema": "prompt_proposals_v3",
                "prompt_version_base": "v1",
                "proposal_count": 1,
                "proposals": [
                    {
                        "proposal_id": "current_rule",
                        "prompt_role_key": "wolf",
                        "target_variable": "v2.role.wolf",
                        "status": "draft",
                        "kind": "positive_persuasion",
                        "priority": 1,
                        "confidence_score": 0.63,
                        "evidence": {"matched_round_elimination": True},
                        "suggested_patch": {
                            "section": "vote_closing",
                            "target_field": "phase_strategies.vote_closing",
                            "action": "update_rule",
                            "text_zh": "历史支持规则：归票时要给出单一目标和次日回查。",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = evolve_prompt_from_run(
        run_dir,
        base_prompt_version="v1",
        output_root=tmp_path / "prompt_versions",
        min_confidence_score=0.68,
    )
    register_role_prompt_search_root(tmp_path / "prompt_versions")

    assert result.applied_count == 1
    applied = json.loads(
        (run_dir / "applied_prompt_proposals.json").read_text(encoding="utf-8")
    )
    assert applied["applied"][0]["history_support_count"] >= 1
    assert applied["applied"][0]["effective_confidence_score"] >= 0.68
    ledger = json.loads(
        (run_dir / "prompt_evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert any(entry["status"] == "applied" for entry in ledger["entries"])
