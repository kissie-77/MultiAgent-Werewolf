from llm_werewolf.adapter.bridge import WerewolfAdapterBridge as CompatBridge
from llm_werewolf.adapter.structured_invoke import (
    unwrap_structured_metadata as compat_unwrap,
)
from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge as CanonicalBridge
from llm_werewolf.agent_team.structured_invoke import (
    unwrap_structured_metadata as canonical_unwrap,
)


def test_adapter_bridge_modules_are_compatibility_exports() -> None:
    assert CompatBridge is CanonicalBridge
    assert compat_unwrap is canonical_unwrap
