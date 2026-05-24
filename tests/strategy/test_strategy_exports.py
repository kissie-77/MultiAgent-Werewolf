from llm_werewolf.strategy.decisions import SpeechDecision
from llm_werewolf.strategy.phase_outputs import ActionPhase
from llm_werewolf.strategy.vote_intention import VoteIntentionTracker


def test_strategy_exports_decision_contracts() -> None:
    assert SpeechDecision.__name__ == "SpeechDecision"
    assert ActionPhase.__name__ == "ActionPhase"
    assert VoteIntentionTracker.__name__ == "VoteIntentionTracker"
