from unittest.mock import patch

from llm_werewolf.interface.cli.runtime.startup_menu import prompt_startup_selection


def test_prompt_startup_selection_defaults_to_all_agent_badge_flow() -> None:
    with patch("builtins.input", side_effect=["", "", ""]):
        selection = prompt_startup_selection()

    assert selection.participation == "all_agent"
    assert selection.rules == "badge_flow"
    assert selection.human_seat is None
    assert selection.players == 12


def test_prompt_startup_selection_human_mix_prompts_for_seat() -> None:
    with patch("builtins.input", side_effect=["2", "3", "9", "5"]):
        selection = prompt_startup_selection()

    assert selection.participation == "all_agent"
    assert selection.rules == "extended_roles"
    assert selection.human_seat == "5"
    assert selection.players == 9


def test_prompt_startup_selection_reprompts_human_seat_against_player_count() -> None:
    with patch("builtins.input", side_effect=["2", "1", "6", "7", "6"]):
        selection = prompt_startup_selection()

    assert selection.human_seat == "6"
    assert selection.players == 6
