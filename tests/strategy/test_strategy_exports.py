from llm_werewolf.strategy.contracts.decisions import SpeechDecision
from llm_werewolf.strategy.contracts.phase_outputs import ActionPhase
from llm_werewolf.strategy.voting.intention import VoteIntentionTracker


def test_strategy_exports_decision_contracts() -> None:
    assert SpeechDecision.__name__ == "SpeechDecision"
    assert ActionPhase.__name__ == "ActionPhase"
    assert VoteIntentionTracker.__name__ == "VoteIntentionTracker"
