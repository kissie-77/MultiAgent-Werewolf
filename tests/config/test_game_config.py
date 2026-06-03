import pytest
from pydantic import ValidationError

from llm_werewolf.game_runtime.config import GameConfig, create_game_config_from_player_count
from llm_werewolf.game_runtime.roles.registry import create_roles


def test_valid_game_config() -> None:
    """测试创建有效游戏配置。"""
    config = GameConfig(
        num_players=9,
        role_names=[
            "Werewolf",
            "Werewolf",
            "Seer",
            "Witch",
            "Hunter",
            "Guard",
            "Villager",
            "Villager",
            "Villager",
        ],
    )

    assert config.num_players == 9
    assert len(config.role_names) == 9


def test_invalid_player_count() -> None:
    """测试无效玩家数量。"""
    with pytest.raises(ValidationError):
        GameConfig(
            num_players=3,  # 人数过少
            role_names=["Werewolf", "Villager", "Villager"],
        )


def test_role_count_mismatch() -> None:
    """测试角色数量与玩家数量不匹配。"""
    with pytest.raises(ValidationError):
        GameConfig(
            num_players=9,
            role_names=["Werewolf", "Villager"],  # 仅 2 个角色
        )


def test_no_werewolf() -> None:
    """测试无狼人的配置。"""
    with pytest.raises(ValidationError):
        GameConfig(
            num_players=6,
            role_names=["Villager"] * 6,  # 无狼人
        )


def test_config_to_role_list() -> None:
    """测试将配置转换为角色实例。"""
    config = create_game_config_from_player_count(6)
    roles = create_roles(config.role_names)

    assert len(roles) == 6
    assert all(hasattr(role, "name") for role in roles)


def test_create_game_config_from_player_count() -> None:
    """测试按玩家数量自动生成游戏配置。"""
    config = create_game_config_from_player_count(9)
    assert config.num_players == 9
    assert len(config.role_names) == 9
    # 9 人局应有 2-3 个狼人
    werewolf_count = sum(1 for role in config.role_names if "Wolf" in role or role == "Werewolf")
    assert 2 <= werewolf_count <= 3


def test_invalid_player_count_config() -> None:
    """测试无效玩家数量的自动配置。"""
    with pytest.raises(ValueError, match="Maximum 20 players supported"):
        create_game_config_from_player_count(100)

    with pytest.raises(ValueError, match="Minimum 6 players required"):
        create_game_config_from_player_count(3)


def test_config_scaling() -> None:
    """测试角色组成随玩家数量扩展。"""
    config_6 = create_game_config_from_player_count(6)
    config_12 = create_game_config_from_player_count(12)

    # 玩家越多狼人应越多
    werewolves_6 = sum(1 for role in config_6.role_names if "Wolf" in role or role == "Werewolf")
    werewolves_12 = sum(1 for role in config_12.role_names if "Wolf" in role or role == "Werewolf")
    assert werewolves_12 >= werewolves_6


def test_6_players_config() -> None:
    """测试 6 人配置（最少人数）。"""
    config = create_game_config_from_player_count(6)
    assert config.num_players == 6
    assert len(config.role_names) == 6
    # 6 人局：2 狼、预言家、女巫、2 村民
    werewolves = sum(1 for role in config.role_names if "Wolf" in role or role == "Werewolf")
    assert werewolves == 2
    assert "Seer" in config.role_names
    assert "Witch" in config.role_names
    assert "Guard" not in config.role_names  # 7 人及以上有守卫
    # 检查超时设置
    assert config.night_timeout == 45
    assert config.day_timeout == 180
    assert config.vote_timeout == 45


def test_7_players_config() -> None:
    """测试 7 人配置（守卫阈值）。"""
    config = create_game_config_from_player_count(7)
    assert config.num_players == 7
    assert len(config.role_names) == 7
    # 此时应有守卫
    assert "Guard" in config.role_names
    assert "Hunter" not in config.role_names  # 9 人及以上有猎人


def test_8_players_config() -> None:
    """测试 8 人配置。"""
    config = create_game_config_from_player_count(8)
    assert config.num_players == 8
    assert len(config.role_names) == 8
    # 仍为 2 个狼人
    werewolves = sum(1 for role in config.role_names if "Wolf" in role or role == "Werewolf")
    assert werewolves == 2
    # 超时仍应使用小型局设置
    assert config.night_timeout == 45
    assert config.day_timeout == 180


def test_9_players_config() -> None:
    """测试 9 人配置（AlphaWolf 阈值）。"""
    config = create_game_config_from_player_count(9)
    assert config.num_players == 9
    assert len(config.role_names) == 9
    # 此时应有 3 个狼人（2 + AlphaWolf）
    werewolves = sum(1 for role in config.role_names if "Wolf" in role or role == "Werewolf")
    assert werewolves == 3
    assert "AlphaWolf" in config.role_names
    assert "Hunter" in config.role_names
    # 超时应切换为中型局设置
    assert config.night_timeout == 60
    assert config.day_timeout == 300


def test_11_players_config() -> None:
    """测试 11 人配置（丘比特阈值）。"""
    config = create_game_config_from_player_count(11)
    assert config.num_players == 11
    assert len(config.role_names) == 11
    # 此时应有丘比特
    assert "Cupid" in config.role_names
    # 仍为 3 个狼人
    werewolves = sum(1 for role in config.role_names if "Wolf" in role or role == "Werewolf")
    assert werewolves == 3


def test_12_players_config() -> None:
    """测试 12 人配置（白狼阈值）。"""
    config = create_game_config_from_player_count(12)
    assert config.num_players == 12
    assert len(config.role_names) == 12
    # 此时应有 4 个狼人（2 + AlphaWolf + WhiteWolf）
    werewolves = sum(1 for role in config.role_names if "Wolf" in role or role == "Werewolf")
    assert werewolves == 4
    assert "WhiteWolf" in config.role_names
    # 仍为中型局超时
    assert config.night_timeout == 60
    assert config.day_timeout == 300


def test_13_players_config() -> None:
    """测试 13 人配置（白痴阈值）。"""
    config = create_game_config_from_player_count(13)
    assert config.num_players == 13
    assert len(config.role_names) == 13
    # 此时应有白痴
    assert "Idiot" in config.role_names
    # 超时应切换为大型局设置
    assert config.night_timeout == 90
    assert config.day_timeout == 400


def test_15_players_config() -> None:
    """测试 15 人配置（狼美人及长老阈值）。"""
    config = create_game_config_from_player_count(15)
    assert config.num_players == 15
    assert len(config.role_names) == 15
    # 此时应有 5 个狼人（2 + AlphaWolf + WhiteWolf + WolfBeauty）
    werewolves = sum(1 for role in config.role_names if "Wolf" in role or role == "Werewolf")
    assert werewolves == 5
    assert "WolfBeauty" in config.role_names
    assert "Elder" in config.role_names


def test_17_players_config() -> None:
    """测试 17 人配置（骑士阈值）。"""
    config = create_game_config_from_player_count(17)
    assert config.num_players == 17
    assert len(config.role_names) == 17
    # 此时应有骑士
    assert "Knight" in config.role_names


def test_19_players_config() -> None:
    """测试 19 人配置（乌鸦阈值）。"""
    config = create_game_config_from_player_count(19)
    assert config.num_players == 19
    assert len(config.role_names) == 19
    # 此时应有乌鸦
    assert "Raven" in config.role_names


def test_20_players_config() -> None:
    """测试 20 人配置（上限）。"""
    config = create_game_config_from_player_count(20)
    assert config.num_players == 20
    assert len(config.role_names) == 20
    # 应包含所有角色
    assert "Raven" in config.role_names
    # 大型局超时
    assert config.night_timeout == 90
    assert config.day_timeout == 400
    assert config.vote_timeout == 90


def test_villager_count() -> None:
    """测试村民正确填充剩余席位。"""
    for num_players in range(6, 21):
        config = create_game_config_from_player_count(num_players)
        villager_count = sum(1 for role in config.role_names if role == "Villager")
        special_roles = sum(1 for role in config.role_names if role != "Villager")
        assert villager_count + special_roles == num_players
        assert villager_count >= 0


def test_vote_intention_concurrency_defaults_to_serial() -> None:
    config = create_game_config_from_player_count(6)

    assert config.vote_intention_concurrency == 1


def test_vote_intention_concurrency_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        GameConfig(
            num_players=6,
            role_names=["Werewolf", "Werewolf", "Seer", "Witch", "Villager", "Villager"],
            vote_intention_concurrency=0,
        )


def test_player_config_accepts_literal_api_key_and_temperature():
    from llm_werewolf.game_runtime.config.player_config import PlayerConfig

    cfg = PlayerConfig(
        name="P1",
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        api_key="sk-literal-123",
        temperature=1.1,
    )
    assert cfg.api_key == "sk-literal-123"
    assert cfg.temperature == 1.1
    # api_key_env 仍可单独使用，互不影响
    cfg2 = PlayerConfig(name="P2", model="demo")
    assert cfg2.api_key is None
    assert cfg2.temperature is None
