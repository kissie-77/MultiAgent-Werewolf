"""情景记忆：基于 EventLogger 的全局事件存储与结构化查询。"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from llm_werewolf.game_runtime.events.events import EventLogger
from llm_werewolf.game_runtime.types import Event, EventType

KEY_EVENT_TYPES = {
    EventType.VOTE_CAST,
    EventType.VOTE_RESULT,
    EventType.PLAYER_DIED,
    EventType.PLAYER_ELIMINATED,
    EventType.WEREWOLF_KILLED,
    EventType.WITCH_POISONED,
    EventType.WITCH_SAVED,
    EventType.SEER_CHECKED,
    EventType.GUARD_PROTECTED,
    EventType.SHERIFF_VOTE_CAST,
    EventType.SHERIFF_ELECTED,
}


@dataclass
class EpisodeRecord:
    """按轮组织的复盘单元。"""

    player_id: str
    round_number: int
    visible_event_count: int
    key_event_messages: list[str]
    decision_event_messages: list[str]
    summary: str


class EpisodicMemory:
    """封装 EventLogger，底层以全量事件存储，查询接口支持过滤。"""

    def __init__(self, event_logger: EventLogger):
        self._logger = event_logger

    # ── 全局查询（不过滤玩家可见性） ──

    def get_all_events(
        self,
        *,
        since_round: int | None = None,
        event_types: set[EventType] | None = None,
    ) -> list[Event]:
        """获取全量事件，支持按轮次和事件类型过滤。"""
        events = list(self._logger.events)
        if since_round is not None:
            events = [e for e in events if e.round_number >= since_round]
        if event_types is not None:
            events = [e for e in events if e.event_type in event_types]
        return events

    def get_round_events(self, round_number: int) -> list[Event]:
        """获取指定轮次的所有事件。"""
        return [e for e in self._logger.events if e.round_number == round_number]

    def get_global_key_events(self) -> list[Event]:
        """返回全局关键决策和结果事件。"""
        return [e for e in self._logger.events if e.event_type in KEY_EVENT_TYPES]

    def get_thought_events(
        self,
        player_id: str | None = None,
    ) -> list[Event]:
        """获取心理记录事件（AGENT_THOUGHT），仅用于复盘/教练。"""
        events = [e for e in self._logger.events if e.event_type == EventType.AGENT_THOUGHT]
        if player_id is not None:
            events = [e for e in events if e.data.get("player_id") == player_id]
        return events

    # ── 玩家视角查询（过滤可见性） ──

    def get_player_timeline(
        self,
        player_id: str,
        since_round: int | None = None,
    ) -> list[Event]:
        """获取玩家视角的可见事件。"""
        return self._logger.get_events_for_player(player_id, since_round)

    def get_key_events(self, player_id: str) -> list[Event]:
        """返回某玩家可见的关键决策和结果事件。"""
        all_events = self._logger.get_events_for_player(player_id)
        return [event for event in all_events if event.event_type in KEY_EVENT_TYPES]

    # ── 摘要与导出 ──

    def summarize_round(self, player_id: str, round_number: int) -> str:
        """按玩家视角生成单轮规则式摘要。"""
        events = [
            event
            for event in self.get_player_timeline(player_id, since_round=round_number)
            if event.round_number == round_number
        ]
        if not events:
            return f"第{round_number}轮：无可见事件"
        preview = "；".join(event.message for event in events[:5])
        return f"第{round_number}轮：{preview}"

    def build_round_episode(self, player_id: str, round_number: int) -> EpisodeRecord:
        """将单轮事件组织为可复盘的 episode 单元。"""
        events = [
            event
            for event in self.get_player_timeline(player_id, since_round=round_number)
            if event.round_number == round_number
        ]
        key_events = [event.message for event in events if event.event_type in KEY_EVENT_TYPES]
        decision_events = [
            event.message
            for event in events
            if event.event_type in {EventType.VOTE_CAST, EventType.SHERIFF_VOTE_CAST}
            and event.data.get("voter_id") == player_id
        ]
        return EpisodeRecord(
            player_id=player_id,
            round_number=round_number,
            visible_event_count=len(events),
            key_event_messages=key_events,
            decision_event_messages=decision_events,
            summary=self.summarize_round(player_id, round_number),
        )

    def export_episode_report(self, player_id: str) -> dict:
        """导出玩家整局的 episode 复盘数据。"""
        timeline = self.get_player_timeline(player_id)
        rounds = sorted({event.round_number for event in timeline})
        episodes = [asdict(self.build_round_episode(player_id, round_number)) for round_number in rounds]
        return {
            "player_id": player_id,
            "episode_count": len(episodes),
            "episodes": episodes,
        }

    def export_for_analysis(self) -> dict:
        """导出完整事件数据，供评测/复盘使用。"""
        return {
            "total_events": len(self._logger.events),
            "events": [event.model_dump(mode="json") for event in self._logger.events],
        }
