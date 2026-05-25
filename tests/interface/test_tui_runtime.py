from pathlib import Path

from llm_werewolf.interface.tui import main
from llm_werewolf.interface.tui_runtime import TUIRunSettings, create_tui_runtime


def _write_demo_roster(path: Path) -> None:
    path.write_text(
        """language: zh-CN
player_roster:
  count: 12
  mode: all_agent
  llm_template:
    name_prefix: DemoPlayer
    model: demo
""",
        encoding="utf-8",
    )


def test_create_tui_runtime_applies_count_and_sheriff_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "demo-roster.yaml"
    _write_demo_roster(config_path)

    runtime = create_tui_runtime(
        TUIRunSettings(
            config=str(config_path),
            num_players=7,
            enable_sheriff=True,
        )
    )

    assert runtime.config_path == config_path
    assert runtime.num_players == 7
    assert runtime.engine.config.num_players == 7
    assert runtime.engine.config.enable_sheriff is True
    assert runtime.engine.game_state is not None
    assert len(runtime.engine.game_state.players) == 7


def test_tui_main_passes_arguments_as_startup_defaults(monkeypatch) -> None:
    captured = {}

    def fake_run_tui(*, startup_settings) -> None:
        captured["settings"] = startup_settings

    monkeypatch.setattr("llm_werewolf.interface.tui.run_tui", fake_run_tui)

    main(
        config="configs/human-mixed-deepseek.yaml",
        participation="human_mixed",
        rules="badge_flow",
        num_players=9,
        enable_sheriff=True,
        show_agent_raw=True,
    )

    settings = captured["settings"]
    assert settings.config == "configs/human-mixed-deepseek.yaml"
    assert settings.participation == "human_mixed"
    assert settings.rules == "badge_flow"
    assert settings.num_players == 9
    assert settings.enable_sheriff is True
    assert settings.show_agent_raw is True
