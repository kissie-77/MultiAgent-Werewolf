"""log_views 可见性过滤与视图生成。"""

import json
from pathlib import Path

from llm_werewolf.evaluation.log_views.filters import (
    event_is_visible_to,
    filter_events_for_player,
    strip_thinking,
    truncate_text,
)
from llm_werewolf.evaluation.log_views.builder import write_log_views
from llm_werewolf.evaluation.post_game.camp_persuasion import build_camp_persuasion_report
from llm_werewolf.evaluation.post_game.run_context import load_run_context


def test_visible_to_public_event() -> None:
    event = {"event_type": "player_speech", "message": "hello", "visible_to": None}
    assert event_is_visible_to(event, "player_1")


def test_visible_to_private_event() -> None:
    event = {
        "event_type": "night_action",
        "message": "secret",
        "visible_to": ["player_2"],
    }
    assert event_is_visible_to(event, "player_2")
    assert not event_is_visible_to(event, "player_1")


def test_filter_events_for_player() -> None:
    events = [
        {"round_number": 1, "visible_to": None, "event_type": "a", "message": "pub"},
        {"round_number": 1, "visible_to": ["player_2"], "event_type": "b", "message": "priv"},
    ]
    pov = filter_events_for_player(events, "player_2")
    assert len(pov) == 2
    pov1 = filter_events_for_player(events, "player_1")
    assert len(pov1) == 1


def test_strip_thinking() -> None:
    text = "发言内容\nThinking:\n内部推理\n\npublic_speech: 对外"
    cleaned = strip_thinking(text)
    assert "内部推理" not in cleaned or "public_speech" in cleaned


def test_write_log_views_creates_manifest(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "player_speech",
            "round_number": 1,
            "phase": "day_discussion",
            "message": "公开发言",
            "visible_to": None,
            "data": {},
        },
        {
            "event_type": "vote_intention_snapshot",
            "round_number": 1,
            "phase": "day_discussion",
            "message": "意向",
            "visible_to": None,
            "data": {
                "speaker_id": "player_1",
                "speaker_name": "A",
                "public_speech": "投五号",
                "swings": [],
                "swing_count": 0,
            },
        },
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    ctx = load_run_context(tmp_path)
    from llm_werewolf.evaluation.post_game.run_context import PlayerRosterEntry

    ctx.roster["player_1"] = PlayerRosterEntry(
        player_id="player_1",
        player_name="A",
        role_name="Villager",
        camp="villager",
    )
    camp = build_camp_persuasion_report(ctx)
    manifest = write_log_views(ctx, camp)
    assert (tmp_path / "views_manifest.json").is_file()
    assert (tmp_path / "views" / "public_digest.md").is_file()
    assert len(manifest.views) >= 3
