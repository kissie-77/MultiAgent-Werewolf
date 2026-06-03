from llm_werewolf.agent_team.agents.factory import player_id_to_seat, create_react_agent


def test_factory_exports_react_agent_builder() -> None:
    assert callable(create_react_agent)


def test_player_id_to_seat_parses_runtime_player_id() -> None:
    assert player_id_to_seat("player_7") == 7


def test_create_react_agent_prefers_literal_api_key_and_sets_temperature(monkeypatch):
    import llm_werewolf.agent_team.agents.factory as factory_mod
    from llm_werewolf.game_runtime.config.player_config import PlayerConfig

    captured = {}

    class _FakeModel:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(factory_mod, "OpenAIChatModel", _FakeModel)
    # 即使设置了 env，也应优先用字面量 api_key
    monkeypatch.setenv("SHOULD_NOT_BE_USED", "env-key")

    cfg = PlayerConfig(
        name="P1",
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        api_key="sk-literal",
        api_key_env="SHOULD_NOT_BE_USED",
        temperature=0.4,
    )
    factory_mod.create_react_agent(cfg, agent_name="P1", sys_prompt="x")

    assert captured["api_key"] == "sk-literal"
    assert captured["generate_kwargs"]["temperature"] == 0.4


def test_create_react_agent_raises_when_no_key(monkeypatch):
    import pytest
    import llm_werewolf.agent_team.agents.factory as factory_mod
    from llm_werewolf.game_runtime.config.player_config import PlayerConfig

    cfg = PlayerConfig(name="P1", model="deepseek-chat",
                       base_url="https://api.deepseek.com/v1")
    with pytest.raises(ValueError):
        factory_mod.create_react_agent(cfg, agent_name="P1", sys_prompt="x")
