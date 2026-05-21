"""Night action planning for core roles (LLM via PhaseInteraction)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_werewolf.adapter.prompts import GamePrompts
from llm_werewolf.adapter.bridge import WerewolfAdapterBridge
from llm_werewolf.core.actions.villager import (
    GuardProtectAction,
    SeerCheckAction,
    WitchPoisonAction,
    WitchSaveAction,
)
from llm_werewolf.core.actions.werewolf import WerewolfVoteAction
from llm_werewolf.core.roles.werewolf import build_werewolf_team_context
from llm_werewolf.core.types import Camp

if TYPE_CHECKING:
    from llm_werewolf.core.phase_interaction import PhaseInteraction
    from llm_werewolf.core.roles.villager import Guard, Seer, Witch
    from llm_werewolf.core.roles.werewolf import Werewolf
    from llm_werewolf.core.types import ActionProtocol, GameStateProtocol, PlayerProtocol


def _seat_label(player: PlayerProtocol) -> str:
    seat = WerewolfAdapterBridge.get_player_seat(player)
    return str(seat) if seat is not None else player.name


async def plan_werewolf_vote(
    role: Werewolf,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    if not role.player.is_alive():
        return []
    werewolves = [w for w in game_state.get_players_by_camp(Camp.WEREWOLF) if w.is_alive()]
    if not werewolves:
        return []
    possible_targets = [
        p for p in game_state.get_alive_players() if p.get_camp() != Camp.WEREWOLF
    ]
    if not possible_targets or not role.player.agent:
        return []
    werewolf_names = [w.name for w in werewolves]
    context = role.player.agent.get_decision_context() if role.player.agent else ""
    context = "\n\n".join(
        filter(None, [context, build_werewolf_team_context(role, game_state, werewolf_names)])
    )
    target = await interaction.request_seat_choice(
        role.player,
        role.player.agent,
        role_name="Werewolf",
        action_description=GamePrompts.WOLF_OPEN,
        possible_targets=possible_targets,
        allow_skip=False,
        additional_context=context,
        round_number=game_state.round_number,
        phase="Night",
    )
    if target:
        return [WerewolfVoteAction(role.player, target, game_state)]
    return []


async def plan_witch_actions(
    role: Witch,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    if not role.player.is_alive():
        return []
    actions: list[ActionProtocol] = []
    saved_this_night: PlayerProtocol | None = None

    if role.has_save_potion and game_state.werewolf_target:
        target = game_state.get_player(game_state.werewolf_target)
        if target and role.player.agent:
            seat = _seat_label(target)
            use_save = await interaction.request_yes_no(
                role.player,
                role.player.agent,
                "Witch",
                GamePrompts.WITCH_ANTIDOTE.format(target=seat),
                (
                    f"{target.name}（{seat}号）将被狼人击杀。"
                    "解药整局只能用一次。首夜外置位刀口通常可救；"
                    "若你救了某人，本局不要用毒药毒同一人。"
                ),
                round_number=game_state.round_number,
                phase="Night",
            )
            if use_save:
                actions.append(WitchSaveAction(role.player, target, game_state))
                saved_this_night = target

    if role.has_poison_potion and role.player.agent:
        use_poison = await interaction.request_yes_no(
            role.player,
            role.player.agent,
            "Witch",
            GamePrompts.WITCH_POISON,
            "毒药整局只能用一次。只在高度怀疑时使用；不要毒明好人或你刚救过的人。",
            round_number=game_state.round_number,
            phase="Night",
        )
        if use_poison:
            possible_targets = [
                p
                for p in game_state.get_alive_players()
                if p.player_id != role.player.player_id
                and (
                    saved_this_night is None
                    or p.player_id != saved_this_night.player_id
                )
            ]
            if possible_targets:
                target = await interaction.request_seat_choice(
                    role.player,
                    role.player.agent,
                    role_name="Witch",
                    action_description=GamePrompts.WITCH_POISON_TARGET,
                    possible_targets=possible_targets,
                    allow_skip=True,
                    additional_context="若不确定，请跳过（[[0]]）。",
                    fallback_random=False,
                    round_number=game_state.round_number,
                    phase="Night",
                )
                if target:
                    actions.append(WitchPoisonAction(role.player, target, game_state))
    return actions


async def plan_guard_protect(
    role: Guard,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    if not role.player.is_alive():
        return []
    possible_targets = [
        p for p in game_state.get_alive_players() if p.player_id != role.last_protected
    ]
    if not possible_targets or not role.player.agent:
        return []
    context = GamePrompts.GUARD_ACTION
    if role.last_protected:
        last_player = game_state.get_player(role.last_protected)
        if last_player:
            context += f"\n\n你不能连续两晚守护 {last_player.name}（{_seat_label(last_player)}号）。"
    target = await interaction.request_seat_choice(
        role.player,
        role.player.agent,
        role_name="Guard",
        action_description=GamePrompts.GUARD_ACTION,
        possible_targets=possible_targets,
        allow_skip=False,
        additional_context=context,
        round_number=game_state.round_number,
        phase="Night",
    )
    if target:
        return [GuardProtectAction(role.player, target, game_state)]
    return []


async def plan_seer_check(
    role: Seer,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    if not role.player.is_alive():
        return []
    possible_targets = [
        p for p in game_state.get_alive_players() if p.player_id != role.player.player_id
    ]
    if not possible_targets or not role.player.agent:
        return []
    checked_info = []
    for round_num, player_id in game_state.seer_checked.items():
        player = game_state.get_player(player_id)
        if player:
            checked_info.append(f"第{round_num}轮：{_seat_label(player)}号 {player.name}")
    context = GamePrompts.PROPHET_ACTION
    if checked_info:
        context += f"\n\n已查验：{', '.join(checked_info)}。尽量不要重复验同一人。"
    target = await interaction.request_seat_choice(
        role.player,
        role.player.agent,
        role_name="Seer",
        action_description=GamePrompts.PROPHET_ACTION,
        possible_targets=possible_targets,
        allow_skip=False,
        additional_context=context,
        round_number=game_state.round_number,
        phase="Night",
    )
    if target:
        return [SeerCheckAction(role.player, target, game_state)]
    return []
