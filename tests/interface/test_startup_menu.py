from unittest.mock import patch

from llm_werewolf.interface.cli.runtime.startup_menu import prompt_startup_selection


def test_prompt_startup_selection_defaults_to_all_agent_badge_flow() -> None:
    with patch("builtins.input", side_effect=["", ""]):
        selection = prompt_startup_selection()

    assert selection.participation == "all_agent"
    assert selection.rules == "badge_flow"
    assert selection.human_seat is None


def test_prompt_startup_selection_human_mix_prompts_for_seat() -> None:
    with patch("builtins.input", side_effect=["2", "3", "5"]):
        selection = prompt_startup_selection()

    assert selection.participation == "all_agent"
    assert selection.rules == "extended_roles"
    assert selection.human_seat == "5"
