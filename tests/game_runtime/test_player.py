from llm_werewolf.game_runtime.roles import Villager, Werewolf
from llm_werewolf.game_runtime.state.player import Player, PlayerStatus


def test_player_creation() -> None:
    """测试创建玩家。"""
    player = Player("p1", "Alice", Villager)

    assert player.player_id == "p1"
    assert player.name == "Alice"
    assert player.is_alive()
    assert player.can_vote()


def test_player_death() -> None:
    """测试玩家死亡。"""
    player = Player("p1", "Alice", Villager)

    player.kill()
    assert not player.is_alive()
    assert player.has_status(PlayerStatus.DEAD)


def test_player_revive() -> None:
    """测试玩家复活。"""
    player = Player("p1", "Alice", Villager)

    player.kill()
    assert not player.is_alive()

    player.revive()
    assert player.is_alive()
    assert player.has_status(PlayerStatus.ALIVE)


def test_player_status() -> None:
    """测试玩家状态管理。"""
    player = Player("p1", "Alice", Villager)

    player.add_status(PlayerStatus.PROTECTED)
    assert player.has_status(PlayerStatus.PROTECTED)

    player.remove_status(PlayerStatus.PROTECTED)
    assert not player.has_status(PlayerStatus.PROTECTED)


def test_player_voting_rights() -> None:
    """测试玩家投票权。"""
    player = Player("p1", "Alice", Villager)

    assert player.can_vote()

    player.disable_voting()
    assert not player.can_vote()
    assert player.has_status(PlayerStatus.NO_VOTE)


def test_player_lover_status() -> None:
    """测试玩家情侣状态。"""
    player = Player("p1", "Alice", Villager)

    assert not player.is_lover()

    player.set_lover("p2")
    assert player.is_lover()
    assert player.lover_partner_id == "p2"


def test_player_private_notes() -> None:
    """测试获取玩家私有笔记。"""
    player = Player("p1", "Alice", Villager)

    notes = player.get_private_notes()
    assert any("你的身份是 Villager" in note for note in notes)


def test_player_public_info() -> None:
    """测试获取玩家公开信息。"""
    player = Player("p1", "Bob", Werewolf, ai_model="gpt-4")

    info = player.get_public_info()
    assert info.player_id == "p1"
    assert info.name == "Bob"
    assert info.is_alive
    assert info.ai_model == "gpt-4"
