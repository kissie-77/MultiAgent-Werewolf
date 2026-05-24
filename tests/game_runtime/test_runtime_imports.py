from llm_werewolf import GameEngine
from llm_werewolf.game_runtime import GameEngine as CoreGameEngine
from llm_werewolf.game_runtime.config import GameConfig as CoreGameConfig
from llm_werewolf.game_runtime import GameEngine as RuntimeGameEngine
from llm_werewolf.game_runtime.config import GameConfig


def test_game_runtime_is_canonical_runtime_package() -> None:
    assert RuntimeGameEngine is GameEngine
    assert CoreGameEngine is RuntimeGameEngine
    assert CoreGameConfig is GameConfig
