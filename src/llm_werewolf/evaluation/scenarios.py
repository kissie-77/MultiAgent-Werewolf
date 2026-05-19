from pydantic import BaseModel, Field

from llm_werewolf.core.config import create_game_config_from_player_count


class EvaluationScenario(BaseModel):
    """A reproducible offline evaluation scenario."""

    name: str
    num_players: int = Field(ge=6, le=20)
    role_names: list[str]
    language: str = "en-US"
    seed: int = 1
    timeout_seconds: float = 30.0
    repetitions: int = Field(default=1, ge=1)


def smoke_6p_basic(
    seed: int = 1,
    repetitions: int = 1,
    timeout_seconds: float = 30.0,
) -> EvaluationScenario:
    """Create a small no-API scenario for engine smoke evaluation."""
    return EvaluationScenario(
        name="smoke_6p_basic",
        num_players=6,
        role_names=["Werewolf", "Werewolf", "Seer", "Witch", "Villager", "Villager"],
        seed=seed,
        timeout_seconds=timeout_seconds,
        repetitions=repetitions,
    )


def regression_default_demo(
    seed: int = 1,
    repetitions: int = 1,
    timeout_seconds: float = 30.0,
) -> EvaluationScenario:
    """Create a scenario matching the default 16-player demo role preset."""
    config = create_game_config_from_player_count(16)
    return EvaluationScenario(
        name="regression_default_demo",
        num_players=config.num_players,
        role_names=config.role_names,
        language="zh-TW",
        seed=seed,
        timeout_seconds=timeout_seconds,
        repetitions=repetitions,
    )


def get_scenario(
    name: str,
    games: int = 1,
    seed: int = 1,
    timeout_seconds: float = 30.0,
) -> EvaluationScenario:
    """Resolve a named built-in evaluation scenario."""
    if name == "smoke_6p_basic":
        return smoke_6p_basic(seed=seed, repetitions=games, timeout_seconds=timeout_seconds)
    if name == "regression_default_demo":
        return regression_default_demo(seed=seed, repetitions=games, timeout_seconds=timeout_seconds)

    msg = f"Unknown evaluation scenario: {name}"
    raise ValueError(msg)
