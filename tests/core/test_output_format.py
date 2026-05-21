"""Tests for speech vs seat-only [[...]] parsing."""

from llm_werewolf.adapter.bridge import WerewolfAdapterBridge
from llm_werewolf.core.decisions import (
    extract_public_text,
    is_valid_public_speech,
    looks_like_seat_only,
    normalize_speech_decision,
    SpeechDecision,
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
    raw = "[[我认为2号可疑，发言前后矛盾]] {我在装村民，不能暴露}"
    decision = WerewolfAdapterBridge.parse_speech(raw)

    assert "2号" in decision.public_speech
    assert decision.private_thought is not None
    assert "装村民" in decision.private_thought


def test_normalize_speech_repairs_structured_seat_only() -> None:
    broken = SpeechDecision.model_construct(
        public_speech="7",
        private_thought="真预",
    )
    fixed = normalize_speech_decision(
        broken,
        raw_fallback="[[7]] [[我是预言家，昨晚验了5号是狼。]]",
    )
    assert is_valid_public_speech(fixed.public_speech)
    assert "预言家" in fixed.public_speech
