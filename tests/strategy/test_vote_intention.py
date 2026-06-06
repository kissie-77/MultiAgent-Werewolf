"""投票意向追踪辅助函数。"""

from llm_werewolf.strategy.voting.intention import (
    VoteIntentionEntry,
    VoteIntentionTracker,
    compute_vote_swings,
    format_intentions_line,
)


def _entry(player_id: str, name: str, seat: int, target: str | None = None) -> VoteIntentionEntry:
    return VoteIntentionEntry(
        player_id=player_id,
        player_name=name,
        seat=seat,
        target_id=f"player_{target}" if target else None,
        target_name=f"P{target}" if target else None,
    )


def test_compute_vote_swings_detects_changes() -> None:
    before = {
        "player_1": _entry("player_1", "A", 3, "3"),
        "player_2": _entry("player_2", "B", 3, "3"),
    }
    after = {
        "player_1": _entry("player_1", "A", 2, "2"),
        "player_2": _entry("player_2", "B", 3, "3"),
    }
    swings = compute_vote_swings(before, after)
    assert len(swings) == 1
    assert swings[0].player_id == "player_1"
    assert swings[0].from_seat == 3
    assert swings[0].to_seat == 2


def test_compute_vote_swings_none_to_target() -> None:
    before = {"player_1": _entry("player_1", "A", 0)}
    after = {"player_1": _entry("player_1", "A", 2, "2")}
    swings = compute_vote_swings(before, after)
    assert len(swings) == 1
    assert swings[0].to_seat == 2


def test_tracker_record_speech_block() -> None:
    tracker = VoteIntentionTracker()
    before = {"player_1": _entry("player_1", "A", 0)}
    after = {"player_1": _entry("player_1", "A", 2, "2")}

    class _Speaker:
        player_id = "player_3"
        name = "C"

    record = tracker.record_speech_block(
        round_number=1,
        phase="day_discussion",
        channel="public",
        speaker=_Speaker(),  # type: ignore[arg-type]
        public_speech="我认为二号可疑",
        before=before,
        after=after,
    )
    assert len(record.swings) == 1
    assert len(tracker.speech_records) == 1
    exported = tracker.export_records()[0]
    assert exported["speaker_name"] == "C"
    assert exported["swing_count"] == 1


def test_format_intentions_line() -> None:
    intentions = {
        "player_1": _entry("player_1", "A", 0),
        "player_2": _entry("player_2", "B", 3, "3"),
    }
    line = format_intentions_line(intentions)
    assert "A→无" in line
    assert "B→P3" in line
