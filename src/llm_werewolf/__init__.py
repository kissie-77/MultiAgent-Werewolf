from pathlib import Path
from importlib.metadata import PackageNotFoundError, version

import logfire

logfire.configure(send_to_logfire=False)

from llm_werewolf.game_runtime import GameEngine  # noqa: E402

package_name = Path(__file__).parent.name
__package__ = package_name
try:
    __version__ = version(package_name)
except PackageNotFoundError:
    __version__ = "0.1.0-dev"

__all__ = ["GameEngine", "__version__"]
