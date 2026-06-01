import json
from pathlib import Path

from llm_werewolf.evaluation.evolution.prompt_evolver import evolve_prompt_from_run
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.strategy.prompt_registry import register_prompt_search_root


def test_evolve_prompt_from_run_generates_runtime_readable_version(tmp_path: Path) -> None:
    run_dir = tmp_path / "v1_initial"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir.joinpath("prompt_proposals.json").write_text(
        json.dumps(
            {
                "schema": "prompt_proposals_v2",
                "prompt_version_base": "v2",
                "proposal_count": 1,
                "proposals": [
                    {
                        "proposal_id": "demo_1",
                        "prompt_role_key": "wolf",
                        "target_variable": "v2.role.wolf.suggestion",
                        "status": "draft",
                        "kind": "positive_persuasion",
                        "priority": 1,
                        "suggested_patch": {
                            "section": "day_speech_strategy",
                            "action": "append_guidance",
                            "text_zh": "测试采纳建议：白天发言要给出单一归票目标。",
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
        base_prompt_version="v2",
        output_root=output_root,
    )
    register_prompt_search_root(output_root)

    assert result.applied_count == 1
    assert result.new_prompt_version != "v2"
    assert result.new_version_dir is not None
    assert (run_dir / "applied_prompt_proposals.json").is_file()
    assert (run_dir / "prompt_version_diff.json").is_file()
    assert (run_dir / "new_prompt_version.txt").read_text(encoding="utf-8") == result.new_prompt_version
    wolf = PromptManager.get_role_strategy_config("wolf", prompt_version=result.new_prompt_version)
    assert "测试采纳建议" in wolf["suggestion"]


def test_evolve_prompt_from_run_keeps_version_when_no_applicable_proposals(tmp_path: Path) -> None:
    run_dir = tmp_path / "v1_initial"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir.joinpath("prompt_proposals.json").write_text(
        json.dumps(
            {
                "schema": "prompt_proposals_v2",
                "proposals": [
                    {
                        "proposal_id": "ignored",
                        "target_variable": "v2.role.wolf.suggestion",
                        "status": "rejected",
                        "kind": "positive_persuasion",
                        "priority": 1,
                        "suggested_patch": {
                            "section": "day_speech_strategy",
                            "action": "append_guidance",
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
        base_prompt_version="v2",
        output_root=tmp_path / "prompt_versions",
    )

    assert result.applied_count == 0
    assert result.new_prompt_version == "v2"
    applied = json.loads((run_dir / "applied_prompt_proposals.json").read_text(encoding="utf-8"))
    assert applied["skipped_reason"] == "no_applicable_prompt_proposals"
