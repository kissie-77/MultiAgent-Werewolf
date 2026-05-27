from llm_werewolf.game_runtime.events import EventLogger
from llm_werewolf.game_runtime.types import EventType, GamePhase
from llm_werewolf.agent_team.memory.episodic_memory import EpisodicMemory


def test_episodic_memory_returns_visible_timeline_and_key_events():
    logger = EventLogger()
    logger.create_event(
        EventType.PLAYER_SPEECH,
        round_number=1,
        phase=GamePhase.DAY_DISCUSSION,
        message="1号发言怀疑3号",
        visible_to=None,
    )
    logger.create_event(
        EventType.VOTE_CAST,
        round_number=1,
        phase=GamePhase.DAY_VOTING,
        message="1号投给3号",
        data={"voter_id": "player_1"},
        visible_to=["player_1"],
    )

    memory = EpisodicMemory(logger)
    timeline = memory.get_player_timeline("player_1")
    key_events = memory.get_key_events("player_1")

    assert len(timeline) == 2
    assert len(key_events) == 1
    assert key_events[0].event_type == EventType.VOTE_CAST


def test_episodic_memory_summarize_and_export():
    logger = EventLogger()
    logger.create_event(
        EventType.PLAYER_ELIMINATED,
        round_number=2,
        phase=GamePhase.DAY_VOTING,
        message="4号被投票淘汰",
        visible_to=None,
    )

    memory = EpisodicMemory(logger)
    summary = memory.summarize_round("player_2", 2)
    exported = memory.export_for_analysis()

    assert "第2轮" in summary
    assert "4号被投票淘汰" in summary
    assert exported["total_events"] == 1
    assert exported["events"][0]["message"] == "4号被投票淘汰"


def test_episodic_memory_builds_episode_report():
    logger = EventLogger()
    logger.create_event(
        EventType.VOTE_CAST,
        round_number=2,
        phase=GamePhase.DAY_VOTING,
        message="2号投给5号",
        data={"voter_id": "player_2"},
        visible_to=["player_2"],
    )
    logger.create_event(
        EventType.VOTE_RESULT,
        round_number=2,
        phase=GamePhase.DAY_VOTING,
        message="5号得票最高",
        visible_to=["player_2"],
    )

    memory = EpisodicMemory(logger)
    report = memory.export_episode_report("player_2")

    assert report["episode_count"] == 1
    assert report["episodes"][0]["round_number"] == 2
    assert "2号投给5号" in report["episodes"][0]["decision_event_messages"]


def test_episode_decision_events_only_include_current_player_votes():
    logger = EventLogger()
    own_vote = "2号投给5号"
    other_visible_vote = "3号投给5号"
    logger.create_event(
        EventType.VOTE_CAST,
        round_number=2,
        phase=GamePhase.DAY_VOTING,
        message=own_vote,
        data={"voter_id": "player_2"},
        visible_to=["player_2"],
    )
    logger.create_event(
        EventType.VOTE_CAST,
        round_number=2,
        phase=GamePhase.DAY_VOTING,
        message=other_visible_vote,
        data={"voter_id": "player_3"},
        visible_to=["player_2"],
    )

    memory = EpisodicMemory(logger)
    episode = memory.build_round_episode("player_2", 2)

    assert episode.decision_event_messages == [own_vote]
