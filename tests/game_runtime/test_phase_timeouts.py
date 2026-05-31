"""PhaseInteraction timeout routing tests."""

from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction


class _Hub:
    pass


def test_timeout_for_phase_uses_day_budget_for_day_discussion() -> None:
    interaction = PhaseInteraction(_Hub())
    interaction.configure_timeouts(night_timeout=45, day_timeout=180, vote_timeout=60)
    assert interaction._timeout_for_phase("day_discussion") == 180.0
    assert interaction._timeout_for_phase("sheriff_election") == 180.0
    assert interaction._timeout_for_phase("day_voting") == 60.0
    assert interaction._timeout_for_phase("Night") == 45.0


def test_timeout_for_phase_legacy_labels_still_work() -> None:
    interaction = PhaseInteraction(_Hub())
    interaction.configure_timeouts(night_timeout=30, day_timeout=300, vote_timeout=45)
    assert interaction._timeout_for_phase("Discussion") == 300.0
    assert interaction._timeout_for_phase("Voting") == 45.0
