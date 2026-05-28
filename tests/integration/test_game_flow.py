from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.game_runtime.config import create_game_config_from_player_count
from llm_werewolf.game_runtime.roles.registry import create_roles
from llm_werewolf.game_runtime.types import Camp


def test_game_initialization() -> None:
    """测试初始化游戏。"""
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config)

    # 创建玩家
    players = []
    for i in range(config.num_players):
        players.append(DemoAgent(name=f"Player{i}", model="demo"))

    # 获取角色
    roles = create_roles(role_names=config.role_names)

    # 设置游戏
    engine.setup_game(players=players, roles=roles)

    assert engine.game_state is not None
    assert len(engine.game_state.players) == 6


def test_game_state_initialization() -> None:
    """测试初始化后的游戏状态。"""
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config)

    players = [DemoAgent(name=f"Player{i}", model="demo") for i in range(config.num_players)]
    roles = create_roles(role_names=config.role_names)

    engine.setup_game(players=players, roles=roles)

    assert engine.game_state.phase.value == "setup"
    assert engine.game_state.round_number == 0
    assert len(engine.game_state.get_alive_players()) == 6


def test_role_assignment() -> None:
    """测试角色是否正确分配。"""
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config)

    players = [DemoAgent(name=f"Player{i}", model="demo") for i in range(config.num_players)]
    roles = create_roles(role_names=config.role_names)

    engine.setup_game(players=players, roles=roles)

    role_assignments = engine.assign_roles()
    assert len(role_assignments) == 6

    # 检查每个玩家都有角色
    for player_id, role_name in role_assignments.items():
        player = engine.game_state.get_player(player_id)
        assert player is not None
        assert player.get_role_name() == role_name


def test_victory_checker() -> None:
    """测试胜利条件检查。"""
    config = create_game_config_from_player_count(6)
    engine = GameEngine(config)

    players = [DemoAgent(name=f"Player{i}", model="demo") for i in range(config.num_players)]
    roles = create_roles(role_names=config.role_names)

    engine.setup_game(players=players, roles=roles)

    # 初始无胜者
    assert not engine.check_victory()

    # 杀死所有狼人（村民应获胜）
    for player in engine.game_state.players:
        if player.get_camp() == Camp.WEREWOLF:
            player.kill()

    # 此时村民应获胜
    assert engine.check_victory()
    assert engine.game_state.winner == "villager"
