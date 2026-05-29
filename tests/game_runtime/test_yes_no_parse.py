import pytest

from llm_werewolf.game_runtime.prompts.yes_no_parse import YesNoParseError, parse_yes_no_strict


def test_parse_yes_no_bracketed() -> None:
    assert parse_yes_no_strict("[[1]]") is True
    assert parse_yes_no_strict("[[0]]") is False


def test_parse_yes_no_single_digit() -> None:
    assert parse_yes_no_strict("1") is True
    assert parse_yes_no_strict("0") is False


def test_parse_yes_no_whole_words() -> None:
    assert parse_yes_no_strict("yes") is True
    assert parse_yes_no_strict("否") is False


def test_parse_yes_no_rejects_substring_false_positive() -> None:
    with pytest.raises(YesNoParseError):
        parse_yes_no_strict("I know the answer")
    with pytest.raises(YesNoParseError):
        parse_yes_no_strict("不知道")


def test_vote_intention_snapshot_not_visible_to_players() -> None:
    from llm_werewolf.game_runtime.events.event_visibility import resolve_visible_to
    from llm_werewolf.game_runtime.types import EventType

    visible = resolve_visible_to(EventType.VOTE_INTENTION_SNAPSHOT, {"speaker_id": "p1"})
    assert visible == []
