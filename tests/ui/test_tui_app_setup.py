from pathlib import Path
from unittest.mock import MagicMock

from textual.widgets import Input, Select, Switch

from llm_werewolf.ui.tui_app import WerewolfTUI
from llm_werewolf.agent_team.base import DemoAgent, HumanAgent
from llm_werewolf.game_runtime.types import Event, EventType, GamePhase
from llm_werewolf.ui.tui_human_input import TextualHumanInputProvider
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.interface.tui_runtime import TUIRuntime, TUIRunSettings
from llm_werewolf.game_runtime.roles.villager import Villager


async def test_tui_setup_screen_uses_startup_defaults() -> None:
    app = WerewolfTUI(
        startup_settings=TUIRunSettings(
            participation="human_mixed",
            num_players=9,
            enable_sheriff=True,
            show_agent_raw=True,
        )
    )

    async with app.run_test() as pilot:
        await pilot.pause()

        assert app.query_one("#setup_container").display is True
        assert app.query_one("#game_container").display is False
        assert app.query_one("#mode_select", Select).value == "human_mixed"
        assert app.query_one("#num_players_input", Input).value == "9"
        assert app.query_one("#sheriff_switch", Switch).value is True
        assert app.query_one("#raw_output_switch", Switch).value is True
        assert app.query_one("#human_input_controls") is not None


def test_tui_app_applies_human_runtime_with_textual_provider() -> None:
    human_agent = HumanAgent(name="Human", model="human")
    bot_agent = DemoAgent(name="Bot", model="demo")
    human = Player("player_1", "Human", Villager, agent=human_agent, ai_model="human")
    bot = Player("player_2", "Bot", Villager, agent=bot_agent, ai_model="demo")

    engine = MagicMock()
    engine.game_state = MagicMock(players=[human, bot])
    engine.phase_interaction = MagicMock()

    app = WerewolfTUI()
    app.apply_runtime(
        TUIRuntime(
            engine=engine,
            players_config=MagicMock(),
            config_path=Path("configs/human-mixed-deepseek.yaml"),
            participation="human_mixed",
            num_players=2,
        )
    )

    assert app.viewer_id == "player_1"
    provider = engine.phase_interaction.set_human_input_provider.call_args.args[0]
    assert isinstance(provider, TextualHumanInputProvider)


def test_tui_app_routes_events_through_viewer_filter() -> None:
    captured = {}

    class FakeChatPanel:
        def add_event(self, event, *, viewer_id=None) -> None:
            captured["event"] = event
            captured["viewer_id"] = viewer_id

    app = WerewolfTUI()
    app.chat_panel = FakeChatPanel()
    app.viewer_id = "player_1"
    app.game_engine = MagicMock(game_state=MagicMock())

    event = Event(
        event_id="e1",
        event_type=EventType.MESSAGE,
        round_number=1,
        phase=GamePhase.NIGHT,
        message="hidden",
    )

    app.on_game_event(event)

    assert captured == {"event": event, "viewer_id": "player_1"}
