"""Provider registry and env template consistency."""

from llm_werewolf.game_runtime.config.provider_registry import (
    DEFAULT_PROVIDER_ID,
    SUPPORTED_PROVIDER_IDS,
    get_provider,
    all_env_var_names,
)


def test_eight_providers_registered() -> None:
    assert SUPPORTED_PROVIDER_IDS == (
        "doubao",
        "deepseek",
        "openai",
        "gemini",
        "claude",
        "kimi",
        "glm",
        "minimax",
    )
    assert DEFAULT_PROVIDER_ID == "doubao"


def test_doubao_uses_ark_env_names() -> None:
    spec = get_provider("doubao")
    assert spec.api_key_env == "ARK_API_KEY"
    assert spec.model_env == "ARK_EP"


def test_env_var_names_are_unique() -> None:
    names = list(all_env_var_names())
    assert len(names) == len(set(names))


def test_unknown_provider_raises() -> None:
    try:
        get_provider("unknown")
    except ValueError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("expected ValueError")
