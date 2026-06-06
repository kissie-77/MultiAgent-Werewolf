"""LLM 资产提取与合并逻辑。"""

from llm_werewolf.evaluation.post_game.llm_asset_extractor import (
    merge_llm_proposals,
    merge_llm_skills,
)
from llm_werewolf.evaluation.post_game.run_context import RunContext
from llm_werewolf.strategy.contracts.evaluation_outputs import (
    LlmPromptProposalItem,
    LlmSkillItem,
)


def _ctx() -> RunContext:
    return RunContext(run_dir="/tmp/test-run", prompt_version="v1", winner_camp="werewolf")


def test_merge_llm_proposals_replaces_templated_positive_persuasion() -> None:
    ctx = _ctx()
    rule_payload = {
        "schema": "prompt_proposals_v3",
        "proposals": [
            {
                "proposal_id": "pos_influence_r1_player_4",
                "prompt_role_key": "wolf",
                "kind": "positive_persuasion",
                "source": "rule",
                "suggested_patch": {
                    "text_zh": "参考本局有效发言模式：我是平民。。后续归票阶段继续保持「结论+依据」的收束方式。"
                },
            },
            {
                "proposal_id": "mvp_golden",
                "prompt_role_key": "wolf",
                "kind": "mvp_golden_quote",
                "source": "rule",
                "suggested_patch": {"text_zh": "金句原文"},
            },
        ],
        "proposal_count": 2,
    }
    llm_assets = {
        "mode": "llm",
        "prompt_proposals": [
            LlmPromptProposalItem(
                prompt_role_key="wolf",
                kind="positive_persuasion",
                suggested_patch_text_zh="归票前先复述场上已公开信息，再用「因此今天先出X」收束，避免无依据踩人。",
                rationale="本局狼队靠逻辑链收票成功",
                confidence_score=0.88,
                evidence_round=1,
            ).model_dump(),
            LlmPromptProposalItem(
                prompt_role_key="prophet",
                kind="bad_case_rule",
                suggested_patch_text_zh="首夜验出狼人后，若场上无对跳，必须在归票前以「我昨晚验了X是狼」公开信息。",
                rationale="修复 seer_silent",
                confidence_score=0.9,
            ).model_dump(),
        ],
    }
    merged = merge_llm_proposals(rule_payload, llm_assets, ctx=ctx)
    kinds_by_role = {(p["prompt_role_key"], p["kind"], p.get("source")) for p in merged["proposals"]}
    assert ("wolf", "positive_persuasion", "rule") not in kinds_by_role
    assert ("wolf", "positive_persuasion", "llm") in kinds_by_role
    assert ("prophet", "bad_case_rule", "llm") in kinds_by_role
    assert merged["llm_merge"]["applied"] is True
    assert merged["proposal_count"] == 3


def test_merge_llm_skills_rewrites_when_scene_matches() -> None:
    ctx = RunContext(
        run_dir="/tmp/test-run",
        prompt_version="v1",
        winner_camp="werewolf",
        events=[],
    )
    scene = "第1天白天进入归票前，已验出狼且场上无人对跳预言家"
    rule_payload = {
        "schema": "role_skills_v1",
        "skills": [
            {
                "skill_id": "prophet_night_r1",
                "prompt_role_key": "prophet",
                "source": "rule",
                "status": "draft",
                "skill_card": {
                    "title_zh": "首夜验狼公开",
                    "when_to_use": f"{scene}；信念矩阵触发：B1对单目标狼信极高",
                    "public_behavior": "① 优先验高置位。",
                    "avoid": "① 查到狼后不公开。",
                },
            },
            {
                "skill_id": "prophet_night_r2",
                "prompt_role_key": "prophet",
                "source": "rule",
                "status": "draft",
                "skill_card": {
                    "title_zh": "第二夜查验",
                    "when_to_use": "第2夜需要扩大验人范围时",
                    "public_behavior": "① 验摇摆位。",
                    "avoid": "",
                },
            },
        ],
        "skill_count": 2,
    }
    llm_assets = {
        "mode": "llm",
        "skills": [
            LlmSkillItem(
                prompt_role_key="prophet",
                title_zh="首夜验狼后的白天公开",
                when_to_use=scene,
                belief_trigger_zh="B1 对单一目标狼信≥0.85 且投票意向已收敛",
                public_behavior="① 先报验人结果；② 给出票X理由；③ 请求跟票。",
                avoid="① 仅说怀疑却不报验人。",
                rationale="本局败因是验狼不公开",
                quality_passed=True,
                source_player_id="player_2",
                evidence_round=1,
            ).model_dump(),
            LlmSkillItem(
                prompt_role_key="prophet",
                title_zh="第二夜扩大验人",
                when_to_use="第2夜存活且需扩大信息覆盖",
                belief_trigger_zh="狼信分散，需新验人定方向",
                public_behavior="① 验未发言摇摆位。",
                avoid="",
                rationale="不同场景",
                quality_passed=True,
            ).model_dump(),
        ],
    }
    merged = merge_llm_skills(rule_payload, llm_assets, ctx=ctx)
    by_id = {s["skill_id"]: s for s in merged["skills"]}
    assert by_id["prophet_night_r1"]["source"] == "rule+llm"
    assert "先报验人结果" in by_id["prophet_night_r1"]["skill_card"]["public_behavior"]
    assert "信念矩阵触发" in by_id["prophet_night_r1"]["skill_card"]["when_to_use"]
    assert by_id["prophet_night_r2"]["source"] == "rule"
    assert merged["llm_merge"]["enriched"] == 1
    assert merged["llm_merge"]["added"] == 1
    assert len(merged["skills"]) == 3
