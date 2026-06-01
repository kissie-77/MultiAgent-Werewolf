from __future__ import annotations

from llm_werewolf.agent_team.agents.agentscope_agent import AgentScopeWerewolfAgent


def test_pick_seat_from_message_excludes_self() -> None:
    agent = AgentScopeWerewolfAgent(name="玩家6", number=6)

    for _ in range(20):
        seat = agent._pick_seat_from_message("今晚可以考虑3号、6号、9号，大家讨论一下。")
        assert seat in {3, 9}


def test_werewolf_team_fallback_speech_never_targets_self() -> None:
    agent = AgentScopeWerewolfAgent(name="玩家6", number=6)

    for _ in range(20):
        text = agent._werewolf_team_fallback_speech("今晚可以考虑6号、8号、10号。")
        assert "6号" not in text
