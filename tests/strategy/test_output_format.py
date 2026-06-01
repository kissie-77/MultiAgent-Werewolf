"""发言与仅座位 [[...]] 解析的测试。"""

import pytest

from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.strategy.decisions import (
    SPEECH_PUBLIC_MIN_CHARS,
    SpeechDecision,
    extract_public_text,
    looks_like_seat_only,
    is_valid_public_speech,
    normalize_speech_decision,
    speech_schema_instruction,
    looks_like_kill_or_vote_format,
    seat_choice_schema_instruction,
    witch_night_schema_instruction,
    vote_intention_schema_instruction,
    mind_state_schema_instruction,
    metadata_looks_like_wrong_schema_for_speech,
)
from llm_werewolf.strategy.phase_outputs import (
    ROUNDTABLE_SPEECH_ONLY_MARKER,
    RoundtablePhase,
    roundtable_phase_instruction,
)


def test_looks_like_seat_only() -> None:
    assert looks_like_seat_only("1")
    assert looks_like_seat_only("12")
    assert not looks_like_seat_only("我觉得1号可疑")


def test_extract_public_text_rejects_vote_token() -> None:
    raw = "{我先想想} [[7]]"
    assert extract_public_text(raw) == "（无公开发言）"


def test_extract_public_text_prefers_long_speech_block() -> None:
    raw = "[[1]] {装村民} [[大家好，我觉得5号发言很怪，需要再听一轮。]]"
    speech = extract_public_text(raw)
    assert "5号" in speech
    assert speech != "1"


def test_extract_public_text_falls_back_to_prose() -> None:
    raw = "{内心} 我暂时看不出狼，建议大家多盘逻辑。"
    assert "盘逻辑" in extract_public_text(raw)


def test_parse_speech_splits_public_and_private() -> None:
    raw = "[[我认为2号玩家发言前后矛盾，暂时想重点听他的解释]] {我在装村民，不能暴露}"
    decision = WerewolfAdapterBridge.parse_speech(raw)

    assert "2号" in decision.public_speech
    assert decision.private_thought is not None
    assert "装村民" in decision.private_thought


def test_speech_schema_instruction_mentions_fields() -> None:
    text = speech_schema_instruction()
    assert "public_speech" in text
    assert "private_thought" in text
    assert str(SPEECH_PUBLIC_MIN_CHARS) in text
    assert "直接输出一个 JSON 对象" in text


def test_non_speech_schema_instructions_do_not_claim_speech_schema() -> None:
    texts = [
        vote_intention_schema_instruction(),
        mind_state_schema_instruction(),
        seat_choice_schema_instruction(),
        witch_night_schema_instruction(can_see_victim=True),
    ]

    for text in texts:
        assert "字段严格遵守 SpeechDecision Schema" not in text
        assert "public_speech / private_thought" not in text


def test_speech_decision_rejects_short_public_speech() -> None:
    with pytest.raises(ValueError):
        SpeechDecision(public_speech="太短", private_thought=None)


def test_kill_vote_format_rejected() -> None:
    assert looks_like_kill_or_vote_format("[[7]]")
    assert looks_like_kill_or_vote_format("刀7")
    assert not looks_like_kill_or_vote_format("我觉得7号发言前后矛盾需要再听一轮解释")
    assert not is_valid_public_speech("[[7]]")


def test_wrong_schema_metadata_for_speech() -> None:
    assert metadata_looks_like_wrong_schema_for_speech({"seat": 7})
    assert not metadata_looks_like_wrong_schema_for_speech({
        "public_speech": "我觉得七号玩家发言前后矛盾需要再听解释"
    })


def test_roundtable_phase_instruction_forbids_seat() -> None:
    text = roundtable_phase_instruction(RoundtablePhase.WOLF_TEAM_DISCUSSION)
    assert ROUNDTABLE_SPEECH_ONLY_MARKER in text
    assert "禁止" in text
    assert "seat" in text


def test_normalize_speech_repairs_structured_seat_only() -> None:
    broken = SpeechDecision.model_construct(public_speech="7", private_thought="真预")
    fixed = normalize_speech_decision(
        broken, raw_fallback="[[7]] [[我是预言家，昨晚验了5号是狼。]]"
    )
    assert is_valid_public_speech(fixed.public_speech)
    assert "预言家" in fixed.public_speech
