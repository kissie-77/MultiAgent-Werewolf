from llm_werewolf.agent_team.memory.semantic_matching import (
    deduplicate_candidates,
    merge_card_contents,
    merge_reflections,
    normalize_content,
    similarity,
)


def test_normalize_content_collapses_whitespace():
    assert normalize_content("  首夜\n  统一   刀口  ") == "首夜 统一 刀口"


def test_similarity_uses_normalized_content():
    assert similarity("首夜 统一刀口", "首夜\n统一刀口") == 1.0


def test_merge_card_contents_keeps_existing_when_same_or_contained():
    assert merge_card_contents("首夜统一刀口", "首夜统一刀口") == "首夜统一刀口"
    assert merge_card_contents("首夜统一刀口，并说明理由", "统一刀口") == "首夜统一刀口，并说明理由"


def test_merge_card_contents_appends_distinct_text():
    merged = merge_card_contents("首夜统一刀口", "白天统一票型")

    assert merged == "首夜统一刀口\n\n白天统一票型"


def test_deduplicate_candidates_preserves_first_seen_text():
    candidates = [" 首夜统一刀口 ", "首夜 统一刀口", "白天统一票型"]

    assert deduplicate_candidates(candidates) == ["首夜统一刀口", "首夜 统一刀口", "白天统一票型"]


def test_merge_reflections_groups_by_chinese_colon_prefix():
    merged = merge_reflections([
        "失败反思：不要过早站边",
        "失败反思：补充核对票型",
        "胜利经验：持续跟踪焦点位",
    ])

    assert "失败反思：不要过早站边；补充核对票型" in merged
    assert "胜利经验：持续跟踪焦点位" in merged
