from llm_werewolf.game_runtime.config.game_config import GameConfig


def _validate_player_count(num_players: int) -> None:
    """校验玩家数量在可接受范围内。

    Args:
        num_players: 待校验的玩家数量。

    Raises:
        ValueError: 玩家数量超出有效范围（6-20）时抛出。
    """
    if num_players < 6:
        msg = "Minimum 6 players required"
        raise ValueError(msg)
    if num_players > 20:
        msg = "Maximum 20 players supported"
        raise ValueError(msg)


def _allocate_werewolf_roles(num_players: int) -> list[str]:
    """根据玩家数量分配狼人角色。

    Args:
        num_players: 玩家总数。

    Returns:
        list[str]: 狼人角色名称列表。
    """
    if num_players <= 8:
        return ["Werewolf", "Werewolf"]
    if num_players <= 11:
        return ["Werewolf", "Werewolf", "AlphaWolf"]
    if num_players <= 14:
        return ["Werewolf", "Werewolf", "AlphaWolf", "WhiteWolf"]
    return ["Werewolf", "Werewolf", "AlphaWolf", "WhiteWolf", "WolfBeauty"]


def _allocate_villager_roles(num_players: int) -> list[str]:
    """根据玩家数量分配好人阵营角色。

    Args:
        num_players: 玩家总数。

    Returns:
        list[str]: 好人阵营角色名称列表。
    """
    # 核心神职（始终存在）
    roles = ["Seer", "Witch"]

    # 根据玩家数量追加神职
    if num_players >= 7:
        roles.append("Guard")
    if num_players >= 9:
        roles.append("Hunter")
    if num_players >= 11:
        roles.append("Cupid")
    if num_players >= 13:
        roles.append("Idiot")
    if num_players >= 15:
        roles.append("Elder")
    if num_players >= 17:
        roles.append("Knight")
    if num_players >= 19:
        roles.append("Raven")

    return roles


def _get_timeouts(num_players: int) -> tuple[int, int, int]:
    """根据玩家数量获取超时值。

    Args:
        num_players: 玩家总数。

    Returns:
        tuple[int, int, int]: (night_timeout, day_timeout, vote_timeout)
    """
    if num_players <= 8:
        return (45, 180, 45)
    if num_players <= 12:
        return (60, 300, 60)
    return (90, 400, 90)


def create_game_config_from_player_count(num_players: int) -> GameConfig:
    """根据玩家数量自动生成游戏配置。

    该函数按玩家总数缩放狼人与特殊角色数量，生成平衡的角色构成。

    Args:
        num_players: 游戏中的玩家数量（6-20）。

    Returns:
        GameConfig: 生成的、角色平衡的游戏配置。

    Raises:
        ValueError: 玩家数量超出有效范围（6-20）时抛出。
    """
    _validate_player_count(num_players)

    # 分配狼人与好人阵营角色
    role_names = _allocate_werewolf_roles(num_players)
    role_names.extend(_allocate_villager_roles(num_players))

    # 剩余名额填充平民
    num_special_roles = len(role_names)
    num_villagers = num_players - num_special_roles
    role_names.extend(["Villager"] * num_villagers)

    # 获取超时设置
    night_timeout, day_timeout, vote_timeout = _get_timeouts(num_players)

    return GameConfig(
        num_players=num_players,
        role_names=role_names,
        night_timeout=night_timeout,
        day_timeout=day_timeout,
        vote_timeout=vote_timeout,
    )
