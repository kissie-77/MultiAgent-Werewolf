from llm_werewolf.agent_team.factory import create_react_agent as canonical_create
from llm_werewolf.adapter.factory import create_react_agent as compat_create


def test_adapter_factory_is_compatibility_export() -> None:
    assert compat_create is canonical_create
