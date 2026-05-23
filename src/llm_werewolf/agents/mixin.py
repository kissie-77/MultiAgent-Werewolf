"""Mixin for agents using unified AgentScope-style prompts."""

from llm_werewolf.core.roles.catalog import get_definition_by_role_class
from llm_werewolf.core.roles.definition import RoleDefinition
from llm_werewolf.core.prompts.manager import PromptManager


class PromptAgentMixin:
    """Inject system + identity prompts after role assignment."""

    role_definition: RoleDefinition | None = None
    seat_number: int = 0
    plan: str = "自由发挥"
    chat_history: list[dict[str, str]]

    def bind_role(self, role_class: type, seat_number: int, plan: str | None = None) -> None:
        """Bind role definition and rebuild prompt history (system + identity)."""
        self.role_definition = get_definition_by_role_class(role_class)
        self.seat_number = seat_number
        if plan:
            self.plan = plan
        name = getattr(self, "name", "玩家")
        self.chat_history = PromptManager.build_initial_chat_history(
            self.role_definition,
            player_name=name,
            seat_number=seat_number,
            plan=self.plan,
        )

    def get_role_display_name(self) -> str:
        """Chinese display name for prompts."""
        if self.role_definition:
            return self.role_definition.display_name
        return "玩家"
