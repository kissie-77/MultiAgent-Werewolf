"""Unit tests for SSE framing + payload + disk backfill helpers."""

from __future__ import annotations

import json

from llm_werewolf.interface.api.services.sse_stream import (
    backfill_from_disk,
    format_sse,
    sse_event_payload,
)


def test_format_sse_frames_id_event_data() -> None:
    frame = format_sse(143, "game", {"seq": 143, "type": "speech"})
    assert frame.startswith("id: 143\n")
    assert "event: game\n" in frame
    assert 'data: {"seq": 143, "type": "speech"}\n' in frame
    assert frame.endswith("\n\n")


def test_sse_event_payload_uses_view_mapping() -> None:
    row = {
        "event_type": "player_speech", "round_number": 2, "phase": "day_discussion",
        "message": "P3: hi",
        "data": {"player_id": "player_3", "player_name": "P3", "speech": "hi",
                 "private_thought": "hmm"},
    }
    payload = sse_event_payload(7, row)
    assert payload["seq"] == 7
    assert payload["type"] == "speech"
    assert payload["phase"] == "day_discussion"
    # spec §5.2: the SSE wire carries `round` (renders the frontend ROUND badge),
    # NOT the legacy `day` key.
    assert payload["round"] == 2
    assert "day" not in payload
    assert payload["speaker"] == {"seat": 3, "name": "P3"}
    assert payload["public_text"] == "hi"
    assert payload["private_thought"] == "hmm"
    assert payload["reveal"] == "now"
    assert payload["visibility"] == "public"


def test_sse_payload_for_five_typed_skills_has_type_skill_and_spec_kind() -> None:
    # Depends on Task 4b widening view._SKILL_TYPES/_SKILL_KIND.
    cases = {
        "white_wolf_killed": "white_wolf_kill",
        "wolf_beauty_charmed": "wolf_beauty_charm",
        "nightmare_blocked": "nightmare_block",
        "guardian_wolf_protected": "guardian_wolf_guard",
        "raven_marked": "raven_mark",
    }
    for event_type, expected_kind in cases.items():
        row = {"event_type": event_type, "round_number": 1, "phase": "night",
               "message": "", "data": {"actor_id": "player_2", "target_id": "player_5",
                                       "result": "ok"}}
        payload = sse_event_payload(9, row)
        assert payload["type"] == "skill", event_type
        assert payload["skill"]["kind"] == expected_kind


def test_sse_payload_for_sub_phase_has_type_sub_phase() -> None:
    row = {"event_type": "sub_phase", "round_number": 1, "phase": "night",
           "message": "", "data": {"name": "witch_decide"}}
    payload = sse_event_payload(10, row)
    assert payload["type"] == "sub_phase"
    # spec §5.2: the sub_phase name is on the wire as top-level `name` (the field
    # the frontend store reads), not nested under a `sub_phase` dict.
    assert payload["name"] == "witch_decide"


def test_backfill_from_disk_returns_seqs_after_cursor(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    rows = [
        {"event_type": "game_started", "round_number": 0, "phase": "setup", "message": "", "data": {}},
        {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
         "message": "P1: a", "data": {"player_id": "player_1", "player_name": "P1", "speech": "a"}},
        {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
         "message": "P2: b", "data": {"player_id": "player_2", "player_name": "P2", "speech": "b"}},
    ]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    # 0-based seqs: rows are seq 0,1,2. Last-Event-ID=0 => backfill seq > 0.
    missed = backfill_from_disk(run_dir, after_seq=0)
    assert [seq for seq, _ in missed] == [1, 2]
    assert missed[0][1]["data"]["player_name"] == "P1"


import pytest

from llm_werewolf.interface.api.services.event_hub import EventHub
from llm_werewolf.interface.api.services.sse_stream import stream_game


class _FakeSession:
    def __init__(self, run_dir=None, error=None) -> None:
        self.hub = EventHub()
        self.run_dir = run_dir
        self.error = error


def _speech_row(pid: int) -> dict:
    return {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
            "message": f"P{pid}", "data": {"player_id": f"player_{pid}",
            "player_name": f"P{pid}", "speech": "x"}}


async def test_stream_game_backfills_then_streams_live() -> None:
    session = _FakeSession()
    session.hub.publish(_speech_row(1))  # seq 0 (before connect)
    session.hub.publish(_speech_row(2))  # seq 1 (before connect)

    frames: list[str] = []
    # Last-Event-ID=0 => client already saw seq 0; backfill seq > 0 (=> seq 1).
    gen = stream_game(session=session, run_dir=__import__("pathlib").Path("."),
                      last_event_id=0)

    frames.append(await gen.__anext__())
    assert "id: 1\n" in frames[0]

    # A live event arrives -> next frame is seq 2.
    session.hub.publish(_speech_row(3))
    frames.append(await gen.__anext__())
    assert "id: 2\n" in frames[1]

    session.hub.close()
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


async def test_stream_game_no_duplicate_between_backfill_and_live() -> None:
    session = _FakeSession()
    session.hub.publish(_speech_row(1))  # seq 0, buffered
    # Fresh connection (no Last-Event-ID) => after_seq = -1 => backfill seq >= 0.
    gen = stream_game(session=session, run_dir=__import__("pathlib").Path("."),
                      last_event_id=-1)
    first = await gen.__anext__()  # backfill seq 0
    assert "id: 0\n" in first
    session.hub.close()
    # seq 0 must not be re-emitted as a live item.
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


async def test_stream_game_evicted_cursor_backfills_gap_from_disk(tmp_path) -> None:
    # Spec §8: requested Last-Event-ID older than the hub buffer => disk gap fill.
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    # Disk holds the full history seq 0..4.
    rows = [_speech_row(i) for i in range(5)]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    session = _FakeSession(run_dir=run_dir)
    session.hub = EventHub(buffer_size=2)  # only the last 2 seqs survive
    for r in rows:
        session.hub.publish(r)  # seqs 0..4; buffer now holds {3, 4}
    assert session.hub.min_buffered_seq == 3

    # Client resumes from Last-Event-ID=0 (seqs 1,2 were EVICTED from the buffer).
    gen = stream_game(session=session, run_dir=run_dir, last_event_id=0)
    seen: list[int] = []
    session.hub.close()  # no further live events; drain backfill then stop
    try:
        while True:
            frame = await gen.__anext__()
            if frame.startswith("id: "):
                seen.append(int(frame.split("\n", 1)[0].removeprefix("id: ")))
    except StopAsyncIteration:
        pass
    # The gap (seq 1,2 from disk) AND the in-buffer seqs (3,4) are all delivered,
    # in order, with NO gap silently skipped.
    assert seen == [1, 2, 3, 4]


async def test_stream_game_terminal_system_error_frame(tmp_path) -> None:
    # Spec §8: _run_game publishes a terminal type=system error event onto the hub
    # before close; it flows through stream_game like any other event.
    session = _FakeSession(run_dir=tmp_path, error="LLM provider timed out")
    # Simulate the Task 3 finally block: publish the system error, then close.
    session.hub.publish({
        "event_type": "system", "round_number": 0, "phase": "ended",
        "message": "LLM provider timed out", "data": {"error": "LLM provider timed out"},
    })
    gen = stream_game(session=session, run_dir=tmp_path, last_event_id=-1)
    session.hub.close()
    frames = []
    try:
        while True:
            frames.append(await gen.__anext__())
    except StopAsyncIteration:
        pass
    body = "".join(frames)
    assert '"type": "system"' in body
    assert "LLM provider timed out" in body
