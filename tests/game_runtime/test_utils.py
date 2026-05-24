"""game_runtime/utils.py 的测试。"""

from pathlib import Path

from llm_werewolf.game_runtime.utils import load_config


def test_load_config(tmp_path: Path) -> None:
    config_file = tmp_path / "players.yaml"
    config_file.write_text(
        """language: en-US
players:
  - name: Player1
    model: demo
  - name: Player2
    model: demo
  - name: Player3
    model: demo
  - name: Player4
    model: demo
  - name: Player5
    model: demo
  - name: Player6
    model: demo
""",
        encoding="utf-8",
    )

    config = load_config(config_file)
    assert config.language == "en-US"
    assert len(config.players) == 6
    assert config.players[0].name == "Player1"
    assert config.players[0].model == "demo"
