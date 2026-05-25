from pathlib import Path

from llm_werewolf.game_runtime.events import EventLogger
from llm_werewolf.game_runtime.types import EventType, GamePhase
from llm_werewolf.agent_team.memory.config import MemoryConfig
from llm_werewolf.agent_team.memory.memory_manager import MemoryManager


def test_memory_manager_injects_semantic_and_working_context(tmp_path: Path):
    manager = MemoryManager(
        EventLogger(),
        role="villager",
        player_id="p1",
        plan_name="bold",
        data_dir=tmp_path / "semantic_cards",
    )
    manager.semantic.add_card("villager", "白天优先核对发言与投票是否一致")

    manager.on_game_start("villager")
    manager.working.add_dynamic("我决定先跟进4号的视角", tag="decision")

    context = manager.get_context_for_decision()
    assert "【稳定经验】" in context
    assert "【跨局经验】" in context
    assert "我决定先跟进4号的视角" in context
    assert "程序记忆" in context
    assert "当前采用计划：bold" in context


def test_memory_manager_updates_card_weight_after_game(tmp_path: Path):
    data_dir = tmp_path / "semantic_cards"
    manager = MemoryManager(EventLogger(), role="wolf", player_id="p2", data_dir=data_dir)
    card = manager.semantic.add_card("wolf", "优先处理发言清晰的强神")

    manager.on_game_start("wolf")
    manager.on_game_end(won=True)

    refreshed = manager.semantic.retrieve_for_role("wolf", top_k=1)[0]
    assert refreshed.id == card.id
    assert refreshed.weight > 1.0
    assert refreshed.use_count == 1
    assert refreshed.win_count == 1


def test_memory_manager_respects_memory_config_and_collects_runtime_inputs(tmp_path: Path):
    logger = EventLogger()
    manager = MemoryManager(
        logger,
        role="villager",
        player_id="player_1",
        data_dir=tmp_path / "semantic_cards",
        config=MemoryConfig(working_max_rounds=2, working_max_dynamic_items=3),
    )

    manager.add_public_speech("1号", "我先听4号怎么聊", round_number=1)
    event = logger.create_event(
        EventType.VOTE_RESULT,
        round_number=1,
        phase=GamePhase.DAY_VOTING,
        message="4号成为焦点票型",
        visible_to=None,
    )
    manager.add_event(event)

    context = manager.get_context_for_decision()
    assert "1号发言" in context
    assert "4号成为焦点票型" in context


def test_memory_manager_extracts_semantic_candidates_by_outcome(tmp_path: Path):
    logger = EventLogger()
    logger.create_event(
        EventType.VOTE_CAST,
        round_number=2,
        phase=GamePhase.DAY_VOTING,
        message="2号投给5号",
        visible_to=["player_2"],
    )
    logger.create_event(
        EventType.VOTE_RESULT,
        round_number=2,
        phase=GamePhase.DAY_VOTING,
        message="5号得票最高",
        visible_to=["player_2"],
    )
    manager = MemoryManager(
        logger,
        role="villager",
        player_id="player_2",
        data_dir=tmp_path / "semantic_cards",
        config=MemoryConfig(semantic_top_k=5),
    )

    won_candidates = manager.extract_semantic_candidates(won=True)
    lost_candidates = manager.extract_semantic_candidates(won=False)

    assert any("胜利经验" in candidate for candidate in won_candidates)
    assert any("失败反思" in candidate for candidate in lost_candidates)


def test_semantic_memory_merges_similar_cards(tmp_path: Path):
    manager = MemoryManager(
        EventLogger(),
        role="villager",
        player_id="player_3",
        data_dir=tmp_path / "semantic_cards",
        config=MemoryConfig(),
    )

    first = manager.semantic.add_or_merge_card("villager", "关键局势复盘：第2轮出现5号得票最高")
    second = manager.semantic.add_or_merge_card("villager", "关键局势复盘：第2轮出现5号得票最高；应继续跟踪")
    cards = manager.semantic.retrieve_for_role("villager", top_k=10)

    assert first.id == second.id
    assert len(cards) == 1
    assert cards[0].use_count >= 1


def test_memory_manager_extracts_and_persists_semantic_candidates_on_game_end(tmp_path: Path):
    logger = EventLogger()
    logger.create_event(
        EventType.VOTE_CAST,
        round_number=3,
        phase=GamePhase.DAY_VOTING,
        message="3号投给6号",
        visible_to=["player_3"],
    )
    logger.create_event(
        EventType.VOTE_RESULT,
        round_number=3,
        phase=GamePhase.DAY_VOTING,
        message="6号成为放逐焦点",
        visible_to=["player_3"],
    )
    manager = MemoryManager(
        logger,
        role="villager",
        player_id="player_3",
        data_dir=tmp_path / "semantic_cards",
        config=MemoryConfig(extract_semantic_on_game_end=True, semantic_top_k=5),
    )

    manager.on_game_end(won=False)
    cards = manager.semantic.retrieve_for_role("villager", top_k=10)

    assert any("失败反思" in card.content for card in cards)
