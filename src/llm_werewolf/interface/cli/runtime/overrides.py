"""CLI 辅助：把 ``--human_seat`` 命令行覆盖应用到已加载的配置上。"""

from __future__ import annotations

from llm_werewolf.game_runtime.config.player_config import PlayersConfig, PlanAssignmentConfig


def parse_seat_list(spec: str | int | tuple | list | None) -> list[int]:
    """把 ``"1,3"`` / ``1`` / ``(1, 3)`` / ``None`` 解析成座位号列表。"""
    if spec is None:
        return []
    if isinstance(spec, (list, tuple)):
        return [int(x) for x in spec]
    text = str(spec).strip()
    if not text:
        return []
    return [int(part.strip()) for part in text.split(",") if part.strip()]


def apply_human_seats(cfg: PlayersConfig, seats: list[int]) -> PlayersConfig:
    """把指定 1-based 座位号的玩家改成 human（保留原名）。"""
    if not seats:
        return cfg

    total = len(cfg.players)
    for seat in seats:
        if seat < 1 or seat > total:
            msg = f"--human_seat={seat} 超出范围（1-{total}）"
            raise ValueError(msg)

    new_players: list[dict] = []
    for idx, player in enumerate(cfg.players, start=1):
        if idx in seats:
            new_players.append({"name": player.name, "model": "human"})
        else:
            new_players.append(player.model_dump(mode="json"))

    data = cfg.model_dump(mode="json", exclude={"use_agentscope_backend"})
    data["players"] = new_players
    return PlayersConfig.model_validate(data)


def apply_plan_assignment_override(
    cfg: PlayersConfig,
    mode: str | None,
    *,
    seed: int | None = None,
) -> PlayersConfig:
    """覆盖开局 plan 分流设置，方便同配置做 A/B 验证。"""
    if mode is None and seed is None:
        return cfg

    data = cfg.model_dump(mode="json", exclude={"use_agentscope_backend"})
    current = cfg.plan_assignment.model_dump(mode="json")
    normalized = (mode or "").strip().lower()

    if normalized in {"", "keep"}:
        assignment = PlanAssignmentConfig.model_validate(current)
    elif normalized in {"off", "none", "disabled", "false", "0"}:
        assignment = PlanAssignmentConfig.model_validate({**current, "enabled": False})
    elif normalized in {"role_cycle", "cycle"}:
        assignment = PlanAssignmentConfig.model_validate({
            **current,
            "enabled": True,
            "mode": "role_cycle",
        })
    elif normalized in {"role_random", "random"}:
        assignment = PlanAssignmentConfig.model_validate({
            **current,
            "enabled": True,
            "mode": "role_random",
        })
    else:
        msg = "--plan_assignment 只能是 off、role_cycle 或 role_random"
        raise ValueError(msg)

    if seed is not None:
        assignment = assignment.model_copy(update={"seed": int(seed)})

    data["plan_assignment"] = assignment.model_dump(mode="json")
    return PlayersConfig.model_validate(data)
