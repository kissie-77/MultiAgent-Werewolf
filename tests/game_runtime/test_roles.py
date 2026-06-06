from unittest.mock import AsyncMock, MagicMock, patch

from llm_werewolf.game_runtime.roles import Camp, Seer, Guard, Witch, Magician, Villager, Werewolf
from llm_werewolf.game_runtime.actions import (
    SeerCheckAction,
    WitchSaveAction,
    WitchPoisonAction,
    GuardProtectAction,
    MagicianSwapAction,
    WerewolfVoteAction,
)
from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.state.game_state import GameState


def test_villager_role() -> None:
    """测试村民角色创建。"""
    player = Player("p1", "Alice", Villager)
    villager = player.role
    assert villager.name == "Villager"
    assert villager.camp == Camp.VILLAGER
    assert not villager.config.can_act_night
    assert not villager.config.can_act_day


def test_werewolf_role() -> None:
    """测试狼人角色创建。"""
    player = Player("p1", "Alice", Werewolf)
    werewolf = player.role
    assert werewolf.name == "Werewolf"
    assert werewolf.camp == Camp.WEREWOLF
    assert werewolf.config.can_act_night
    assert werewolf.config.priority is not None


def test_seer_role() -> None:
    """测试预言家角色创建。"""
    player = Player("p1", "Alice", Seer)
    seer = player.role
    assert seer.name == "Seer"
    assert seer.camp == Camp.VILLAGER
    assert seer.config.can_act_night


def test_witch_role() -> None:
    """测试带药水的女巫角色。"""
    player = Player("p1", "Alice", Witch)
    witch: Witch = player.role
    assert witch.name == "Witch"
    assert witch.camp == Camp.VILLAGER
    assert witch.has_save_potion
    assert witch.has_poison_potion


def test_role_string_representation() -> None:
    """测试角色字符串表示。"""
    player = Player("p1", "Alice", Villager)
    villager = player.role
    assert str(villager) == "Villager"
    assert "Villager" in repr(villager)


def test_magician_swap_action_swaps_roles_once() -> None:
    """魔术师应能交换两名玩家身份，且整局只可使用一次。"""
    magician = Player("m1", "Magician", Magician)
    seer = Player("s1", "Seer", Seer)
    villager = Player("v1", "Villager", Villager)
    state = GameState([magician, seer, villager])

    action = MagicianSwapAction(magician, seer, villager, state)

    assert action.validate() is True
    assert action.execute() == ["Magician swaps roles of Seer and Villager"]
    assert magician.role.has_swapped is True
    assert seer.get_role_name() == "Villager"
    assert villager.get_role_name() == "Seer"
    assert seer.role.player is seer
    assert villager.role.player is villager
    assert action.validate() is False


async def test_werewolf_get_night_actions() -> None:
    """测试 Werewolf get_night_actions 方法。"""
    werewolf_player = Player(
        "p1", "Werewolf", Werewolf, agent=DemoAgent(name="Werewolf", model="demo")
    )
    villager_player = Player(
        "p2", "Villager", Villager, agent=DemoAgent(name="Villager", model="demo")
    )
    players = [werewolf_player, villager_player]
    game_state = GameState(players)
    game_state.phase_interaction = MagicMock()
    with patch(
        "llm_werewolf.game_runtime.registries.role_night_plans.dispatch_night_plan",
        new_callable=AsyncMock,
        return_value=[WerewolfVoteAction(werewolf_player, villager_player, game_state)],
    ) as plan_mock:
        actions = await werewolf_player.role.get_night_actions(game_state)
        plan_mock.assert_awaited_once()
    assert len(actions) == 1
    assert isinstance(actions[0], WerewolfVoteAction)
    assert actions[0].target == villager_player


async def test_seer_get_night_actions() -> None:
    """测试 Seer get_night_actions 方法。"""
    seer_player = Player("p1", "Seer", Seer, agent=DemoAgent(name="Seer", model="demo"))
    villager_player = Player(
        "p2", "Villager", Villager, agent=DemoAgent(name="Villager", model="demo")
    )
    players = [seer_player, villager_player]
    game_state = GameState(players)
    game_state.phase_interaction = MagicMock()
    with patch(
        "llm_werewolf.game_runtime.registries.role_night_plans.dispatch_night_plan",
        new_callable=AsyncMock,
        return_value=[SeerCheckAction(seer_player, villager_player, game_state)],
    ):
        actions = await seer_player.role.get_night_actions(game_state)
    assert len(actions) == 1
    assert isinstance(actions[0], SeerCheckAction)
    assert actions[0].target == villager_player


async def test_witch_get_night_actions_save() -> None:
    """测试女巫 get_night_actions 方法的救人分支。"""
    witch_player = Player("p1", "Witch", Witch, agent=DemoAgent(name="Witch", model="demo"))
    villager_player = Player(
        "p2", "Villager", Villager, agent=DemoAgent(name="Villager", model="demo")
    )
    players = [witch_player, villager_player]
    game_state = GameState(players)
    game_state.werewolf_target = "p2"
    game_state.phase_interaction = MagicMock()

    with patch(
        "llm_werewolf.game_runtime.registries.role_night_plans.dispatch_night_plan",
        new_callable=AsyncMock,
        return_value=[WitchSaveAction(witch_player, villager_player, game_state)],
    ):
        actions = await witch_player.role.get_night_actions(game_state)
    assert len(actions) == 1
    assert isinstance(actions[0], WitchSaveAction)
    assert actions[0].target == villager_player


async def test_witch_get_night_actions_poison() -> None:
    """测试女巫 get_night_actions 方法的毒杀分支。"""
    witch_player = Player("p1", "Witch", Witch)
    villager_player = Player("p2", "Villager", Villager)
    players = [witch_player, villager_player]
    game_state = GameState(players)
    witch_player.role.has_save_potion = False
    game_state.phase_interaction = MagicMock()

    with (
        patch("random.choice", return_value=villager_player),
        patch(
            "llm_werewolf.game_runtime.registries.role_night_plans.dispatch_night_plan",
            new_callable=AsyncMock,
            return_value=[WitchPoisonAction(witch_player, villager_player, game_state)],
        ),
    ):
        actions = await witch_player.role.get_night_actions(game_state)
        if actions:
            assert len(actions) == 1
            assert isinstance(actions[0], WitchPoisonAction)
            assert actions[0].target == villager_player


async def test_guard_get_night_actions() -> None:
    """测试 Guard get_night_actions 方法。"""
    guard_player = Player("p1", "Guard", Guard, agent=DemoAgent(name="Guard", model="demo"))
    villager_player = Player(
        "p2", "Villager", Villager, agent=DemoAgent(name="Villager", model="demo")
    )
    players = [guard_player, villager_player]
    game_state = GameState(players)
    game_state.phase_interaction = MagicMock()
    with patch(
        "llm_werewolf.game_runtime.registries.role_night_plans.dispatch_night_plan",
        new_callable=AsyncMock,
        return_value=[GuardProtectAction(guard_player, villager_player, game_state)],
    ):
        actions = await guard_player.role.get_night_actions(game_state)
    assert len(actions) == 1
    assert isinstance(actions[0], GuardProtectAction)
    assert actions[0].target == villager_player
