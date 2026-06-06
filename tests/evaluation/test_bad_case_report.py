"""Bad Case 报告的单元测试。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from llm_werewolf.evaluation.post_game.run_context import RunContext, PlayerRosterEntry
from llm_werewolf.evaluation.post_game.bad_case_report import (
    build_bad_case_report,
    write_bad_case_artifacts,
    _detect_seer_silent_cases,
    _detect_witch_no_save_cases,
    _detect_villager_vote_friendly_fire,
    _detect_wolf_repeat_blocked,
)


def _make_ctx(events: list, roster: dict | None = None, tmp_path: Path | None = None) -> RunContext:
    r = roster or {}
    return RunContext(
        run_dir=tmp_path or Path("/tmp/test_run"),
        events=events,
        roster=r,
        winner_camp="villager",
    )


def _roster() -> dict[str, PlayerRosterEntry]:
    return {
        "seer_1": PlayerRosterEntry("seer_1", "Seer", "Seer", "villager"),
        "witch_1": PlayerRosterEntry("witch_1", "Witch", "Witch", "villager"),
        "guard_1": PlayerRosterEntry("guard_1", "Guard", "Guard", "villager"),
        "wolf_1": PlayerRosterEntry("wolf_1", "Wolf1", "Werewolf", "werewolf"),
        "wolf_2": PlayerRosterEntry("wolf_2", "Wolf2", "Werewolf", "werewolf"),
        "v1": PlayerRosterEntry("v1", "Villager1", "Villager", "villager"),
        "v2": PlayerRosterEntry("v2", "Villager2", "Villager", "villager"),
    }


class TestSeerSilentDetection:
    def test_detects_seer_silent_on_wolf(self) -> None:
        events = [
            {"event_type": "seer_checked", "round_number": 1,
             "data": {"player_id": "seer_1", "target_id": "wolf_1", "result": "werewolf"}},
            {"event_type": "player_speech", "round_number": 2,
             "data": {"player_id": "seer_1", "content": "我觉得3号比较可疑"}},
        ]
        ctx = _make_ctx(events, _roster())
        cases = _detect_seer_silent_cases(ctx)
        assert len(cases) == 1
        assert cases[0]["kind"] == "seer_silent_on_wolf"
        assert cases[0]["severity"] == "high"

    def test_no_case_when_seer_mentions_target(self) -> None:
        events = [
            {"event_type": "seer_checked", "round_number": 1,
             "data": {"player_id": "seer_1", "target_id": "wolf_1", "result": "werewolf"}},
            {"event_type": "player_speech", "round_number": 2,
             "data": {"player_id": "seer_1", "content": "我验了Wolf1是狼人"}},
        ]
        ctx = _make_ctx(events, _roster())
        cases = _detect_seer_silent_cases(ctx)
        assert len(cases) == 0

    def test_no_case_when_result_is_villager(self) -> None:
        events = [
            {"event_type": "seer_checked", "round_number": 1,
             "data": {"player_id": "seer_1", "target_id": "v1", "result": "villager"}},
        ]
        ctx = _make_ctx(events, _roster())
        cases = _detect_seer_silent_cases(ctx)
        assert len(cases) == 0


class TestWitchNoSave:
    def test_detects_witch_no_save(self) -> None:
        events = [
            {"event_type": "werewolf_killed", "round_number": 1,
             "data": {"target_id": "v1"}},
        ]
        ctx = _make_ctx(events, _roster())
        cases = _detect_witch_no_save_cases(ctx)
        assert len(cases) == 1
        assert cases[0]["kind"] == "witch_no_save"

    def test_no_case_when_witch_saved(self) -> None:
        events = [
            {"event_type": "werewolf_killed", "round_number": 1,
             "data": {"target_id": "v1"}},
            {"event_type": "witch_saved", "round_number": 1,
             "data": {"player_id": "witch_1", "target_id": "v1"}},
        ]
        ctx = _make_ctx(events, _roster())
        cases = _detect_witch_no_save_cases(ctx)
        assert len(cases) == 0

    def test_no_case_when_target_is_wolf(self) -> None:
        events = [
            {"event_type": "werewolf_killed", "round_number": 1,
             "data": {"target_id": "wolf_2"}},
        ]
        ctx = _make_ctx(events, _roster())
        cases = _detect_witch_no_save_cases(ctx)
        assert len(cases) == 0


class TestFriendlyFireVote:
    def test_detects_villager_voting_villager(self) -> None:
        events = [
            {"event_type": "vote_result", "round_number": 2,
             "data": {
                 "executed": "wolf_1",
                 "votes": {
                     "wolf_1": ["v1", "seer_1"],
                     "v2": ["v1"],
                 },
             }},
        ]
        roster = _roster()
        ctx = _make_ctx(events, roster)
        cases = _detect_villager_vote_friendly_fire(ctx)
        assert len(cases) >= 1
        assert cases[0]["kind"] == "friendly_fire_vote"

    def test_no_case_when_no_wolf_candidate(self) -> None:
        events = [
            {"event_type": "vote_result", "round_number": 2,
             "data": {
                 "executed": "v1",
                 "votes": {"v1": ["v2"], "v2": ["v1"]},
             }},
        ]
        roster = _roster()
        ctx = _make_ctx(events, roster)
        cases = _detect_villager_vote_friendly_fire(ctx)
        assert len(cases) == 0


class TestWolfRepeatBlocked:
    def test_detects_repeat_blocked(self) -> None:
        events = [
            {"event_type": "werewolf_killed", "round_number": 1, "data": {"target_id": "v1"}},
            {"event_type": "guard_protected", "round_number": 1, "data": {"target_id": "v1"}},
            {"event_type": "werewolf_killed", "round_number": 2, "data": {"target_id": "v1"}},
            {"event_type": "guard_protected", "round_number": 2, "data": {"target_id": "v1"}},
        ]
        ctx = _make_ctx(events, _roster())
        cases = _detect_wolf_repeat_blocked(ctx)
        assert len(cases) == 1
        assert cases[0]["kind"] == "wolf_repeat_blocked"

    def test_no_case_when_single_block(self) -> None:
        events = [
            {"event_type": "werewolf_killed", "round_number": 1, "data": {"target_id": "v1"}},
            {"event_type": "guard_protected", "round_number": 1, "data": {"target_id": "v1"}},
        ]
        ctx = _make_ctx(events, _roster())
        cases = _detect_wolf_repeat_blocked(ctx)
        assert len(cases) == 0


class TestBuildReport:
    def test_empty_game_produces_empty_report(self) -> None:
        ctx = _make_ctx([], _roster())
        report = build_bad_case_report(ctx)
        assert report["schema"] == "bad_case_report_v1"
        assert report["total_cases"] == 0

    def test_write_artifacts(self, tmp_path: Path) -> None:
        events = [
            {"event_type": "seer_checked", "round_number": 1,
             "data": {"player_id": "seer_1", "target_id": "wolf_1", "result": "werewolf"}},
        ]
        ctx = _make_ctx(events, _roster(), tmp_path)
        json_path = write_bad_case_artifacts(ctx)
        assert json_path.exists()
        assert (tmp_path / "bad_case_report.md").exists()
