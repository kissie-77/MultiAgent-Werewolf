from pathlib import Path

import yaml

from llm_werewolf.game_runtime.config import PlayersConfig
from llm_werewolf.game_runtime.env import load_project_dotenv


def load_config(config_path: str | Path) -> PlayersConfig:
    load_project_dotenv()
    config_path = Path(config_path) if isinstance(config_path, str) else config_path
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = f"Config file is empty or invalid: {config_path}"
        raise ValueError(msg)
    return PlayersConfig(**data)
