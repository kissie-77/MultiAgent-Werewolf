"""各角色夜间行动规划（通过 PhaseInteraction / InformationHub 调用 LLM）。"""

from __future__ import annotations

from typing import TYPE_CHECKING
from collections.abc import Callable, Awaitable

from llm_werewolf.game_runtime.seat import get_player_seat, resolve_player_by_seat
from llm_werewolf.game_runtime.types import Camp
from llm_werewolf.strategy.role_prompts import GamePrompts
from llm_werewolf.strategy.phase_outputs import ActionPhase
from llm_werewolf.game_runtime.roles.names import (
    is_untransformed_blood_moon,
    participates_in_wolf_team,
)
from llm_werewolf.game_runtime.roles.werewolf import build_werewolf_team_context
from llm_werewolf.game_runtime.actions.villager import (
    CupidLinkAction,
    RavenMarkAction,
    SeerCheckAction,
    WitchSaveAction,
    WitchPoisonAction,
    GuardProtectAction,
    GraveyardKeeperCheckAction,
)
from llm_werewolf.game_runtime.actions.werewolf import (
    WerewolfVoteAction,
    WhiteWolfKillAction,
    WolfBeautyCharmAction,
    NightmareWolfBlockAction,
    GuardianWolfProtectAction,
)

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import ActionProtocol, PlayerProtocol, GameStateProtocol
    from llm_werewolf.game_runtime.roles.base import Role
    from llm_werewolf.game_runtime.roles.villager import Seer, Cupid, Guard, Witch
    from llm_werewolf.game_runtime.roles.werewolf import (
        WhiteWolf,
        WolfBeauty,
        GuardianWolf,
        NightmareWolf,
        BloodMoonApostle,
    )
    from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction

NightPlanner = Callable[
    ["Role", "GameStateProtocol", "PhaseInteraction"], Awaitable[list["ActionProtocol"]]
]


def _seat_label(player: PlayerProtocol) -> str:
    seat = get_player_seat(player)
    return str(seat) if seat is not None else player.name


def _attach_decision_metadata(
    action: ActionProtocol, target: PlayerProtocol, decision: object | None
) -> ActionProtocol:
    metadata = {
        "decision_seat": get_player_seat(target),
        "resolved_target_id": target.player_id,
        "resolved_target_name": target.name,
        "fallback": False,
    }
    if decision is not None and hasattr(decision, "model_dump"):
        metadata["structured_decision"] = decision.model_dump(mode="json")
    setattr(action, "_decision_metadata", metadata)
    return action


def _werewolf_context(role: Role, game_state: GameStateProtocol) -> str:
    werewolves = [
        w for w in game_state.get_alive_players() if participates_in_wolf_team(w)
    ]
    names = [w.name for w in werewolves]
    return build_werewolf_team_context(role, game_state, names)


async def _plan_werewolf_pack_vote(
    role: Role, game_state: GameStateProtocol, interaction: PhaseInteraction, *, role_name: str
) -> list[ActionProtocol]:
    if not role.player.is_alive() or not role.player.agent:
        return []
    targets = [
        p for p in game_state.get_alive_players() if not participates_in_wolf_team(p)
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
        fallback_random=False,
        round_number=game_state.round_number,
        phase="Night",
        action_phase=ActionPhase.NIGHT_KILL_VOTE,
    )
    if target:
        return [WerewolfVoteAction(role.player, target, game_state)]
    return []


async def plan_werewolf_vote(
    role, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    return await _plan_werewolf_pack_vote(role, game_state, interaction, role_name="Werewolf")


async def dispatch_werewolf_vote_plan(
    role: Role, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    """收集狼队刀票；所有参与狼队的角色在狼票阶段都走这里。"""
    return await _plan_werewolf_pack_vote(
        role,
        game_state,
        interaction,
        role_name=role.name,
    )


async def plan_alpha_wolf_vote(role, game_state, interaction):
    return await _plan_werewolf_pack_vote(role, game_state, interaction, role_name="Alpha Wolf")


async def plan_hidden_wolf_vote(role, game_state, interaction):
    return await _plan_werewolf_pack_vote(role, game_state, interaction, role_name="Hidden Wolf")


async def plan_white_wolf(
    role: WhiteWolf, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    actions: list[ActionProtocol] = []
    if game_state.round_number % 2 == 1 and role.player.agent:
        wolf_targets = [
            p
            for p in game_state.get_alive_players()
            if p.is_alive()
            and p.player_id != role.player.player_id
            and participates_in_wolf_team(p)
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
    role: WolfBeauty, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    actions: list[ActionProtocol] = []
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
                fallback_random=False,
                round_number=game_state.round_number,
                phase="Night",
            )
            if target:
                actions.append(WolfBeautyCharmAction(role.player, target, game_state))
    return actions


async def plan_guardian_wolf(
    role: GuardianWolf, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    actions: list[ActionProtocol] = []
    wolf_targets = [
        p for p in game_state.get_alive_players() if participates_in_wolf_team(p)
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
    role: NightmareWolf, game_state: GameStateProtocol, interaction: PhaseInteraction
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
    return actions


async def plan_blood_moon_apostle(
    role: BloodMoonApostle, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    if not role.transformed:
        return []

    if role.player.is_alive() and role.player.agent:
        return await _plan_werewolf_pack_vote(
            role, game_state, interaction, role_name="Blood Moon Apostle"
        )
    return []


def blood_moon_other_wolves_alive(game_state: GameStateProtocol, apostle: PlayerProtocol) -> bool:
    """除给定血月使徒外是否仍有存活狼人（不含其他未变身血月）。"""
    from llm_werewolf.game_runtime.roles.werewolf import BloodMoonApostle as BmaClass

    for player in game_state.get_players_by_camp(Camp.WEREWOLF):
        if not player.is_alive() or player.player_id == apostle.player_id:
            continue
        if isinstance(player.role, BmaClass) and is_untransformed_blood_moon(player.role):
            continue
        return True
    return False


async def offer_blood_moon_transform(
    role: BloodMoonApostle, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> bool:
    """当其余狼人全灭时，由 LLM 决定是否变身。返回是否已变身。"""
    if role.transformed or not role.player.is_alive() or not role.player.agent:
        return False
    if blood_moon_other_wolves_alive(game_state, role.player):
        return False

    yes = await interaction.request_yes_no(
        role.player,
        role.player.agent,
        role_name="Blood Moon Apostle",
        question="所有狼人队友已阵亡。是否在本夜变身为狼人，加入狼队击杀？",
        context="变身前你不与狼队同醒；变身后将参与狼队讨论与投票。整局仅可变身一次。",
        round_number=game_state.round_number,
        phase="Night",
    )
    if yes:
        role.transformed = True
    return role.transformed


async def plan_witch_actions(
    role: Witch, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    if not role.player.is_alive() or not role.player.agent:
        return []

    has_save = role.has_save_potion
    has_poison = role.has_poison_potion
    if not has_save and not has_poison:
        return []

    victim: PlayerProtocol | None = None
    can_see_victim = False
    can_save = False
    victim_line = ""
    if game_state.werewolf_target:
        victim = game_state.get_player(game_state.werewolf_target)
        if victim:
            can_see_victim = True
            can_save = has_save
            seat = _seat_label(victim)
            if has_save:
                victim_line = (
                    f"今晚狼人刀口：{victim.name}（{seat}号）。你仍持有解药，可以选择救他/她。"
                )
            else:
                victim_line = (
                    f"今晚狼人刀口：{victim.name}（{seat}号）。你的解药已用完，不能救；"
                    "你仍可选择是否使用毒药。"
                )

    poison_targets = [
        p for p in game_state.get_alive_players() if p.player_id != role.player.player_id
    ]

    notes = [
        f"解药：{'可用' if has_save else '已用完'}。",
        f"毒药：{'可用' if has_poison else '已用完'}。",
    ]

    decision = await interaction.request_witch_night_choice(
        role.player,
        role.player.agent,
        role_name="Witch",
        can_see_victim=can_see_victim,
        can_save=can_save,
        victim_line=victim_line,
        poison_targets=poison_targets if has_poison else [],
        additional_context="\n".join(notes),
        round_number=game_state.round_number,
        phase="Night",
    )

    actions: list[ActionProtocol] = []
    saved_this_night: PlayerProtocol | None = None

    if decision.action == "save" and has_save and can_see_victim and victim is not None:
        action = WitchSaveAction(role.player, victim, game_state)
        actions.append(_attach_decision_metadata(action, victim, decision))
        saved_this_night = victim

    if decision.action == "poison" and has_poison and decision.seat > 0:
        poison_candidates = [
            p
            for p in poison_targets
            if saved_this_night is None or p.player_id != saved_this_night.player_id
        ]
        poison_target = resolve_player_by_seat(decision.seat, poison_candidates)
        if poison_target:
            action = WitchPoisonAction(role.player, poison_target, game_state)
            actions.append(_attach_decision_metadata(action, poison_target, decision))

    return actions


async def plan_guard_protect(
    role: Guard, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    if not role.player.is_alive():
        return []
    possible_targets = [
        p for p in game_state.get_alive_players() if p.player_id != role.last_protected
    ]
    if not possible_targets or not role.player.agent:
        return []
    context = ""
    if role.last_protected:
        last_player = game_state.get_player(role.last_protected)
        if last_player:
            context = f"你不能连续两晚守护 {last_player.name}（{_seat_label(last_player)}号）。"
    target = await interaction.request_seat_choice(
        role.player,
        role.player.agent,
        role_name="Guard",
        action_description=GamePrompts.GUARD_ACTION,
        possible_targets=possible_targets,
        allow_skip=False,
        additional_context=context,
        fallback_random=False,
        round_number=game_state.round_number,
        phase="Night",
        action_phase=ActionPhase.NIGHT_SKILL_TARGET,
    )
    if target:
        return [GuardProtectAction(role.player, target, game_state)]
    return []


async def plan_seer_check(
    role: Seer, game_state: GameStateProtocol, interaction: PhaseInteraction
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
    context = ""
    if checked_info:
        context = f"已查验：{', '.join(checked_info)}。尽量不要重复验同一人。"
    target = await interaction.request_seat_choice(
        role.player,
        role.player.agent,
        role_name="Seer",
        action_description=GamePrompts.PROPHET_ACTION,
        possible_targets=possible_targets,
        allow_skip=False,
        additional_context=context,
        fallback_random=False,
        round_number=game_state.round_number,
        phase="Night",
        action_phase=ActionPhase.NIGHT_SKILL_TARGET,
    )
    if target:
        return [SeerCheckAction(role.player, target, game_state)]
    return []


async def plan_cupid_link(
    role: Cupid, game_state: GameStateProtocol, interaction: PhaseInteraction
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
    role, game_state: GameStateProtocol, interaction: PhaseInteraction
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
        fallback_random=False,
        round_number=game_state.round_number,
        phase="Night",
    )
    if target:
        return [RavenMarkAction(role.player, target, game_state)]
    return []


async def plan_graveyard_check(
    role, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    if not role.player.is_alive() or not role.player.agent:
        return []
    dead_players = game_state.get_dead_players()
    if not dead_players:
        return []
    checked_info = []
    for round_num, player_id in game_state.graveyard_checked.items():
        player = game_state.get_player(player_id)
        if player:
            checked_info.append(f"第{round_num}轮：{_seat_label(player)}号 {player.name}")
    context = "可查验一名死者的真实阵营；不确定请跳过。"
    if checked_info:
        context += f"\n\n已验尸：{', '.join(checked_info)}。尽量不要重复查验同一人。"
    target = await interaction.request_seat_choice(
        role.player,
        role.player.agent,
        role_name="Graveyard Keeper",
        action_description="选择一名已死亡玩家查验身份",
        possible_targets=dead_players,
        allow_skip=True,
        additional_context=context,
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
    role: Role, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    """经 Hub 路由夜间行动；未注册的角色返回 []。"""
    planner = _resolve_night_planner(role.name)
    if planner is None:
        return []
    return await planner(role, game_state, interaction)
