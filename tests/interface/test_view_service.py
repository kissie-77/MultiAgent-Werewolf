import json
from pathlib import Path

from llm_werewolf.interface.api.services.view import build_view


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
