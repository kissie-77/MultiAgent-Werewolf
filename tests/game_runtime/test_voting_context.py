"""Voting context regression tests."""

from llm_werewolf.game_runtime.engine.voting_phase import VotingPhaseMixin
from llm_werewolf.game_runtime.i18n.locale import Locale


class _DummyVotingEngine(VotingPhaseMixin):
    def __init__(self) -> None:
        self.game_state = object()
        self.locale = Locale("zh-CN")

    def build_player_observation(self, *args, **kwargs) -> str:  # noqa: ANN002, ANN003
        raise AssertionError("Observation is injected by InformationHub, not voting context")


def test_voting_context_does_not_duplicate_player_observation() -> None:
    engine = _DummyVotingEngine()

    context = engine._build_voting_context(object())

    assert "你是 玩家1" not in context
    assert "场上玩家" not in context
    assert "【决策上下文 · MsgHub】" in context
    assert "请各位玩家投票" in context
