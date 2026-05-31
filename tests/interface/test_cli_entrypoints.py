"""Smoke tests for CLI entrypoint modules and vote-swing CLI."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import llm_werewolf.interface.cli as cli_pkg
import llm_werewolf.interface.eval_cli as eval_cli_shim
import llm_werewolf.interface.tui as tui_shim
import llm_werewolf.interface.vote_swing_cli as vote_swing_shim
from llm_werewolf.interface.cli import vote_swing as vote_swing_mod


def test_cli_package_exports() -> None:
    assert callable(cli_pkg.entry)
    assert callable(cli_pkg.main)


def test_compat_shims_reexport_entrypoints() -> None:
    assert callable(eval_cli_shim.main)
    assert callable(tui_shim.entry)
    assert callable(vote_swing_shim.main)


def test_vote_swing_main_writes_artifacts(tmp_path, capsys) -> None:
    record = {
        "round_number": 1,
        "phase": "day_discussion",
        "speaker_id": "player_1",
        "speaker_name": "A",
        "public_speech": "test",
        "before": {},
        "after": {},
        "swings": [],
        "swing_count": 0,
    }
    path = tmp_path / "vote_intentions.jsonl"
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    out_dir = vote_swing_mod.main(str(tmp_path), print_report=True)
    assert (tmp_path / "vote_swing_report.md").is_file()
    assert out_dir == str(tmp_path.resolve())
    assert capsys.readouterr().out


def test_vote_swing_main_no_print(tmp_path) -> None:
    record = {
        "round_number": 1,
        "phase": "day_discussion",
        "speaker_id": "player_1",
        "speaker_name": "A",
        "public_speech": "test",
        "before": {},
        "after": {},
        "swings": [],
        "swing_count": 0,
    }
    path = tmp_path / "vote_intentions.jsonl"
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    vote_swing_mod.main(str(tmp_path), print_report=False)


def test_eval_cli_main_smoke(tmp_path) -> None:
    from llm_werewolf.interface.cli import eval as eval_mod

    with patch("llm_werewolf.interface.cli.eval.EvaluationRunner") as mock_runner_cls:
        mock_runner_cls.return_value.run = AsyncMock(return_value=[])
        with patch("llm_werewolf.interface.cli.eval.asyncio.run") as mock_run:
            result = eval_mod.main(output_dir=str(tmp_path), games=1)
            mock_run.assert_called_once()
    assert result == str(tmp_path)
