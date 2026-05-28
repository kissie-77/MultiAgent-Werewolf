from llm_werewolf.agent_team.agents.factory import create_react_agent, player_id_to_seat


def test_factory_exports_react_agent_builder() -> None:
    assert callable(create_react_agent)


def test_player_id_to_seat_parses_runtime_player_id() -> None:
    assert player_id_to_seat("player_7") == 7
