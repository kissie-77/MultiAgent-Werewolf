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
    assert payload["sub_phase"] == {"name": "witch_decide"}


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
