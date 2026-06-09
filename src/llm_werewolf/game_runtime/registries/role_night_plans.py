"""各角色夜间行动规划（通过 PhaseInteraction / InformationHub 调用 LLM）。

新增角色只需在 NIGHT_PLAN_SPECS 注册一个 NightPlanSpec 并实现 planner 函数，
夜间调度器和优先级注册表自动生效——主流程无需修改。
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING
from dataclasses import field, dataclass
from collections.abc import Callable, Awaitable

from llm_werewolf.game_runtime.types import Camp
from llm_werewolf.game_runtime.roles.names import (
    participates_in_wolf_team,
    is_untransformed_blood_moon,
)
from llm_werewolf.game_runtime.support.seat import get_player_seat, resolve_player_by_seat
from llm_werewolf.game_runtime.roles.werewolf import build_werewolf_team_context
from llm_werewolf.game_runtime.actions.villager import (
    CupidLinkAction,
    RavenMarkAction,
    SeerCheckAction,
    ThiefChooseAction,
    WitchSaveAction,
    WitchPoisonAction,
    GuardProtectAction,
    MagicianSwapAction,
    GraveyardKeeperCheckAction,
)
from llm_werewolf.game_runtime.actions.werewolf import (
    WerewolfVoteAction,
    WhiteWolfKillAction,
    WolfBeautyCharmAction,
    NightmareWolfBlockAction,
    GuardianWolfProtectAction,
)
from llm_werewolf.strategy.registry.role_prompts import GamePrompts
from llm_werewolf.strategy.contracts.phase_outputs import ActionPhase

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import ActionProtocol, PlayerProtocol, GameStateProtocol
    from llm_werewolf.game_runtime.roles.base import Role
    from llm_werewolf.game_runtime.roles.villager import Seer, Cupid, Guard, Witch, Magician
    from llm_werewolf.game_runtime.roles.werewolf import (
        WhiteWolf,
        WolfBeauty,
        GuardianWolf,
        NightmareWolf,
        BloodMoonApostle,
    )
    from llm_werewolf.game_runtime.interaction.phase_interaction import PhaseInteraction

NightPlanner = Callable[
    ["Role", "GameStateProtocol", "PhaseInteraction"], Awaitable[list["ActionProtocol"]]
]


class NightStage(str, Enum):
    """夜间调度阶段——新增角色必须归入其中一个阶段。"""

    PRE_WOLF = "pre_wolf"
    WOLF_PHASE_SPECIAL = "wolf_phase_special"
    WITCH = "witch"
    POST_WITCH = "post_witch"


PRE_WOLF_STAGE = NightStage.PRE_WOLF.value
WOLF_PHASE_SPECIAL_STAGE = NightStage.WOLF_PHASE_SPECIAL.value
WITCH_STAGE = NightStage.WITCH.value
POST_WITCH_STAGE = NightStage.POST_WITCH.value


@dataclass(frozen=True)
class NightPlanSpec:
    """声明一个角色的夜间调度规格。

    新增角色只需填写此数据类并加入 NIGHT_PLAN_SPECS 即可接入夜间调度，
    无需修改 NightSkillScheduler 或 ActionProcessor。

    Attributes:
        role_name: 角色标识名（与 Role.name 一致）。
        planner: 异步函数，返回该角色本夜产生的 Action 列表。
        stage: 所属调度阶段；None 表示仅参与狼票（wolf_vote=True 时）。
        order: 同阶段内的执行顺序（值越小越先执行）。
        wolf_vote: 是否参与狼队刀票投票。
        action_classes: 该角色可能产出的 Action 类名列表（用于注册完整性校验）。
    """

    role_name: str
    planner: NightPlanner
    stage: str | None
    order: int = 0
    wolf_vote: bool = False
    action_classes: tuple[str, ...] = field(default_factory=tuple)


def _seat_label(player: PlayerProtocol) -> str:
    seat = get_player_seat(player)
    return str(seat) if seat is not None else player.name


def _attach_decision_metadata(
    action: ActionProtocol, target: PlayerProtocol, decision: object | None
) -> ActionProtocol:
    metadata: dict[str, object] = {
        "decision_seat": get_player_seat(target),
        "resolved_target_id": target.player_id,
        "resolved_target_name": target.name,
        "fallback": False,
    }
    actor = getattr(action, "actor", None)
    agent = getattr(actor, "agent", None)
    agent_meta = getattr(agent, "_last_decision_metadata", None)
    if isinstance(agent_meta, dict) and agent_meta.get("fallback"):
        metadata["fallback"] = True
        metadata["fallback_reason"] = agent_meta.get("fallback_reason")
        metadata["decision_kind"] = agent_meta.get("decision_kind", "skill")
    if decision is not None and hasattr(decision, "model_dump"):
        metadata["structured_decision"] = decision.model_dump(mode="json")
    action._decision_metadata = metadata
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


async def plan_magician_swap(
    role: Magician, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    if role.has_swapped or not role.player.is_alive() or not role.player.agent:
        return []
    possible_targets = game_state.get_alive_players()
    if len(possible_targets) < 2:
        return []
    selected = await interaction.request_multi_targets(
        role.player,
        role.player.agent,
        role_name="Magician",
        action_description="选择两名玩家交换身份",
        possible_targets=possible_targets,
        num_targets=2,
        additional_context="整局仅可交换一次。被交换玩家不会立刻知道自己的身份已被交换。",
        round_number=game_state.round_number,
        phase="Night",
    )
    if selected and len(selected) == 2:
        action = MagicianSwapAction(role.player, selected[0], selected[1], game_state)
        return [action]
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


async def plan_thief_choose(
    role: Role, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    """盗贼首夜选阵营。

    MVP：引擎未发额外身份牌，故以一个 yes/no 决定是否加入狼队。
    仅首夜且未选择过时触发；产出 ThiefChooseAction 由 ActionProcessor 结算。
    """
    if game_state.round_number != 1:
        return []
    if getattr(role, "has_chosen", False):
        return []
    if not role.player.is_alive() or not role.player.agent:
        return []

    join_wolves = await interaction.request_yes_no(
        role.player,
        role.player.agent,
        role_name="Thief",
        question="首夜择牌：你是否选择加入狼人阵营？（是=成为狼人；否=成为好人）",
        context="选定后本局阵营与胜利目标随之确定，整局仅可选择一次。",
        round_number=game_state.round_number,
        phase="Night",
    )
    return [ThiefChooseAction(role.player, join_wolves, game_state)]


async def plan_noop_night_action(
    role: Role, game_state: GameStateProtocol, interaction: PhaseInteraction
) -> list[ActionProtocol]:
    """用于已注册但尚未开放夜间技能的占位角色。"""
    return []


NIGHT_PLAN_SPECS: dict[str, NightPlanSpec] = {
    # ── PRE_WOLF 阶段 ──────────────────────────────────────────────
    "Cupid": NightPlanSpec(
        "Cupid", plan_cupid_link, PRE_WOLF_STAGE, order=10,
        action_classes=("CupidLinkAction",),
    ),
    "Nightmare Wolf": NightPlanSpec(
        "Nightmare Wolf", plan_nightmare_wolf, PRE_WOLF_STAGE, order=20, wolf_vote=True,
        action_classes=("NightmareWolfBlockAction",),
    ),
    "Guard": NightPlanSpec(
        "Guard", plan_guard_protect, PRE_WOLF_STAGE, order=30,
        action_classes=("GuardProtectAction",),
    ),
    "Guardian Wolf": NightPlanSpec(
        "Guardian Wolf", plan_guardian_wolf, PRE_WOLF_STAGE, order=40, wolf_vote=True,
        action_classes=("GuardianWolfProtectAction",),
    ),
    "Thief": NightPlanSpec(
        "Thief", plan_thief_choose, PRE_WOLF_STAGE, order=50,
        action_classes=("ThiefChooseAction",),
    ),
    # ── 狼票阶段（stage=None, wolf_vote=True）──────────────────────
    "Werewolf": NightPlanSpec(
        "Werewolf", plan_werewolf_vote, None, wolf_vote=True,
        action_classes=("WerewolfVoteAction",),
    ),
    "Alpha Wolf": NightPlanSpec(
        "Alpha Wolf", plan_alpha_wolf_vote, None, wolf_vote=True,
        action_classes=("WerewolfVoteAction",),
    ),
    "Hidden Wolf": NightPlanSpec(
        "Hidden Wolf", plan_hidden_wolf_vote, None, wolf_vote=True,
        action_classes=("WerewolfVoteAction",),
    ),
    "Blood Moon Apostle": NightPlanSpec(
        "Blood Moon Apostle", plan_blood_moon_apostle, None, wolf_vote=True,
        action_classes=("WerewolfVoteAction",),
    ),
    # ── WOLF_PHASE_SPECIAL 阶段（狼票后额外技能）─────────────────────
    "White Wolf": NightPlanSpec(
        "White Wolf", plan_white_wolf, WOLF_PHASE_SPECIAL_STAGE, order=10, wolf_vote=True,
        action_classes=("WhiteWolfKillAction",),
    ),
    "Wolf Beauty": NightPlanSpec(
        "Wolf Beauty", plan_wolf_beauty, WOLF_PHASE_SPECIAL_STAGE, order=20, wolf_vote=True,
        action_classes=("WolfBeautyCharmAction",),
    ),
    # ── WITCH 阶段 ──────────────────────────────────────────────────
    "Witch": NightPlanSpec(
        "Witch", plan_witch_actions, WITCH_STAGE, order=10,
        action_classes=("WitchSaveAction", "WitchPoisonAction"),
    ),
    # ── POST_WITCH 阶段 ─────────────────────────────────────────────
    "Seer": NightPlanSpec(
        "Seer", plan_seer_check, POST_WITCH_STAGE, order=10,
        action_classes=("SeerCheckAction",),
    ),
    "Graveyard Keeper": NightPlanSpec(
        "Graveyard Keeper", plan_graveyard_check, POST_WITCH_STAGE, order=20,
        action_classes=("GraveyardKeeperCheckAction",),
    ),
    "Raven": NightPlanSpec(
        "Raven", plan_raven_mark, POST_WITCH_STAGE, order=30,
        action_classes=("RavenMarkAction",),
    ),
    "Magician": NightPlanSpec(
        "Magician", plan_magician_swap, POST_WITCH_STAGE, order=40,
        action_classes=("MagicianSwapAction",),
    ),
}

NIGHT_PLANNERS: dict[str, NightPlanner] = {
    role_name: spec.planner for role_name, spec in NIGHT_PLAN_SPECS.items()
}


def night_roles_for_stage(stage: str) -> tuple[str, ...]:
    """返回某个夜间阶段内按 order 排好的角色名。"""
    return tuple(
        spec.role_name
        for spec in sorted(NIGHT_PLAN_SPECS.values(), key=lambda item: item.order)
        if spec.stage == stage
    )


def night_roles_with_wolf_vote() -> frozenset[str]:
    """返回参与狼队刀票的运行时角色名。"""
    return frozenset(spec.role_name for spec in NIGHT_PLAN_SPECS.values() if spec.wolf_vote)


def explicit_night_role_names() -> frozenset[str]:
    """返回已声明夜间计划的角色名，用于 scheduler 避免重复兜底调度。"""
    return frozenset(NIGHT_PLAN_SPECS)


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


def validate_night_plan_registry() -> list[str]:
    """校验 NIGHT_PLAN_SPECS 的注册完整性。

    检查每个声明了 action_classes 的 spec，确认对应类名在
    ACTION_PRIORITY_BY_CLASS 中已注册优先级。返回缺失注册的错误描述列表。
    空列表表示校验通过。
    """
    from llm_werewolf.game_runtime.registries.action_registry import ACTION_PRIORITY_BY_CLASS

    errors: list[str] = []
    valid_stages = {s.value for s in NightStage}
    for role_name, spec in NIGHT_PLAN_SPECS.items():
        if spec.stage is not None and spec.stage not in valid_stages:
            errors.append(f"{role_name}: stage '{spec.stage}' 不是合法的 NightStage 值")
        for cls_name in spec.action_classes:
            if cls_name not in ACTION_PRIORITY_BY_CLASS:
                errors.append(
                    f"{role_name}: action_class '{cls_name}' 未在 ACTION_PRIORITY_BY_CLASS 注册"
                )
    return errors
