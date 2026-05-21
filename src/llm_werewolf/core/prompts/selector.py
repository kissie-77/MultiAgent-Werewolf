import re
import random

from llm_werewolf.core.types import AgentProtocol, PlayerProtocol
from llm_werewolf.core.prompts.manager import PromptManager


def _role_display_name(agent: AgentProtocol, role_name: str) -> str:
    if hasattr(agent, "get_role_display_name"):
        return agent.get_role_display_name()  # type: ignore[no-any-return]
    return role_name


class ActionSelector:
    """Helper for structured Chinese prompts and [[n]] / [[0]]/[[1]] parsing."""

    @staticmethod
    def build_target_selection_prompt(
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        allow_skip: bool = False,
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> str:
        return PromptManager.build_target_selection_prompt(
            role_name,
            action_description,
            possible_targets,
            allow_skip=allow_skip,
            additional_context=additional_context,
            round_number=round_number,
            phase=phase,
        )

    @staticmethod
    def build_yes_no_prompt(
        role_name: str,
        question: str,
        context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> str:
        return PromptManager.build_yes_no_prompt(
            role_name, question, context, round_number=round_number, phase=phase
        )

    @staticmethod
    def build_multi_target_prompt(
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        num_targets: int,
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> str:
        return PromptManager.build_multi_target_prompt(
            role_name,
            action_description,
            possible_targets,
            num_targets,
            additional_context=additional_context,
            round_number=round_number,
            phase=phase,
        )

    parse_yes_no = staticmethod(PromptManager.parse_yes_no)

    @staticmethod
    def parse_target_selection(
        response: str, possible_targets: list[PlayerProtocol], allow_skip: bool = False
    ) -> PlayerProtocol | None:
        """Parse [[n]] or plain number target selection."""
        selection = PromptManager.parse_bracket_number(response)
        if selection is None:
            return None
        if 1 <= selection <= len(possible_targets):
            return possible_targets[selection - 1]
        if allow_skip and selection == len(possible_targets) + 1:
            return None
        return None

    @staticmethod
    def parse_multi_target_selection(
        response: str, possible_targets: list[PlayerProtocol], num_targets: int
    ) -> list[PlayerProtocol] | None:
        """Parse multiple targets from response."""
        numbers = re.findall(r"\d+", response.strip())
        if len(numbers) < num_targets:
            return None

        try:
            selected = []
            for num_str in numbers[:num_targets]:
                selection = int(num_str)
                if 1 <= selection <= len(possible_targets):
                    selected.append(possible_targets[selection - 1])
                else:
                    return None

            if len(selected) != len({p.player_id for p in selected}):
                return None

            return selected
        except (ValueError, IndexError):
            return None

    @staticmethod
    async def get_target_from_agent(
        agent: AgentProtocol,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        allow_skip: bool = False,
        additional_context: str = "",
        fallback_random: bool = True,
        round_number: int | None = None,
        phase: str | None = None,
    ) -> PlayerProtocol | None:
        """Get a target selection from an AI agent."""
        if not possible_targets:
            return None

        display = _role_display_name(agent, role_name)
        prompt = PromptManager.build_target_selection_prompt(
            display,
            action_description,
            possible_targets,
            allow_skip=allow_skip,
            additional_context=additional_context,
            round_number=round_number,
            phase=phase or "夜晚",
        )

        try:
            response = await agent.get_response(prompt)
            target = ActionSelector.parse_target_selection(response, possible_targets, allow_skip)

            if target is not None or allow_skip:
                return target

            if fallback_random:
                return random.choice(possible_targets)  # noqa: S311

        except Exception:
            if fallback_random:
                return random.choice(possible_targets)  # noqa: S311

        return None

    @staticmethod
    async def ask_yes_no(
        agent: AgentProtocol,
        context: str,
        question: str,
        role_name: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> bool:
        """Ask an agent a yes/no question."""
        display = _role_display_name(agent, role_name or "玩家")

        prompt = PromptManager.build_yes_no_prompt(
            display,
            question,
            context,
            round_number=round_number,
            phase=phase or "夜晚",
        )

        try:
            response = await agent.get_response(prompt)
            return PromptManager.parse_yes_no(response)
        except Exception:
            return False

    @staticmethod
    async def select_target(
        agent: AgentProtocol,
        context: str,
        possible_targets: list[PlayerProtocol],
        action_description: str,
        role_name: str = "",
        allow_skip: bool = False,
        fallback_random: bool = True,
        round_number: int | None = None,
        phase: str | None = None,
    ) -> PlayerProtocol | None:
        """Select a target from a list of possible targets."""
        if not role_name:
            role_name = "玩家"

        return await ActionSelector.get_target_from_agent(
            agent,
            role_name,
            action_description,
            possible_targets,
            allow_skip,
            context,
            fallback_random,
            round_number,
            phase,
        )

    @staticmethod
    async def get_free_response(agent: AgentProtocol, context: str, prompt: str) -> str:
        """Get a free-form text response from an agent."""
        full_prompt = f"{context}\n\n{prompt}"
        try:
            return await agent.get_response(full_prompt)
        except Exception:
            return ""
