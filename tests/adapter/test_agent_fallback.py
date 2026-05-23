"""Tests for AgentScopeWerewolfAgent fallback responses."""

import pytest

from llm_werewolf.adapter.agent import AgentScopeWerewolfAgent


@pytest.fixture
def wolf_agent() -> AgentScopeWerewolfAgent:
    return AgentScopeWerewolfAgent(name="W1", role="wolf", number=3)


@pytest.fixture
def villager_agent() -> AgentScopeWerewolfAgent:
    return AgentScopeWerewolfAgent(name="V1", role="villager", number=1)


class TestWerewolfPrivateFallback:
    def test_no_good_identity_in_wolf_night_chat(self, wolf_agent: AgentScopeWerewolfAgent) -> None:
        prompt = "\n".join([
            "You are W1, a Werewolf.",
            "Discuss with your fellow werewolves who should be eliminated tonight.",
            "Available targets: P4, P5, P12.",
        ])
        for _ in range(20):
            text = wolf_agent._generate_fallback_response(prompt, "empty")
            assert "好人" not in text
            assert "狼人" not in text
            assert "我是" not in text
            assert "I am" not in text.lower()

    def test_wolf_team_marker_detected(self, wolf_agent: AgentScopeWerewolfAgent) -> None:
        assert wolf_agent._is_werewolf_private_chat("Werewolf team discussion:\nA: hi")


class TestPublicFallback:
    def test_no_role_reveal_on_day_speech(self, villager_agent: AgentScopeWerewolfAgent) -> None:
        prompt = "Share your thoughts.\nProvide a brief statement for discussion."
        for _ in range(20):
            text = villager_agent._generate_fallback_response(prompt, "err")
            assert "我是" not in text
            assert villager_agent.role_name not in text


class TestStructuredFallback:
    def test_yes_no(self, wolf_agent: AgentScopeWerewolfAgent) -> None:
        prompt = "Please respond with ONLY 'YES' or 'NO'."
        assert wolf_agent._generate_fallback_response(prompt, "x") in {
            "[[0]]",
            "[[1]]",
            "YES",
            "NO",
        }

    def test_numeric_target(self, wolf_agent: AgentScopeWerewolfAgent) -> None:
        prompt = (
            "You are a Werewolf.\nAvailable targets:\n1. P4\n2. P5\n"
            "Please select a target by responding with ONLY the number"
        )
        assert wolf_agent._generate_fallback_response(prompt, "x") in {"1", "2"}
