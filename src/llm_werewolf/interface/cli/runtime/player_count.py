"""CLI 辅助：按 ``--players N`` 调整内存中的玩家名单（不改动磁盘 YAML）。"""

from __future__ import annotations

from llm_werewolf.game_runtime.config.player_config import PlayersConfig

_MIN_PLAYERS = 6
_MAX_PLAYERS = 20


def resize_players_config(cfg: PlayersConfig, n: int) -> PlayersConfig:
    """返回座位数恰为 ``n`` 的新 :class:`PlayersConfig`。"""
    if n < _MIN_PLAYERS or n > _MAX_PLAYERS:
        msg = f"--players 必须在 {_MIN_PLAYERS}-{_MAX_PLAYERS} 之间，收到 {n}"
        raise ValueError(msg)

    players = list(cfg.players)
    if n == len(players):
        return cfg

    human_count = sum(1 for p in players if p.model == "human")
    if n < human_count:
        msg = f"无法缩减到 {n} 座：当前存在 {human_count} 个 human 座位"
        raise ValueError(msg)

    if n < len(players):
        kept, tail = players[:n], players[n:]
        if any(p.model == "human" for p in tail):
            msg = "缩减会丢弃 human 座位；请把人类座位放到更靠前的位置"
            raise ValueError(msg)
        players = kept
    else:
        template = next((p for p in reversed(players) if p.model != "human"), None)
        if template is None:
            msg = "无法扩容：名单里没有可作模板的非 human 座位，请先保留至少一个 LLM/demo 座位"
            raise ValueError(msg)
        existing = {p.name for p in players}
        k = len(players) + 1
        while len(players) < n:
            name = f"Player{k}"
            while name in existing:
                k += 1
                name = f"Player{k}"
            players.append(template.model_copy(update={"name": name}))
            existing.add(name)
            k += 1

    data = cfg.model_dump(mode="json", exclude={"use_agentscope_backend"})
    data["players"] = [p.model_dump(mode="json") for p in players]
    return PlayersConfig.model_validate(data)
