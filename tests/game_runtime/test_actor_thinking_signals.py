"""InformationHub emits actor_thinking before each roundtable speech step."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_werewolf.agent_team.communication.information_hub import InformationHub
from llm_werewolf.game_runtime.events.visibility import VisibilityChannel
from llm_werewolf.strategy.contracts.decisions import SpeechDecision


def test_resolve_thinking_context_mappings() -> None:
    assert (
        InformationHub.resolve_thinking_context(
            channel=VisibilityChannel.PUBLIC, phase="sheriff_election"
        )
        == "sheriff_speech"
    )
    assert (
        InformationHub.resolve_thinking_context(
            channel=VisibilityChannel.PUBLIC, phase="day_discussion"
        )
        == "day_speech"
    )
    assert (
        InformationHub.resolve_thinking_context(
            channel=VisibilityChannel.WOLF_TEAM, phase="night"
        )
        == "werewolf_chat"
    )


@pytest.mark.asyncio
async def test_run_roundtable_emits_actor_thinking_before_speech() -> None:
    hub = InformationHub()
    calls: list[tuple[str, str]] = []

    speaker = MagicMock()
    speaker.is_alive.return_value = True
    speaker.agent = MagicMock()
    speaker.agent.model = "demo"
    speaker.name = "Alice"
    speaker.player_id = "player_1"
    speaker.get_role_name.return_value = "Seer"

    react_agent = MagicMock()
    hub.set_context_provider(
        build_observation=lambda _p: "ctx",
        get_alive_players=lambda: [speaker],
    )
    hub.set_actor_thinking_callback(
        lambda actor, context: calls.append((actor.player_id, context))
    )

    with (
        patch.object(hub, "_react_agent", return_value=react_agent),
        patch(
            "llm_werewolf.agent_team.communication.information_hub.WerewolfAdapterBridge.request_speech",
            new_callable=AsyncMock,
            return_value=SpeechDecision(
                public_speech="hello from the seer today",
                private_thought=None,
            ),
        ),
        patch(
            "llm_werewolf.agent_team.communication.information_hub.MsgHub",
        ) as msg_hub_cls,
    ):
        hub_ctx = AsyncMock()
        hub_ctx.__aenter__.return_value = hub_ctx
        hub_ctx.__aexit__.return_value = None
        msg_hub_cls.return_value = hub_ctx

        await hub.run_roundtable(
            [speaker],
            channel=VisibilityChannel.PUBLIC,
            context_builder=lambda _p: "ctx",
            instruction="speak",
            phase="day_discussion",
            round_number=1,
            audience=[speaker],
        )

    assert calls == [("player_1", "day_speech")]
