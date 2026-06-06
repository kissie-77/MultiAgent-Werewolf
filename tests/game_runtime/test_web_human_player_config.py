"""web-human 座位是内建模型，不应被 base_url / api_key_env 校验拦截（M3）。"""

from __future__ import annotations

from llm_werewolf.game_runtime.config.player_config import PlayerConfig


def test_web_human_needs_no_base_url_or_key() -> None:
    cfg = PlayerConfig(name="P1", model="web-human")
    assert cfg.model == "web-human"
    assert cfg.base_url is None
    assert cfg.api_key_env is None


def test_human_and_demo_still_builtin() -> None:
    assert PlayerConfig(name="H", model="human").model == "human"
    assert PlayerConfig(name="D", model="demo").model == "demo"


def test_web_human_model_is_not_overwritten_by_model_env(monkeypatch) -> None:
    # Converting an LLM seat to web-human may leave a stray model_env behind.
    # web-human must stay web-human, not get resolved into the env's model id.
    monkeypatch.setenv("SOME_EP", "deepseek-chat")
    cfg = PlayerConfig(name="P1", model="web-human", model_env="SOME_EP", base_url="https://x")
    assert cfg.model == "web-human"
