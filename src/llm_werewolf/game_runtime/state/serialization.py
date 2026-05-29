import json
from typing import Any
from pathlib import Path

from pydantic import Field, BaseModel

from llm_werewolf.game_runtime.events.events import EventLogger
from llm_werewolf.game_runtime.types import Event, GamePhase, PlayerStatus, PlayerProtocol, GameStateProtocol
from llm_werewolf.game_runtime.state.player import Player
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.roles.registry import get_role_map
from llm_werewolf.game_runtime.roles.neutral import Thief
from llm_werewolf.game_runtime.roles.villager import Cupid, Elder, Guard, Idiot, Witch, Knight, Magician
from llm_werewolf.game_runtime.roles.werewolf import WolfBeauty, BloodMoonApostle


class PlayerSnapshot(BaseModel):
    """玩家状态的可序列化快照。"""

    player_id: str
    name: str
    role_name: str
    role_data: dict[str, Any] = Field(default_factory=dict)
    is_alive: bool
    statuses: list[str] = Field(default_factory=list)
    lover_partner_id: str | None = None
    can_vote_flag: bool = True
    ai_model: str = "unknown"


class GameStateSnapshot(BaseModel):
    """游戏状态的可序列化快照。"""

    players: list[PlayerSnapshot]

    phase: str
    round_number: int

    night_deaths: list[str] = Field(default_factory=list)
    day_deaths: list[str] = Field(default_factory=list)
    death_abilities_used: list[str] = Field(default_factory=list)
    death_causes: dict[str, str] = Field(default_factory=dict)

    werewolf_target: str | None = None
    werewolf_votes: dict[str, str] = Field(default_factory=dict)
    witch_save_used: bool = False
    witch_poison_used: bool = False
    witch_saved_target: str | None = None
    witch_poison_target: str | None = None
    guard_protected: str | None = None
    guardian_wolf_protected: str | None = None
    nightmare_blocked: str | None = None
    seer_checked: dict[str, str] = Field(default_factory=dict)
    graveyard_checked: dict[str, str] = Field(default_factory=dict)

    # 投票追踪
    votes: dict[str, str] = Field(default_factory=dict)
    raven_marked: str | None = None
    wolf_beauty_charmed: str | None = None

    # 警长选举
    enable_sheriff: bool = False
    sheriff_id: str | None = None
    sheriff_election_done: bool = False
    sheriff_votes: dict[str, str] = Field(default_factory=dict)
    sheriff_tie_count: int = 0
    vote_tie_count: int = 0

    # 获胜方
    winner: str | None = None

    # 事件日志（与 EventLogger 同步，供读档恢复 observation）
    events: list[dict[str, Any]] = Field(default_factory=list)


def _extract_witch_data(role: Witch) -> dict[str, Any]:
    """提取女巫角色数据。"""
    return {"has_save_potion": role.has_save_potion, "has_poison_potion": role.has_poison_potion}


def _extract_role_data(player: PlayerProtocol) -> dict[str, Any]:
    """提取角色专属数据以供序列化。

    Args:
        player: 要提取角色数据的玩家。

    Returns:
        dict[str, Any]: 角色专属数据。
    """
    role = player.role
    role_data: dict[str, Any] = {}

    # 使用字典映射处理较简单的角色
    simple_extractors = {
        Guard: lambda r: {"last_protected": r.last_protected},
        Elder: lambda r: {"lives": r.lives},
        Idiot: lambda r: {"revealed": r.revealed},
        WolfBeauty: lambda r: {"charmed_player": r.charmed_player},
        Knight: lambda r: {"has_dueled": r.has_dueled},
        Cupid: lambda r: {"has_linked": r.has_linked},
        BloodMoonApostle: lambda r: {"transformed": r.transformed},
        Magician: lambda r: {"has_swapped": r.has_swapped},
        Thief: lambda r: {"has_chosen": r.has_chosen},
    }

    # 女巫需特殊处理
    if isinstance(role, Witch):
        return _extract_witch_data(role)

    # 检查简单提取器
    for role_class, extractor in simple_extractors.items():
        if isinstance(role, role_class):
            return extractor(role)

    return role_data


def serialize_player(player: PlayerProtocol) -> PlayerSnapshot:
    """将玩家序列化为快照。

    Args:
        player: 要序列化的玩家。

    Returns:
        PlayerSnapshot: 序列化后的玩家数据。
    """
    return PlayerSnapshot(
        player_id=player.player_id,
        name=player.name,
        role_name=player.get_role_name(),
        role_data=_extract_role_data(player),
        is_alive=player.is_alive(),
        statuses=[s.value for s in player.statuses],
        lover_partner_id=player.lover_partner_id,
        can_vote_flag=player.can_vote_flag,
        ai_model=player.ai_model,
    )


def serialize_game_state(game_state: GameStateProtocol) -> GameStateSnapshot:
    """将游戏状态序列化为快照。

    Args:
        game_state: 要序列化的游戏状态。

    Returns:
        GameStateSnapshot: 序列化后的游戏状态数据。
    """
    return GameStateSnapshot(
        players=[serialize_player(p) for p in game_state.players],
        phase=game_state.phase.value,
        round_number=game_state.round_number,
        night_deaths=list(game_state.night_deaths),
        day_deaths=list(game_state.day_deaths),
        death_abilities_used=list(game_state.death_abilities_used),
        death_causes=game_state.death_causes,
        werewolf_target=game_state.werewolf_target,
        werewolf_votes=game_state.werewolf_votes,
        witch_save_used=game_state.witch_save_used,
        witch_poison_used=game_state.witch_poison_used,
        witch_saved_target=game_state.witch_saved_target,
        witch_poison_target=game_state.witch_poison_target,
        guard_protected=game_state.guard_protected,
        guardian_wolf_protected=game_state.guardian_wolf_protected,
        nightmare_blocked=game_state.nightmare_blocked,
        seer_checked={str(k): v for k, v in game_state.seer_checked.items()},
        graveyard_checked={str(k): v for k, v in game_state.graveyard_checked.items()},
        votes=game_state.votes,
        raven_marked=game_state.raven_marked,
        wolf_beauty_charmed=game_state.wolf_beauty_charmed,
        sheriff_id=game_state.sheriff_id,
        enable_sheriff=game_state.enable_sheriff,
        sheriff_election_done=game_state.sheriff_election_done,
        sheriff_votes=game_state.sheriff_votes,
        sheriff_tie_count=game_state.sheriff_tie_count,
        vote_tie_count=game_state.vote_tie_count,
        winner=game_state.winner,
    )


def serialize_events(event_logger: EventLogger) -> list[dict[str, Any]]:
    """将 EventLogger 中的事件序列化为可 JSON 存储的 dict 列表。"""
    return [event.model_dump(mode="json") for event in event_logger.events]


def restore_event_logger(events: list[dict[str, Any]]) -> EventLogger:
    """从存档中的事件列表恢复 EventLogger。"""
    logger = EventLogger()
    for raw in events:
        try:
            logger.log_event(Event.model_validate(raw))
        except (ValueError, TypeError):
            continue
    return logger


def save_game_state(
    game_state: GameStateProtocol,
    file_path: str | Path,
    *,
    event_logger: EventLogger | None = None,
) -> None:
    """将游戏状态保存到 JSON 文件。

    Args:
        game_state: 要保存的游戏状态。
        file_path: 存档文件路径。
        event_logger: 可选，一并持久化事件日志。
    """
    snapshot = serialize_game_state(game_state)
    if event_logger is not None:
        snapshot.events = serialize_events(event_logger)
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        f.write(snapshot.model_dump_json(indent=2))


def load_game_state_snapshot(file_path: str | Path) -> GameStateSnapshot:
    """从 JSON 文件加载游戏状态快照。

    Args:
        file_path: 存档文件路径。

    Returns:
        GameStateSnapshot: 加载的游戏状态快照。

    Note:
        此函数仅加载快照。要恢复包含 agent 的完整 GameState，
        需使用 restore_game_state() 并提供 agent 工厂。
    """
    path = Path(file_path)

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return GameStateSnapshot.model_validate(data)


def _restore_witch_data(role: Witch, role_data: dict[str, Any]) -> None:
    """恢复女巫角色数据。"""
    role.has_save_potion = role_data.get("has_save_potion", True)
    role.has_poison_potion = role_data.get("has_poison_potion", True)


def _restore_role_data(player: Player, role_data: dict[str, Any]) -> None:
    """将角色专属数据恢复到玩家角色上。

    Args:
        player: 要恢复角色的玩家。
        role_data: 要恢复的角色专属数据。
    """
    role = player.role

    # 使用字典映射处理较简单的角色
    simple_restorers = {
        Guard: lambda r, d: setattr(r, "last_protected", d.get("last_protected")),
        Elder: lambda r, d: setattr(r, "lives", d.get("lives", 2)),
        Idiot: lambda r, d: setattr(r, "revealed", d.get("revealed", False)),
        WolfBeauty: lambda r, d: setattr(r, "charmed_player", d.get("charmed_player")),
        Knight: lambda r, d: setattr(r, "has_dueled", d.get("has_dueled", False)),
        Cupid: lambda r, d: setattr(r, "has_linked", d.get("has_linked", False)),
        BloodMoonApostle: lambda r, d: setattr(r, "transformed", d.get("transformed", False)),
        Magician: lambda r, d: setattr(r, "has_swapped", d.get("has_swapped", False)),
        Thief: lambda r, d: setattr(r, "has_chosen", d.get("has_chosen", False)),
    }

    # 女巫需特殊处理
    if isinstance(role, Witch):
        _restore_witch_data(role, role_data)
        return

    # 检查简单恢复器
    for role_class, restorer in simple_restorers.items():
        if isinstance(role, role_class):
            restorer(role, role_data)
            return


def _restore_players(snapshot: GameStateSnapshot, agent_factory: dict[str, Any]) -> list[Player]:
    """从快照恢复玩家。

    Args:
        snapshot: 游戏状态快照。
        agent_factory: 玩家 ID 到 agent 实例的映射字典。

    Returns:
        list[Player]: 恢复后的玩家列表。

    Raises:
        ValueError: 遇到未知角色时抛出。
    """
    players: list[Player] = []
    role_map = get_role_map()

    for p_snap in snapshot.players:
        # 从注册表获取角色类
        role_class = role_map.get(p_snap.role_name)
        if not role_class:
            msg = f"Unknown role: {p_snap.role_name}"
            raise ValueError(msg)

        # 获取该玩家的 agent（若有）
        agent = agent_factory.get(p_snap.player_id)

        # 创建玩家
        player = Player(
            player_id=p_snap.player_id,
            name=p_snap.name,
            role=role_class,
            agent=agent,
            ai_model=p_snap.ai_model,
        )

        # 恢复玩家状态
        if not p_snap.is_alive:
            player.kill()

        player.statuses = {PlayerStatus(s) for s in p_snap.statuses}
        player.lover_partner_id = p_snap.lover_partner_id
        player.can_vote_flag = p_snap.can_vote_flag

        # 恢复角色专属数据
        _restore_role_data(player, p_snap.role_data)

        players.append(player)

    return players


def _restore_game_state_fields(game_state: GameState, snapshot: GameStateSnapshot) -> None:
    """从快照恢复游戏状态字段。

    Args:
        game_state: 要恢复字段的游戏状态。
        snapshot: 包含待恢复字段的快照。
    """
    game_state.phase = GamePhase(snapshot.phase)
    game_state.round_number = snapshot.round_number

    game_state.night_deaths = set(snapshot.night_deaths)
    game_state.day_deaths = set(snapshot.day_deaths)
    game_state.death_abilities_used = set(snapshot.death_abilities_used)
    game_state.death_causes = snapshot.death_causes

    game_state.werewolf_target = snapshot.werewolf_target
    game_state.werewolf_votes = snapshot.werewolf_votes
    game_state.witch_save_used = snapshot.witch_save_used
    game_state.witch_poison_used = snapshot.witch_poison_used
    game_state.witch_saved_target = snapshot.witch_saved_target
    game_state.witch_poison_target = snapshot.witch_poison_target
    game_state.guard_protected = snapshot.guard_protected
    game_state.guardian_wolf_protected = snapshot.guardian_wolf_protected
    game_state.nightmare_blocked = snapshot.nightmare_blocked
    game_state.seer_checked = {int(k): v for k, v in snapshot.seer_checked.items()}
    game_state.graveyard_checked = {
        int(k): v for k, v in snapshot.graveyard_checked.items()
    }

    game_state.votes = snapshot.votes
    game_state.raven_marked = snapshot.raven_marked
    game_state.wolf_beauty_charmed = snapshot.wolf_beauty_charmed

    game_state.sheriff_election_done = snapshot.sheriff_election_done
    game_state.enable_sheriff = snapshot.enable_sheriff
    game_state.sheriff_votes = snapshot.sheriff_votes
    game_state.sheriff_tie_count = snapshot.sheriff_tie_count
    game_state.vote_tie_count = snapshot.vote_tie_count
    if snapshot.sheriff_id:
        game_state.set_sheriff(snapshot.sheriff_id)

    game_state.winner = snapshot.winner


def restore_game_state(
    snapshot: GameStateSnapshot, agent_factory: dict[str, Any] | None = None
) -> GameState:
    """从快照恢复 GameState。

    Args:
        snapshot: 游戏状态快照。
        agent_factory: 可选，玩家 ID 到 agent 实例的映射字典。未提供时玩家将没有 agent。

    Returns:
        GameState: 恢复后的游戏状态。

    Note:
        Agent 无法序列化，需手动重建。
        传入 player_id 到 agent 实例的映射以恢复 agent。
    """
    agent_factory = agent_factory or {}

    # 恢复玩家
    players = _restore_players(snapshot, agent_factory)

    # 创建游戏状态
    game_state = GameState(players)

    # 恢复游戏状态字段
    _restore_game_state_fields(game_state, snapshot)

    return game_state


def load_game_state(
    file_path: str | Path, agent_factory: dict[str, Any] | None = None
) -> GameState:
    """从 JSON 文件加载游戏状态。

    Args:
        file_path: 存档文件路径。
        agent_factory: 可选，玩家 ID 到 agent 实例的映射字典。

    Returns:
        GameState: 恢复后的游戏状态。
    """
    snapshot = load_game_state_snapshot(file_path)
    return restore_game_state(snapshot, agent_factory)
