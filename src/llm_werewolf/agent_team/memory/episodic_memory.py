"""情景记忆：基于 EventLogger 的结构化查询。"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from llm_werewolf.game_runtime.events import EventLogger
from llm_werewolf.game_runtime.types import Event, EventType

_KEY_EVENT_TYPES = {
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
    """封装 EventLogger，提供记忆视角的时间线与导出能力。"""

    def __init__(self, event_logger: EventLogger):
        self._logger = event_logger

    def get_player_timeline(
        self,
        player_id: str,
        since_round: int | None = None,
    ) -> list[Event]:
        """获取玩家视角的可见事件。"""
        return self._logger.get_events_for_player(player_id, since_round)

    def get_key_events(self, player_id: str) -> list[Event]:
        """返回关键决策和结果事件。"""
        all_events = self._logger.get_events_for_player(player_id)
        return [event for event in all_events if event.event_type in _KEY_EVENT_TYPES]

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
        key_events = [event.message for event in events if event.event_type in _KEY_EVENT_TYPES]
        decision_events = [
            event.message
            for event in events
            if event.event_type in {EventType.VOTE_CAST, EventType.SHERIFF_VOTE_CAST}
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
