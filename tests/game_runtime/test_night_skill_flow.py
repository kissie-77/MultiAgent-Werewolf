"""夜间技能调度集成测试——验证各角色行动产出与注册完整性。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_werewolf.game_runtime.roles import (
    Guard,
    Seer,
    Villager,
    Werewolf,
    Witch,
)
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.registries.role_night_plans import (
    NIGHT_PLAN_SPECS,
    NightStage,
    plan_guard_protect,
    plan_seer_check,
    plan_witch_actions,
    plan_werewolf_vote,
    validate_night_plan_registry,
)
from llm_werewolf.game_runtime.actions.villager import (
    GuardProtectAction,
    SeerCheckAction,
    WitchPoisonAction,
    WitchSaveAction,
)
from llm_werewolf.game_runtime.actions.werewolf import WerewolfVoteAction


# ─── 注册完整性 ─────────────────────────────────────────────────────


def test_night_plan_registry_is_consistent() -> None:
    """所有 action_classes 都在 ACTION_PRIORITY_BY_CLASS 中注册。"""
    errors = validate_night_plan_registry()
    assert errors == [], f"注册完整性校验失败:\n" + "\n".join(errors)


def test_all_specs_use_valid_stage_enum_values() -> None:
    valid_stages = {s.value for s in NightStage} | {None}
    for name, spec in NIGHT_PLAN_SPECS.items():
        assert spec.stage in valid_stages, f"{name} 使用了非法 stage: {spec.stage}"


def test_night_stage_enum_matches_constants() -> None:
    from llm_werewolf.game_runtime.registries.role_night_plans import (
        PRE_WOLF_STAGE,
        WOLF_PHASE_SPECIAL_STAGE,
        WITCH_STAGE,
        POST_WITCH_STAGE,
    )

    assert PRE_WOLF_STAGE == NightStage.PRE_WOLF.value
    assert WOLF_PHASE_SPECIAL_STAGE == NightStage.WOLF_PHASE_SPECIAL.value
    assert WITCH_STAGE == NightStage.WITCH.value
    assert POST_WITCH_STAGE == NightStage.POST_WITCH.value


# ─── 守卫技能流程 ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_guard_protect_produces_action() -> None:
    """守卫选择目标后产出 GuardProtectAction。"""
    guard_player = Player("g1", "Guard", Guard, agent=MagicMock())
    wolf = Player("w1", "Wolf", Werewolf)
    villager = Player("v1", "Villager", Villager)
    game_state = GameState([guard_player, wolf, villager])
    game_state.round_number = 1

    interaction = MagicMock()
    interaction.request_seat_choice = AsyncMock(return_value=villager)

    actions = await plan_guard_protect(guard_player.role, game_state, interaction)

    assert len(actions) == 1
    assert isinstance(actions[0], GuardProtectAction)
    assert actions[0].target == villager


@pytest.mark.asyncio
async def test_guard_cannot_protect_same_target_twice() -> None:
    """守卫不能连续两夜守同一人——候选列表排除 last_protected。"""
    guard_player = Player("g1", "Guard", Guard, agent=MagicMock())
    wolf = Player("w1", "Wolf", Werewolf)
    villager = Player("v1", "Villager", Villager)
    game_state = GameState([guard_player, wolf, villager])
    game_state.round_number = 2
    guard_player.role.last_protected = villager.player_id

    interaction = MagicMock()
    interaction.request_seat_choice = AsyncMock(return_value=wolf)

    actions = await plan_guard_protect(guard_player.role, game_state, interaction)

    call_kwargs = interaction.request_seat_choice.call_args.kwargs
    targets = call_kwargs.get("possible_targets") or interaction.request_seat_choice.call_args[0][4]
    target_ids = [p.player_id for p in targets]
    assert villager.player_id not in target_ids


# ─── 预言家技能流程 ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_seer_check_produces_action() -> None:
    """预言家选择目标后产出 SeerCheckAction。"""
    seer_player = Player("s1", "Seer", Seer, agent=MagicMock())
    wolf = Player("w1", "Wolf", Werewolf)
    villager = Player("v1", "Villager", Villager)
    game_state = GameState([seer_player, wolf, villager])
    game_state.round_number = 1

    interaction = MagicMock()
    interaction.request_seat_choice = AsyncMock(return_value=wolf)

    actions = await plan_seer_check(seer_player.role, game_state, interaction)

    assert len(actions) == 1
    assert isinstance(actions[0], SeerCheckAction)
    assert actions[0].target == wolf


@pytest.mark.asyncio
async def test_seer_dead_produces_no_action() -> None:
    """死亡预言家不产出行动。"""
    seer_player = Player("s1", "Seer", Seer, agent=MagicMock())
    wolf = Player("w1", "Wolf", Werewolf)
    game_state = GameState([seer_player, wolf])
    seer_player.kill()

    interaction = MagicMock()
    actions = await plan_seer_check(seer_player.role, game_state, interaction)

    assert actions == []


# ─── 女巫技能流程 ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_witch_save_produces_action() -> None:
    """女巫在有刀口且有解药时选择救人产出 WitchSaveAction。"""
    witch_player = Player("witch1", "Witch", Witch, agent=MagicMock())
    wolf = Player("w1", "Wolf", Werewolf)
    villager = Player("v1", "Villager", Villager)
    game_state = GameState([witch_player, wolf, villager])
    game_state.round_number = 1
    game_state.werewolf_target = villager.player_id

    decision = MagicMock()
    decision.action = "save"
    decision.seat = 0

    interaction = MagicMock()
    interaction.request_witch_night_choice = AsyncMock(return_value=decision)

    actions = await plan_witch_actions(witch_player.role, game_state, interaction)

    assert len(actions) == 1
    assert isinstance(actions[0], WitchSaveAction)
    assert actions[0].target == villager


@pytest.mark.asyncio
async def test_witch_poison_produces_action() -> None:
    """女巫有毒药时选择毒杀产出 WitchPoisonAction。"""
    witch_player = Player("witch1", "Witch", Witch, agent=MagicMock())
    wolf = Player("w1", "Wolf", Werewolf)
    villager = Player("v1", "Villager", Villager)
    game_state = GameState([witch_player, wolf, villager])
    game_state.round_number = 1
    game_state.werewolf_target = None

    from llm_werewolf.game_runtime.support.seat import get_player_seat

    decision = MagicMock()
    decision.action = "poison"
    decision.seat = get_player_seat(wolf) or 2

    interaction = MagicMock()
    interaction.request_witch_night_choice = AsyncMock(return_value=decision)

    actions = await plan_witch_actions(witch_player.role, game_state, interaction)

    assert len(actions) == 1
    assert isinstance(actions[0], WitchPoisonAction)


@pytest.mark.asyncio
async def test_witch_no_potions_produces_no_action() -> None:
    """女巫药瓶均空时不产出行动。"""
    witch_player = Player("witch1", "Witch", Witch, agent=MagicMock())
    wolf = Player("w1", "Wolf", Werewolf)
    game_state = GameState([witch_player, wolf])
    game_state.round_number = 2
    witch_player.role.has_save_potion = False
    witch_player.role.has_poison_potion = False

    interaction = MagicMock()
    actions = await plan_witch_actions(witch_player.role, game_state, interaction)

    assert actions == []


# ─── 狼人刀票流程 ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_werewolf_vote_produces_action() -> None:
    """狼人选择目标后产出 WerewolfVoteAction。"""
    wolf_player = Player("w1", "Wolf", Werewolf, agent=MagicMock())
    villager = Player("v1", "Villager", Villager)
    game_state = GameState([wolf_player, villager])
    game_state.round_number = 1

    interaction = MagicMock()
    interaction.request_seat_choice = AsyncMock(return_value=villager)

    actions = await plan_werewolf_vote(wolf_player.role, game_state, interaction)

    assert len(actions) == 1
    assert isinstance(actions[0], WerewolfVoteAction)
    assert actions[0].target == villager


@pytest.mark.asyncio
async def test_werewolf_dead_produces_no_action() -> None:
    """死亡狼人不产出刀票。"""
    wolf_player = Player("w1", "Wolf", Werewolf, agent=MagicMock())
    villager = Player("v1", "Villager", Villager)
    game_state = GameState([wolf_player, villager])
    wolf_player.kill()

    interaction = MagicMock()
    actions = await plan_werewolf_vote(wolf_player.role, game_state, interaction)

    assert actions == []


@pytest.mark.asyncio
async def test_werewolf_cannot_target_wolf_team() -> None:
    """狼人刀票候选列表不包含狼队成员。"""
    wolf1 = Player("w1", "Wolf1", Werewolf, agent=MagicMock())
    wolf2 = Player("w2", "Wolf2", Werewolf)
    villager = Player("v1", "Villager", Villager)
    game_state = GameState([wolf1, wolf2, villager])
    game_state.round_number = 1

    interaction = MagicMock()
    interaction.request_seat_choice = AsyncMock(return_value=villager)

    await plan_werewolf_vote(wolf1.role, game_state, interaction)

    call_kwargs = interaction.request_seat_choice.call_args.kwargs
    targets = call_kwargs.get("possible_targets")
    target_ids = [p.player_id for p in targets]
    assert wolf1.player_id not in target_ids
    assert wolf2.player_id not in target_ids
    assert villager.player_id in target_ids
