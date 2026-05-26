"""CLI 辅助：把 ``--human_seat`` 命令行覆盖应用到已加载的配置上。

``--human_seat`` 接受 1-based 座位号，可用逗号分隔指定多个人类座位（如 ``1,3``）。
被指定的座位会改成 ``model="human"``（保留原显示名）。重建走 ``model_validate``
以保证重名 / 长度校验仍然生效。
"""

from __future__ import annotations

from llm_werewolf.game_runtime.config.player_config import PlayersConfig


def parse_seat_list(spec: str | int | tuple | list | None) -> list[int]:
    """把 ``"1,3"`` / ``1`` / ``(1, 3)`` / ``None`` 解析成座位号列表。

    注意：python-fire 会把 ``--human_seat 1,3`` 解析成 ``tuple``（而非字符串），
    把 ``--human_seat 1`` 解析成 ``int``，因此这里必须兼容序列与标量两种输入。
    """
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
