from __future__ import annotations

from pydantic import BaseModel, Field

from llm_werewolf.core.types import Event, GameStateInfo, PlayerInfo, PlayerProtocol


class PlayerObservation(BaseModel):
    """单个玩家可见的过滤后游戏上下文。"""

    self_player: PlayerInfo = Field(..., description="Public identity and status of the acting player")
    game_state: GameStateInfo = Field(..., description="Public game-state summary")
    visible_players: list[PlayerInfo] = Field(
        default_factory=list,
        description="Publicly visible player information for all players",
    )
    visible_events: list[Event] = Field(
        default_factory=list,
        description="Events this player is allowed to observe",
    )
    private_notes: list[str] = Field(
        default_factory=list,
        description="Role-specific private facts only this player may know",
    )


def flatten_private_notes(notes: list | None) -> list[str]:
    """将 private_notes 规范为纯字符串（EngineContexts 可能传入嵌套列表）。"""
    flat: list[str] = []
    for item in notes or []:
        if isinstance(item, (list, tuple)):
            flat.extend(str(part) for part in item if str(part).strip())
        elif item is not None and str(item).strip():
            flat.append(str(item))
    return flat


class ObservationBuilder:
    """在严格信息隔离下构建玩家专属视图。"""

    def build(
        self,
        player: PlayerProtocol,
        game_state: GameStateInfo,
        all_players: list[PlayerProtocol],
        visible_events: list[Event],
        private_notes: list[str] | None = None,
    ) -> PlayerObservation:
        return PlayerObservation(
            self_player=player.get_public_info(),
            game_state=game_state,
            visible_players=[other.get_public_info() for other in all_players],
            visible_events=visible_events,
            private_notes=flatten_private_notes(private_notes),
        )

    def format_for_prompt(
        self,
        observation: PlayerObservation,
        include_visible_events: bool = True,
        include_private_notes: bool = True,
    ) -> str:
        lines = [
            f"你是 {observation.self_player.name}。",
            f"当前阶段：{observation.game_state.phase.value}",
            f"当前轮次：第 {observation.game_state.round_number} 轮",
            (
                "存活概况："
                f"{observation.game_state.alive_players}/{observation.game_state.total_players} 人存活，"
                f"狼人 {observation.game_state.werewolves_alive}，"
                f"好人 {observation.game_state.villagers_alive}"
            ),
            "",
            "场上玩家：",
        ]

        for info in observation.visible_players:
            status = "存活" if info.is_alive else "死亡"
            lines.append(f"- {info.name}（{info.player_id}）：{status}")

        if include_visible_events and observation.visible_events:
            lines.extend(["", "可见事件记录："])
            for event in observation.visible_events:
                lines.append(f"- [{event.phase} 第{event.round_number}轮] {event.message}")

        if include_private_notes and observation.private_notes:
            lines.extend(["", "私密信息："])
            for note in observation.private_notes:
                lines.append(f"- {note}")

        return "\n".join(lines)
