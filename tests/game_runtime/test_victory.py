"""game_runtime/victory.py 模块的测试。"""

from llm_werewolf.game_runtime.roles import Seer, Witch, Villager, Werewolf
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.victory import VictoryChecker
from llm_werewolf.game_runtime.state.game_state import GameState


class TestVictoryChecker:
    """VictoryChecker 类的测试。"""

    def create_mock_player(
        self, player_id: str, name: str, role_class: type, is_alive: bool = True
    ) -> Player:
        """创建用于测试的模拟玩家。"""
        player = Player(player_id=player_id, name=name, role=role_class)
        if not is_alive:
            player.kill()
        return player

    def test_werewolf_victory_equal_numbers(self) -> None:
        """测试狼人数量等于村民时获胜。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf),
            self.create_mock_player("w2", "Wolf2", Werewolf),
            self.create_mock_player("v1", "Villager1", Villager),
            self.create_mock_player("v2", "Villager2", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_werewolf_victory()

        assert result.has_winner is True
        assert result.winner_camp == "werewolf"
        assert len(result.winner_ids) == 2
        assert "w1" in result.winner_ids
        assert "w2" in result.winner_ids
        assert "equal or outnumber villagers" in result.reason

    def test_werewolf_victory_outnumber(self) -> None:
        """测试狼人数量超过村民时获胜。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf),
            self.create_mock_player("w2", "Wolf2", Werewolf),
            self.create_mock_player("v1", "Villager1", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_werewolf_victory()

        assert result.has_winner is True
        assert result.winner_camp == "werewolf"
        assert len(result.winner_ids) == 2

    def test_werewolf_not_won_yet(self) -> None:
        """测试狼人尚未获胜。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf),
            self.create_mock_player("v1", "Villager1", Villager),
            self.create_mock_player("v2", "Villager2", Villager),
            self.create_mock_player("v3", "Villager3", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_werewolf_victory()

        assert result.has_winner is False
        assert "have not won" in result.reason

    def test_werewolf_all_dead(self) -> None:
        """测试狼人全部死亡时无法获胜。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf, is_alive=False),
            self.create_mock_player("w2", "Wolf2", Werewolf, is_alive=False),
            self.create_mock_player("v1", "Villager1", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_werewolf_victory()

        assert result.has_winner is False

    def test_villager_victory_all_werewolves_dead(self) -> None:
        """测试所有狼人死亡时村民获胜。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf, is_alive=False),
            self.create_mock_player("w2", "Wolf2", Werewolf, is_alive=False),
            self.create_mock_player("v1", "Villager1", Villager),
            self.create_mock_player("v2", "Villager2", Seer),
            self.create_mock_player("v3", "Villager3", Witch),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_villager_victory()

        assert result.has_winner is True
        assert result.winner_camp == "villager"
        assert len(result.winner_ids) == 3
        assert "v1" in result.winner_ids
        assert "v2" in result.winner_ids
        assert "v3" in result.winner_ids
        assert "eliminated" in result.reason

    def test_villager_not_won_yet(self) -> None:
        """测试村民尚未获胜。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf),
            self.create_mock_player("v1", "Villager1", Villager),
            self.create_mock_player("v2", "Villager2", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_villager_victory()

        assert result.has_winner is False
        assert "have not won" in result.reason

    def test_lover_victory(self) -> None:
        """测试仅同阵营情侣存活时情侣获胜。"""
        players = [
            self.create_mock_player("p1", "Player1", Villager),
            self.create_mock_player("p2", "Player2", Villager),
            self.create_mock_player("p3", "Player3", Villager, is_alive=False),
            self.create_mock_player("p4", "Player4", Werewolf, is_alive=False),
        ]
        players[0].set_lover("p2")
        players[1].set_lover("p1")

        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_lover_victory()

        assert result.has_winner is True
        assert result.winner_camp == "lover"
        assert len(result.winner_ids) == 2

    def test_white_lover_wolf_victory(self) -> None:
        """测试狼+好人情侣仅剩两人时白狼情侣胜。"""
        players = [
            self.create_mock_player("p1", "Player1", Villager),
            self.create_mock_player("p2", "Player2", Werewolf),
            self.create_mock_player("p3", "Player3", Villager, is_alive=False),
        ]
        players[0].set_lover("p2")
        players[1].set_lover("p1")

        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_special_victory()

        assert result.has_winner is True
        assert result.winner_camp == "white_lover_wolf"
        assert checker.check_lover_victory().has_winner is False

    def test_lover_not_won_more_alive(self) -> None:
        """测试存活超过 2 人时情侣未获胜。"""
        players = [
            self.create_mock_player("p1", "Player1", Villager),
            self.create_mock_player("p2", "Player2", Werewolf),
            self.create_mock_player("p3", "Player3", Villager),
        ]
        # 设置情侣
        players[0].set_lover("p2")
        players[1].set_lover("p1")

        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_lover_victory()

        assert result.has_winner is False

    def test_lover_not_won_one_dead(self) -> None:
        """测试一方情侣死亡时情侣未获胜。"""
        players = [
            self.create_mock_player("p1", "Player1", Villager),
            self.create_mock_player("p2", "Player2", Werewolf, is_alive=False),
            self.create_mock_player("p3", "Player3", Villager),
        ]
        # 设置情侣
        players[0].set_lover("p2")
        players[1].set_lover("p1")

        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_lover_victory()

        assert result.has_winner is False

    def test_check_victory_priority_lover_first(self) -> None:
        """测试同阵营情侣优先于阵营胜负。"""
        players = [
            self.create_mock_player("p1", "Player1", Villager),
            self.create_mock_player("p2", "Player2", Villager),
            self.create_mock_player("p3", "Player3", Villager, is_alive=False),
        ]
        players[0].set_lover("p2")
        players[1].set_lover("p1")

        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_victory()

        assert result.has_winner is True
        assert result.winner_camp == "lover"

    def test_check_victory_white_lover_priority(self) -> None:
        """测试白狼情侣走 special 路径。"""
        players = [
            self.create_mock_player("p1", "Player1", Villager),
            self.create_mock_player("p2", "Player2", Werewolf),
            self.create_mock_player("p3", "Player3", Villager, is_alive=False),
        ]
        players[0].set_lover("p2")
        players[1].set_lover("p1")

        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_victory()

        assert result.has_winner is True
        assert result.winner_camp == "white_lover_wolf"

    def test_check_victory_werewolf_wins(self) -> None:
        """测试 check_victory 返回狼人胜利。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf),
            self.create_mock_player("w2", "Wolf2", Werewolf),
            self.create_mock_player("v1", "Villager1", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_victory()

        assert result.has_winner is True
        assert result.winner_camp == "werewolf"

    def test_check_victory_villager_wins(self) -> None:
        """测试 check_victory 返回村民胜利。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf, is_alive=False),
            self.create_mock_player("v1", "Villager1", Villager),
            self.create_mock_player("v2", "Villager2", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_victory()

        assert result.has_winner is True
        assert result.winner_camp == "villager"

    def test_check_victory_no_winner(self) -> None:
        """测试游戏继续时 check_victory 无胜者。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf),
            self.create_mock_player("v1", "Villager1", Villager),
            self.create_mock_player("v2", "Villager2", Villager),
            self.create_mock_player("v3", "Villager3", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_victory()

        assert result.has_winner is False
        assert "continues" in result.reason

    def test_check_special_victory(self) -> None:
        """测试 check_special_victory 始终无胜者。"""
        players = [self.create_mock_player("p1", "Player1", Villager)]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.check_special_victory()

        assert result.has_winner is False
        assert "special" in result.reason.lower()

    def test_get_winner(self) -> None:
        """测试 get_winner 委托给 check_victory。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf, is_alive=False),
            self.create_mock_player("v1", "Villager1", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        result = checker.get_winner()

        assert result.has_winner is True
        assert result.winner_camp == "villager"

    def test_is_game_over_true(self) -> None:
        """测试有胜者时 is_game_over 返回 True。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf, is_alive=False),
            self.create_mock_player("v1", "Villager1", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        assert checker.is_game_over() is True

    def test_is_game_over_false(self) -> None:
        """测试游戏继续时 is_game_over 返回 False。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf),
            self.create_mock_player("v1", "Villager1", Villager),
            self.create_mock_player("v2", "Villager2", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        assert checker.is_game_over() is False

    def test_get_winning_players(self) -> None:
        """测试 get_winning_players 返回正确玩家。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf, is_alive=False),
            self.create_mock_player("v1", "Villager1", Villager),
            self.create_mock_player("v2", "Villager2", Seer),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        winning_players = checker.get_winning_players()

        assert len(winning_players) == 2
        assert winning_players[0].player_id in ["v1", "v2"]
        assert winning_players[1].player_id in ["v1", "v2"]

    def test_get_winning_players_no_winner(self) -> None:
        """测试无胜者时 get_winning_players 返回空列表。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf),
            self.create_mock_player("v1", "Villager1", Villager),
            self.create_mock_player("v2", "Villager2", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        winning_players = checker.get_winning_players()

        assert len(winning_players) == 0

    def test_get_losing_players(self) -> None:
        """测试 get_losing_players 返回正确玩家。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf, is_alive=False),
            self.create_mock_player("v1", "Villager1", Villager),
            self.create_mock_player("v2", "Villager2", Seer),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        losing_players = checker.get_losing_players()

        assert len(losing_players) == 1
        assert losing_players[0].player_id == "w1"

    def test_get_losing_players_no_winner(self) -> None:
        """测试无胜者时 get_losing_players 返回空列表。"""
        players = [
            self.create_mock_player("w1", "Wolf1", Werewolf),
            self.create_mock_player("v1", "Villager1", Villager),
            self.create_mock_player("v2", "Villager2", Villager),
        ]
        game_state = GameState(players=players)
        checker = VictoryChecker(game_state)

        losing_players = checker.get_losing_players()

        assert len(losing_players) == 0
