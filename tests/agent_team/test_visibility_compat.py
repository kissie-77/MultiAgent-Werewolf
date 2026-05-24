from llm_werewolf.adapter.information_hub import InformationHub as CompatHub
from llm_werewolf.adapter.message_router import MessageRouter as CompatRouter
from llm_werewolf.adapter.visibility import VisibilityChannel as CompatChannel
from llm_werewolf.agent_team.information_hub import InformationHub as CanonicalHub
from llm_werewolf.agent_team.message_router import MessageRouter as CanonicalRouter
from llm_werewolf.agent_team.visibility import VisibilityChannel as CanonicalChannel


def test_adapter_visibility_modules_are_compatibility_exports() -> None:
    assert CompatHub is CanonicalHub
    assert CompatRouter is CanonicalRouter
    assert CompatChannel is CanonicalChannel
