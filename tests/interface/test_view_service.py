import json
from pathlib import Path

from llm_werewolf.interface.api.services.view import build_view, _reveal_visibility


def _seed_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    (run_dir / "roster.json").write_text(json.dumps({"players": [
        {"seat": 1, "player_id": "player_1", "name": "P1", "role": "预言家", "camp": "villager", "model": "deepseek-chat"},
        {"seat": 2, "player_id": "player_2", "name": "P2", "role": "狼人", "camp": "werewolf", "model": "doubao"},
    ]}), encoding="utf-8")
    rows = [
        {"event_type": "phase_changed", "round_number": 1, "phase": "day_discussion", "message": "第1天 讨论", "data": {"phase": "day_discussion", "round": 1}},
        {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion", "message": "P1: 我怀疑2号",
         "data": {"player_id": "player_1", "player_name": "P1", "speech": "我怀疑2号", "private_thought": "其实2号像狼"}},
        {"event_type": "seer_checked", "round_number": 1, "phase": "night", "message": "预言家查验2号→查杀",
         "data": {"player_id": "player_1", "target_id": "player_2", "result": "werewolf"}},
        {"event_type": "player_eliminated", "round_number": 1, "phase": "day_voting", "message": "2号被放逐",
         "data": {"player_id": "player_2", "player_name": "P2"}},
    ]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    return run_dir


def test_build_view_cursor_and_event_mapping(tmp_path):
    run_dir = _seed_run(tmp_path)
    view = build_view(run_dir, since=0, status="running")
    assert view.cursor == 4
    types = [e.type for e in view.events]
    assert types == ["phase", "speech", "skill", "death"]
    speech = next(e for e in view.events if e.type == "speech")
    assert speech.private_thought == "其实2号像狼"
    # spec §5.2: events carry `round` (not `day`) — the field the frontend reads.
    assert speech.round == 1
    assert not hasattr(speech, "day")
    skill = next(e for e in view.events if e.type == "skill")
    assert skill.visibility == "god"
    assert skill.reveal == "on_game_end"


def test_build_view_since_returns_only_new(tmp_path):
    run_dir = _seed_run(tmp_path)
    view = build_view(run_dir, since=3, status="running")
    assert view.cursor == 4
    assert len(view.events) == 1
    assert view.events[0].seq == 3  # 0-based index of 4th row


def test_build_view_snapshot_alive_and_role(tmp_path):
    run_dir = _seed_run(tmp_path)
    view = build_view(run_dir, since=0, status="running")
    snap = view.snapshot
    assert snap.alive_count == 1   # player_2 eliminated
    assert snap.dead_count == 1
    p2 = next(p for p in snap.players if p.seat == 2)
    assert p2.role == "狼人"
    assert p2.is_alive is False


def test_build_view_alive_count_never_negative_with_off_roster_deaths(tmp_path):
    run_dir = tmp_path / "run_offroster"
    run_dir.mkdir()
    (run_dir / "roster.json").write_text(json.dumps({"players": [
        {"seat": 1, "player_id": "player_1", "name": "P1", "role": "村民", "camp": "villager", "model": "demo"},
    ]}), encoding="utf-8")
    rows = [
        {"event_type": "player_eliminated", "round_number": 1, "phase": "day_voting", "message": "x",
         "data": {"player_id": "player_99", "player_name": "ghost"}},
        {"event_type": "player_died", "round_number": 1, "phase": "night", "message": "y",
         "data": {"player_id": "player_42", "player_name": "ghost2"}},
    ]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    view = build_view(run_dir, since=0, status="running")
    snap = view.snapshot
    # roster player_1 is not in the death events, so it remains alive
    assert snap.alive_count == 1
    assert snap.alive_count >= 0


def test_public_skills_are_immediately_visible():
    # hunter_revenge and sheriff_badge_transferred happen publicly during the day
    assert _reveal_visibility("hunter_revenge", "day_voting") == ("now", "public")
    assert _reveal_visibility("sheriff_badge_transferred", "day_discussion") == ("now", "public")


def test_build_view_hunter_revenge_event_is_public(tmp_path):
    run_dir = tmp_path / "run_hunter"
    run_dir.mkdir()
    (run_dir / "roster.json").write_text(json.dumps({"players": [
        {"seat": 1, "player_id": "player_1", "name": "P1", "role": "猎人", "camp": "villager", "model": "demo"},
    ]}), encoding="utf-8")
    rows = [
        {"event_type": "hunter_revenge", "round_number": 1, "phase": "day_voting", "message": "猎人开枪带走2号",
         "data": {"player_id": "player_1", "target_id": "player_2"}},
    ]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    view = build_view(run_dir, since=0, status="running")
    ev = next(e for e in view.events if e.type == "skill")
    assert ev.reveal == "now"
    assert ev.visibility == "public"


from llm_werewolf.interface.api.services.view import _classify, _map_event


def test_new_skill_eventtypes_classify_as_skill_with_spec_kind() -> None:
    cases = {
        "white_wolf_killed": "white_wolf_kill",
        "wolf_beauty_charmed": "wolf_beauty_charm",
        "nightmare_blocked": "nightmare_block",
        "guardian_wolf_protected": "guardian_wolf_guard",
        "raven_marked": "raven_mark",
    }
    for event_type, expected_kind in cases.items():
        assert _classify(event_type) == "skill", event_type
        row = {
            "event_type": event_type, "round_number": 1, "phase": "night",
            "message": "", "data": {"actor_id": "player_2", "target_id": "player_5",
                                    "result": "ok"},
        }
        ev = _map_event(3, row)
        assert ev.type == "skill"
        assert ev.skill["kind"] == expected_kind
        assert ev.skill["actor"] == {"seat": 2}
        assert ev.skill["target"] == {"seat": 5}
        assert ev.skill["result"] == "ok"


def test_sub_phase_eventtype_classifies_as_sub_phase() -> None:
    assert _classify("sub_phase") == "sub_phase"
    row = {"event_type": "sub_phase", "round_number": 1, "phase": "night",
           "message": "", "data": {"name": "werewolf_chat"}}
    ev = _map_event(4, row)
    assert ev.type == "sub_phase"
    # spec §5.2: sub_phase name is delivered TOP-LEVEL as `name` (the field the
    # frontend store reads), not nested under a `sub_phase` dict.
    assert ev.name == "werewolf_chat"
    # a night-phase sub_phase is a public display hint, not god-only
    assert ev.reveal == "now"
    assert ev.visibility == "public"
