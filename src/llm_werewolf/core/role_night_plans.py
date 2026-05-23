"""各角色夜间行动规划（通过 PhaseInteraction / InformationHub 调用 LLM）。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from llm_werewolf.adapter.prompts import GamePrompts
from llm_werewolf.adapter.bridge import WerewolfAdapterBridge
from llm_werewolf.core.phase_outputs import ActionPhase
from llm_werewolf.core.actions.villager import (
    CupidLinkAction,
    GraveyardKeeperCheckAction,
    GuardProtectAction,
    RavenMarkAction,
    SeerCheckAction,
    WitchPoisonAction,
    WitchSaveAction,
)
from llm_werewolf.core.actions.werewolf import (
    GuardianWolfProtectAction,
    NightmareWolfBlockAction,
    WerewolfVoteAction,
    WhiteWolfKillAction,
    WolfBeautyCharmAction,
)
from llm_werewolf.core.roles.werewolf import build_werewolf_team_context
from llm_werewolf.core.types import Camp

if TYPE_CHECKING:
    from llm_werewolf.core.phase_interaction import PhaseInteraction
    from llm_werewolf.core.roles.base import Role
    from llm_werewolf.core.roles.villager import Cupid, Guard, GraveyardKeeper, Seer, Witch
    from llm_werewolf.core.roles.werewolf import (
        BloodMoonApostle,
        GuardianWolf,
        NightmareWolf,
        WhiteWolf,
        WolfBeauty,
    )
    from llm_werewolf.core.types import ActionProtocol, GameStateProtocol, PlayerProtocol

NightPlanner = Callable[
    ["Role", "GameStateProtocol", "PhaseInteraction"],
    Awaitable[list["ActionProtocol"]],
]


def _seat_label(player: PlayerProtocol) -> str:
    seat = WerewolfAdapterBridge.get_player_seat(player)
    return str(seat) if seat is not None else player.name


def _werewolf_context(role: Role, game_state: GameStateProtocol) -> str:
    werewolves = [w for w in game_state.get_players_by_camp(Camp.WEREWOLF) if w.is_alive()]
    names = [w.name for w in werewolves]
    parts = []
    if role.player.agent:
        parts.append(role.player.agent.get_decision_context())
    parts.append(build_werewolf_team_context(role, game_state, names))
    return "\n\n".join(filter(None, parts))


async def _plan_werewolf_pack_vote(
    role: Role,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
    *,
    role_name: str,
) -> list[ActionProtocol]:
    if not role.player.is_alive() or not role.player.agent:
        return []
    targets = [
        p for p in game_state.get_alive_players() if p.get_camp() != Camp.WEREWOLF
    ]
    if not targets:
        return []
    target = await interaction.request_seat_choice(
        role.player,
        role.player.agent,
        role_name=role_name,
        action_description=GamePrompts.WOLF_OPEN,
        possible_targets=targets,
        allow_skip=False,
        additional_context=_werewolf_context(role, game_state),
        round_number=game_state.round_number,
        phase="Night",
        action_phase=ActionPhase.NIGHT_KILL_VOTE,
    )
    if target:
        return [WerewolfVoteAction(role.player, target, game_state)]
    return []


async def plan_werewolf_vote(
    role,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    return await _plan_werewolf_pack_vote(
        role, game_state, interaction, role_name="Werewolf"
    )


async def plan_alpha_wolf_vote(role, game_state, interaction):
    return await _plan_werewolf_pack_vote(role, game_state, interaction, role_name="Alpha Wolf")


async def plan_hidden_wolf_vote(role, game_state, interaction):
    return await _plan_werewolf_pack_vote(role, game_state, interaction, role_name="Hidden Wolf")


async def plan_white_wolf(
    role: WhiteWolf,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    actions = await _plan_werewolf_pack_vote(
        role, game_state, interaction, role_name="White Wolf"
    )
    if game_state.round_number % 2 == 1 and role.player.agent:
        wolf_targets = [
            p
            for p in game_state.get_players_by_camp(Camp.WEREWOLF)
            if p.is_alive() and p.player_id != role.player.player_id
        ]
        if wolf_targets:
            target = await interaction.request_seat_choice(
                role.player,
                role.player.agent,
                role_name="White Wolf",
                action_description="选择一名狼人队友击杀（或跳过）",
                possible_targets=wolf_targets,
                allow_skip=True,
                additional_context="可选击杀一名狼队友；不确定请跳过。",
                fallback_random=False,
                round_number=game_state.round_number,
                phase="Night",
            )
            if target:
                actions.append(WhiteWolfKillAction(role.player, target, game_state))
    return actions


async def plan_wolf_beauty(
    role: WolfBeauty,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    actions = await _plan_werewolf_pack_vote(
        role, game_state, interaction, role_name="Wolf Beauty"
    )
    if not role.charmed_player and role.player.agent:
        targets = game_state.get_alive_players()
        if targets:
            target = await interaction.request_seat_choice(
                role.player,
                role.player.agent,
                role_name="Wolf Beauty",
                action_description="选择一名玩家魅惑",
                possible_targets=targets,
                allow_skip=False,
                additional_context="你死亡时魅惑对象殉情；整局只能魅惑一次。",
                round_number=game_state.round_number,
                phase="Night",
            )
            if target:
                actions.append(WolfBeautyCharmAction(role.player, target, game_state))
    return actions


async def plan_guardian_wolf(
    role: GuardianWolf,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    actions = await _plan_werewolf_pack_vote(
        role, game_state, interaction, role_name="Guardian Wolf"
    )
    wolf_targets = [
        p for p in game_state.get_players_by_camp(Camp.WEREWOLF) if p.is_alive()
    ]
    if wolf_targets and role.player.agent:
        target = await interaction.request_seat_choice(
            role.player,
            role.player.agent,
            role_name="Guardian Wolf",
            action_description="选择一名狼人队友保护",
            possible_targets=wolf_targets,
            allow_skip=True,
            additional_context="可保护一名狼队友免受当晚击杀威胁；不确定请跳过。",
            fallback_random=False,
            round_number=game_state.round_number,
            phase="Night",
        )
        if target:
            actions.append(GuardianWolfProtectAction(role.player, target, game_state))
    return actions


async def plan_nightmare_wolf(
    role: NightmareWolf,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    actions: list[ActionProtocol] = []
    block_targets = game_state.get_alive_players(except_ids=[role.player.player_id])
    if block_targets and role.player.agent:
        target = await interaction.request_seat_choice(
            role.player,
            role.player.agent,
            role_name="Nightmare Wolf",
            action_description="选择一名玩家封锁其技能",
            possible_targets=block_targets,
            allow_skip=True,
            additional_context="封锁后该玩家本夜无法发动技能；不确定请跳过。",
            fallback_random=False,
            round_number=game_state.round_number,
            phase="Night",
        )
        if target:
            actions.append(NightmareWolfBlockAction(role.player, target, game_state))
    actions.extend(
        await _plan_werewolf_pack_vote(
            role, game_state, interaction, role_name="Nightmare Wolf"
        )
    )
    return actions


async def plan_blood_moon_apostle(
    role: BloodMoonApostle,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    from llm_werewolf.core.roles.werewolf import BloodMoonApostle as BmaClass

    if not role.transformed:
        werewolves = [
            p
            for p in game_state.get_players_by_camp(Camp.WEREWOLF)
            if p.is_alive()
            and p.player_id != role.player.player_id
            and not isinstance(p.role, BmaClass)
        ]
        if not werewolves and role.player.is_alive():
            role.transformed = True
        return []

    if role.transformed and role.player.is_alive() and role.player.agent:
        return await _plan_werewolf_pack_vote(
            role, game_state, interaction, role_name="Blood Moon Apostle"
        )
    return []


async def plan_witch_actions(
    role: Witch,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    if not role.player.is_alive() or not role.player.agent:
        return []

    has_save = role.has_save_potion
    has_poison = role.has_poison_potion
    if not has_save and not has_poison:
        return []

    victim: PlayerProtocol | None = None
    can_see_victim = False
    victim_line = ""
    if has_save and game_state.werewolf_target:
        victim = game_state.get_player(game_state.werewolf_target)
        if victim:
            can_see_victim = True
            seat = _seat_label(victim)
            victim_line = (
                f"今晚狼人刀口：{victim.name}（{seat}号）。"
                "你仍持有解药，可以选择救他/她。"
            )

    poison_targets = [
        p
        for p in game_state.get_alive_players()
        if p.player_id != role.player.player_id
    ]

    notes = [
        f"解药：{'可用' if has_save else '已用完'}。",
        f"毒药：{'可用' if has_poison else '已用完'}。",
    ]
    if not can_see_victim and has_poison:
        notes.append("解药已耗尽，本夜不会告知刀口身份。")

    decision = await interaction.request_witch_night_choice(
        role.player,
        role.player.agent,
        role_name="Witch",
        can_see_victim=can_see_victim,
        victim_line=victim_line,
        poison_targets=poison_targets if has_poison else [],
        additional_context="\n".join(notes),
        round_number=game_state.round_number,
        phase="Night",
    )

    actions: list[ActionProtocol] = []
    saved_this_night: PlayerProtocol | None = None

    if (
        decision.action == "save"
        and has_save
        and can_see_victim
        and victim is not None
    ):
        actions.append(WitchSaveAction(role.player, victim, game_state))
        saved_this_night = victim

    if decision.action == "poison" and has_poison and decision.seat > 0:
        poison_candidates = [
            p
            for p in poison_targets
            if saved_this_night is None or p.player_id != saved_this_night.player_id
        ]
        poison_target = WerewolfAdapterBridge.resolve_player_by_seat(
            decision.seat, poison_candidates
        )
        if poison_target:
            actions.append(WitchPoisonAction(role.player, poison_target, game_state))

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
        action_phase=ActionPhase.NIGHT_SKILL_TARGET,
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
        action_phase=ActionPhase.NIGHT_SKILL_TARGET,
    )
    if target:
        return [SeerCheckAction(role.player, target, game_state)]
    return []


async def plan_cupid_link(
    role: Cupid,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    if game_state.round_number != 1 or role.has_linked or not role.player.agent:
        return []
    possible_targets = game_state.get_alive_players()
    if len(possible_targets) < 2:
        return []
    selected = await interaction.request_multi_targets(
        role.player,
        role.player.agent,
        role_name="Cupid",
        action_description="选择两名玩家结为情侣",
        possible_targets=possible_targets,
        num_targets=2,
        additional_context="情侣互知身份，一方死亡另一方殉情。",
        round_number=game_state.round_number,
        phase="Night",
    )
    if selected and len(selected) == 2:
        return [CupidLinkAction(role.player, selected[0], selected[1], game_state)]
    return []


async def plan_raven_mark(
    role,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    if not role.player.is_alive() or not role.player.agent:
        return []
    possible_targets = game_state.get_alive_players()
    if not possible_targets:
        return []
    target = await interaction.request_seat_choice(
        role.player,
        role.player.agent,
        role_name="Raven",
        action_description="选择一名玩家施加诅咒",
        possible_targets=possible_targets,
        allow_skip=False,
        additional_context="被标记者在次日投票阶段会额外获得一票。",
        round_number=game_state.round_number,
        phase="Night",
    )
    if target:
        return [RavenMarkAction(role.player, target, game_state)]
    return []


async def plan_graveyard_check(
    role,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    if not role.player.is_alive() or not role.player.agent:
        return []
    dead_players = game_state.get_dead_players()
    if not dead_players:
        return []
    target = await interaction.request_seat_choice(
        role.player,
        role.player.agent,
        role_name="Graveyard Keeper",
        action_description="选择一名已死亡玩家查验身份",
        possible_targets=dead_players,
        allow_skip=True,
        additional_context="可查验一名死者的真实阵营；不确定请跳过。",
        fallback_random=False,
        round_number=game_state.round_number,
        phase="Night",
    )
    if target:
        return [GraveyardKeeperCheckAction(role.player, target, game_state)]
    return []


NIGHT_PLANNERS: dict[str, NightPlanner] = {
    "Werewolf": plan_werewolf_vote,
    "Alpha Wolf": plan_alpha_wolf_vote,
    "White Wolf": plan_white_wolf,
    "Wolf Beauty": plan_wolf_beauty,
    "Guardian Wolf": plan_guardian_wolf,
    "Hidden Wolf": plan_hidden_wolf_vote,
    "Blood Moon Apostle": plan_blood_moon_apostle,
    "Nightmare Wolf": plan_nightmare_wolf,
    "Witch": plan_witch_actions,
    "Guard": plan_guard_protect,
    "Seer": plan_seer_check,
    "Cupid": plan_cupid_link,
    "Raven": plan_raven_mark,
    "Graveyard Keeper": plan_graveyard_check,
}


def _resolve_night_planner(role_name: str) -> NightPlanner | None:
    """在调用时解析 planner，以便测试可 patch planner 函数。"""
    return NIGHT_PLANNERS.get(role_name)


async def dispatch_night_plan(
    role: Role,
    game_state: GameStateProtocol,
    interaction: PhaseInteraction,
) -> list[ActionProtocol]:
    """经 Hub 路由夜间行动；未注册的角色返回 []。"""
    planner = _resolve_night_planner(role.name)
    if planner is None:
        return []
    return await planner(role, game_state, interaction)
