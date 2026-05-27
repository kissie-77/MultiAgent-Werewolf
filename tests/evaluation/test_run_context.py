"""run_context roster 构建测试。"""

from pathlib import Path

from llm_werewolf.evaluation.post_game.run_context import load_run_context, roster_from_events
from llm_werewolf.game_runtime.prompts.manager import PromptManager


def test_roster_from_role_acting_events() -> None:
    events = [
        {
            "event_type": "role_acting",
            "round_number": 1,
            "phase": "night",
            "data": {"player_id": "player_9", "role": "Seer"},
        },
        {
            "event_type": "role_acting",
            "round_number": 1,
            "phase": "night",
            "data": {"player_id": "player_5", "role": "Guard"},
        },
        {
            "event_type": "player_eliminated",
            "round_number": 1,
            "phase": "day_voting",
            "data": {"player_id": "player_1", "role": "Werewolf"},
        },
    ]
    roster = roster_from_events(events)
    assert roster["player_9"].role_name == "Seer"
    assert PromptManager.get_prompt_role_key(roster["player_9"].role_name) == "prophet"
    assert roster["player_5"].role_name == "Guard"
    assert roster["player_1"].role_name == "Werewolf"


def test_load_run_context_doubao_run_roster() -> None:
    run_dir = Path("artifacts/runs/doubao-9p-20260525-170043")
    if not (run_dir / "events.jsonl").is_file():
        return
    ctx = load_run_context(run_dir)
    entry = ctx.roster.get("player_9")
    assert entry is not None
    assert entry.role_name == "Seer"
    assert PromptManager.get_prompt_role_key(entry.role_name) == "prophet"
    assert ctx.roster["player_7"].role_name == "Witch"
    assert ctx.roster["player_4"].role_name == "Alpha Wolf"
