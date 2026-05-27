from pathlib import Path

import pytest

from llm_werewolf.agent_team import skill_loader
from llm_werewolf.agent_team.memory.config import MemoryConfig
from llm_werewolf.agent_team.memory.memory_manager import MemoryManager
from llm_werewolf.agent_team.memory.semantic_memory import InMemoryBackend, SemanticMemory, StrategyCard
from llm_werewolf.game_runtime.events import EventLogger
from llm_werewolf.game_runtime.types import EventType, GamePhase


class StubCompressor:
    def __init__(self, response: str | Exception) -> None:
        self.response = response
        self.prompts: list[str] = []

    def _call_llm_text(self, prompt: str, max_tokens: int = 300) -> str:
        del max_tokens
        self.prompts.append(prompt)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


DESCRIPTION_ONE = "\u7b2c\u4e00\u5929\u6ca1\u6709\u4eba\u8df3\u9884\u8a00\u5bb6\u7684\u60c5\u51b5\u4e0b\uff0c\u4f7f\u7528\u8be5 skill"
DESCRIPTION_TWO = "\u9884\u8a00\u5bb6\u7b2c\u4e8c\u5929\u4ecd\u672a\u5e26\u8282\u594f\u7684\u60c5\u51b5\u4e0b\uff0c\u4f7f\u7528\u8be5 skill"
SKILL_BODY = (
    "\u4f5c\u4e3a\u72fc\u4eba\uff0c\u9996\u8f6e\u4e0d\u8981\u66b4\u9732\u961f\u53cb\u8eab\u4efd\uff0c"
    "\u4f18\u5148\u8ddf\u98ce\u6751\u6c11\u53d1\u8a00\u3002"
)
VILLAGER_EXPERIENCE = "\u767d\u5929\u4f18\u5148\u6838\u5bf9\u53d1\u8a00\u4e0e\u6295\u7968\u662f\u5426\u4e00\u81f4\u3002"
DECISION_TEXT = "\u6211\u51b3\u5b9a\u5148\u8ddf\u8fdb4\u53f7\u7684\u89c6\u89d2"


@pytest.fixture
def temp_skill_root(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: tmp_path)
    skill_loader.list_role_skill_files.cache_clear()
    yield tmp_path
    skill_loader.list_role_skill_files.cache_clear()


def test_memory_manager_injects_semantic_and_working_context():
    manager = MemoryManager(
        EventLogger(),
        role="villager",
        player_id="p1",
        plan_name="bold",
        config=MemoryConfig(),
        semantic_backend=InMemoryBackend(),
    )
    manager.semantic.add_card("villager", VILLAGER_EXPERIENCE)

    manager.on_game_start("villager")
    manager.working.add_dynamic(DECISION_TEXT, tag="decision")

    context = manager.get_context_for_decision()
    assert "\u3010\u7a33\u5b9a\u7ecf\u9a8c\u3011" in context
    assert "[经验]" in context
    assert VILLAGER_EXPERIENCE.rstrip("\u3002") in context
    assert DECISION_TEXT in context
    assert "\u7a0b\u5e8f\u8bb0\u5fc6" in context
    assert "\u5f53\u524d\u91c7\u7528\u8ba1\u5212\uff1abold" in context


def test_memory_manager_updates_card_weight_after_game():
    manager = MemoryManager(
        EventLogger(),
        role="wolf",
        player_id="p2",
        config=MemoryConfig(),
        semantic_backend=InMemoryBackend(),
    )
    card = manager.semantic.add_card("wolf", "\u4f18\u5148\u5904\u7406\u53d1\u8a00\u6e05\u6670\u7684\u5f3a\u795e\u3002")

    manager.on_game_start("wolf")
    manager.on_game_end(won=True)

    refreshed = manager.semantic.retrieve_for_role("wolf", top_k=1)[0]
    assert refreshed.id == card.id
    assert refreshed.weight > 1.0
    assert refreshed.use_count == 1
    assert refreshed.win_count == 1


def test_semantic_memory_decreases_weight_after_lost_game_and_skips_missing_ids():
    semantic = SemanticMemory(backend=InMemoryBackend())
    card = semantic.add_card("wolf", "\u4f18\u5148\u5904\u7406\u53d1\u8a00\u6e05\u6670\u7684\u5f3a\u795e\u3002")

    semantic.update_after_game("wolf", won=False, used_card_ids=[card.id, "missing"])
    refreshed = semantic.retrieve_for_role("wolf", top_k=1)[0]

    assert refreshed.weight == pytest.approx(0.95)
    assert refreshed.use_count == 1
    assert refreshed.win_count == 0


def test_memory_manager_respects_memory_config_and_collects_runtime_inputs():
    logger = EventLogger()
    manager = MemoryManager(
        logger,
        role="villager",
        player_id="player_1",
        config=MemoryConfig(working_max_rounds=2, working_max_dynamic_items=3),
        semantic_backend=InMemoryBackend(),
    )

    manager.add_public_speech(
        "\u0031\u53f7",
        "\u6211\u5148\u542c\u0034\u53f7\u600e\u4e48\u804a",
        round_number=1,
    )
    event = logger.create_event(
        EventType.VOTE_RESULT,
        round_number=1,
        phase=GamePhase.DAY_VOTING,
        message="\u0034\u53f7\u6210\u4e3a\u7126\u70b9\u7968\u578b",
        visible_to=None,
    )
    manager.add_event(event)

    context = manager.get_context_for_decision()
    assert "\u0031\u53f7\u53d1\u8a00" in context
    assert "\u0034\u53f7\u6210\u4e3a\u7126\u70b9\u7968\u578b" in context


def test_get_context_uses_working_memory_only_and_respects_semantic_top_k_zero():
    manager = MemoryManager(
        EventLogger(),
        role="villager",
        player_id="player_9",
        config=MemoryConfig(semantic_top_k=0),
        semantic_backend=InMemoryBackend(),
    )
    manager.semantic.add_card("villager", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}")
    manager.semantic.format_for_prompt = lambda role: pytest.fail("semantic context should not be injected twice")

    manager.on_game_start("villager")
    context = manager.get_context_for_decision()

    assert DESCRIPTION_ONE not in context
    assert SKILL_BODY not in context
    assert "程序记忆" in context


def test_on_game_start_and_add_decision_respect_working_memory_disabled():
    manager = MemoryManager(
        EventLogger(),
        role="villager",
        player_id="player_10",
        plan_name="bold",
        config=MemoryConfig(enable_working_memory=False),
        semantic_backend=InMemoryBackend(),
    )
    manager.semantic.add_card("villager", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}")

    manager.on_game_start("villager")
    manager.add_decision(DECISION_TEXT)

    assert manager.get_context_for_decision() == ""
    assert manager.working.get_context() == ""
    assert manager._used_card_ids == []


def test_working_memory_disabled_keeps_semantic_updates_available():
    manager = MemoryManager(
        EventLogger(),
        role="wolf",
        player_id="player_10",
        config=MemoryConfig(enable_working_memory=False),
        semantic_backend=InMemoryBackend(),
    )
    card = manager.semantic.add_card("wolf", f"描述：{DESCRIPTION_ONE}\n\n{SKILL_BODY}")

    manager.semantic.update_after_game("wolf", won=True, used_card_ids=[card.id])

    refreshed = manager.semantic.retrieve_for_role("wolf", top_k=1)[0]
    assert refreshed.weight > 1.0
    assert refreshed.use_count == 1


def test_global_memory_disabled_blocks_semantic_extraction():
    logger = EventLogger()
    logger.create_event(
        EventType.VOTE_CAST,
        round_number=1,
        phase=GamePhase.DAY_VOTING,
        message="2号投给5号",
        data={"voter_id": "player_2"},
        visible_to=["player_2"],
    )
    manager = MemoryManager(
        logger,
        role="villager",
        player_id="player_2",
        config=MemoryConfig(enabled=False, enable_episodic_memory=True),
        semantic_backend=InMemoryBackend(),
    )

    assert manager.extract_semantic_candidates(won=False) == []


def test_add_decision_respects_global_memory_disabled():
    manager = MemoryManager(
        EventLogger(),
        role="villager",
        player_id="player_11",
        config=MemoryConfig(enabled=False),
        semantic_backend=InMemoryBackend(),
    )

    manager.add_decision(DECISION_TEXT)

    assert manager.working.get_context() == ""


def test_add_event_deduplicates_same_visible_event():
    logger = EventLogger()
    manager = MemoryManager(
        logger,
        role="villager",
        player_id="player_12",
        config=MemoryConfig(),
        semantic_backend=InMemoryBackend(),
    )
    event = logger.create_event(
        EventType.VOTE_RESULT,
        round_number=1,
        phase=GamePhase.DAY_VOTING,
        message="5号得票最高",
        visible_to=["player_12"],
    )

    manager.add_event(event)
    manager.add_event(event)

    context = manager.working.get_context()
    assert context.count("5号得票最高") == 1


def test_add_event_deduplicates_visible_to_order_variants():
    logger = EventLogger()
    manager = MemoryManager(
        logger,
        role="villager",
        player_id="player_12",
        config=MemoryConfig(),
        semantic_backend=InMemoryBackend(),
    )
    first = logger.create_event(
        EventType.VOTE_RESULT,
        round_number=1,
        phase=GamePhase.DAY_VOTING,
        message="5号得票最高",
        data={"targets": ["player_5"]},
        visible_to=["player_1", "player_2"],
    )
    second = logger.create_event(
        EventType.VOTE_RESULT,
        round_number=1,
        phase=GamePhase.DAY_VOTING,
        message="5号得票最高",
        data={"targets": ["player_5"]},
        visible_to=["player_2", "player_1"],
    )

    manager.add_event(first)
    manager.add_event(second)

    assert manager.working.get_context().count("5号得票最高") == 1


def test_on_round_end_compresses_dynamic_memory():
    manager = MemoryManager(
        EventLogger(),
        role="villager",
        player_id="player_13",
        config=MemoryConfig(),
        semantic_backend=InMemoryBackend(),
    )
    manager.add_decision(DECISION_TEXT)

    manager.on_round_end(round_number=1)
    context = manager.get_context_for_decision()

    assert "【本轮记忆】" not in context
    assert "【历史回顾】" in context
    assert "做了1个决策" in context


def test_on_game_start_resets_used_cards_and_seen_events():
    logger = EventLogger()
    manager = MemoryManager(
        logger,
        role="villager",
        player_id="player_14",
        config=MemoryConfig(),
        semantic_backend=InMemoryBackend(),
    )
    manager.semantic.add_card("villager", VILLAGER_EXPERIENCE)
    event = logger.create_event(
        EventType.VOTE_RESULT,
        round_number=1,
        phase=GamePhase.DAY_VOTING,
        message="5号得票最高",
        visible_to=["player_14"],
    )
    manager.on_game_start("villager")
    manager.add_event(event)

    manager.on_game_start("villager")
    manager.add_event(event)

    assert manager.working.get_context().count("5号得票最高") == 2
    assert len(manager._used_card_ids) == 1


def test_memory_manager_extracts_semantic_candidates_by_outcome():
    logger = EventLogger()
    logger.create_event(
        EventType.VOTE_CAST,
        round_number=2,
        phase=GamePhase.DAY_VOTING,
        message="\u0032\u53f7\u6295\u7ed9\u0035\u53f7",
        data={"voter_id": "player_2"},
        visible_to=["player_2"],
    )
    logger.create_event(
        EventType.VOTE_RESULT,
        round_number=2,
        phase=GamePhase.DAY_VOTING,
        message="\u0035\u53f7\u5f97\u7968\u6700\u9ad8",
        visible_to=["player_2"],
    )
    manager = MemoryManager(
        logger,
        role="villager",
        player_id="player_2",
        config=MemoryConfig(semantic_top_k=5),
        semantic_backend=InMemoryBackend(),
    )

    won_candidates = manager.extract_semantic_candidates(won=True)
    lost_candidates = manager.extract_semantic_candidates(won=False)

    assert any("\u80dc\u5229\u7ecf\u9a8c" in candidate for candidate in won_candidates)
    assert any("\u5931\u8d25\u53cd\u601d" in candidate for candidate in lost_candidates)


def test_llm_semantic_extraction_without_endpoint_falls_back_to_rules():
    logger = EventLogger()
    logger.create_event(
        EventType.VOTE_CAST,
        round_number=2,
        phase=GamePhase.DAY_VOTING,
        message="\u0032\u53f7\u6295\u7ed9\u0035\u53f7",
        data={"voter_id": "player_2"},
        visible_to=["player_2"],
    )
    logger.create_event(
        EventType.VOTE_RESULT,
        round_number=2,
        phase=GamePhase.DAY_VOTING,
        message="\u0035\u53f7\u5f97\u7968\u6700\u9ad8",
        visible_to=["player_2"],
    )
    manager = MemoryManager(
        logger,
        role="villager",
        player_id="player_2",
        config=MemoryConfig(enable_llm_semantic_extraction=True, semantic_top_k=5),
        semantic_backend=InMemoryBackend(),
    )

    candidates = manager.extract_semantic_candidates(won=False)

    assert manager._semantic_llm() is None
    assert any("\u5931\u8d25\u53cd\u601d" in candidate for candidate in candidates)


def test_semantic_memory_merges_similar_cards():
    manager = MemoryManager(
        EventLogger(),
        role="villager",
        player_id="player_3",
        config=MemoryConfig(),
        semantic_backend=InMemoryBackend(),
    )

    first = manager.semantic.add_or_merge_card(
        "villager",
        "\u5173\u952e\u5c40\u52bf\u590d\u76d8\uff1a\u7b2c\u0031\u8f6e\u51fa\u73b0\u0035\u53f7\u5f97\u7968\u6700\u9ad8",
    )
    second = manager.semantic.add_or_merge_card(
        "villager",
        "\u5173\u952e\u5c40\u52bf\u590d\u76d8\uff1a\u7b2c\u0031\u8f6e\u51fa\u73b0\u0035\u53f7\u5f97\u7968\u6700\u9ad8\uff1b\u5e94\u7ee7\u7eed\u8ddf\u8e2a",
    )
    cards = manager.semantic.retrieve_for_role("villager", top_k=10)

    assert first.id == second.id
    assert len(cards) == 1
    assert cards[0].use_count >= 1


def test_memory_manager_extracts_and_persists_semantic_candidates_on_game_end():
    logger = EventLogger()
    logger.create_event(
        EventType.VOTE_CAST,
        round_number=3,
        phase=GamePhase.DAY_VOTING,
        message="\u0033\u53f7\u6295\u7ed9\u0036\u53f7",
        data={"voter_id": "player_3"},
        visible_to=["player_3"],
    )
    logger.create_event(
        EventType.VOTE_RESULT,
        round_number=3,
        phase=GamePhase.DAY_VOTING,
        message="\u0036\u53f7\u6210\u4e3a\u653e\u9010\u7126\u70b9",
        visible_to=["player_3"],
    )
    manager = MemoryManager(
        logger,
        role="villager",
        player_id="player_3",
        config=MemoryConfig(extract_semantic_on_game_end=True, semantic_top_k=5),
        semantic_backend=InMemoryBackend(),
    )

    manager.on_game_end(won=False)
    cards = manager.semantic.retrieve_for_role("villager", top_k=10)

    assert any("\u5931\u8d25\u53cd\u601d" in card.content for card in cards)


def test_description_extracted_from_content_line():
    content = f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}"

    description, body = SemanticMemory._split_description_line(content)

    assert description == DESCRIPTION_ONE
    assert body == SKILL_BODY
    assert SemanticMemory._extract_description(content) == DESCRIPTION_ONE


def test_description_extracted_from_when_to_use_section():
    content = (
        "# 第1轮狼队夜间刀口协商\n\n"
        "## 提取依据\n"
        "这里是对局来源，不应该作为描述。\n\n"
        "## 何时使用\n"
        "第1轮狼队私密频道，需在落刀前统一目标。\n\n"
        "## 公开行为\n"
        "先报建议刀口和理由。"
    )

    description = SemanticMemory._extract_description(content)

    assert description == "第1轮狼队私密频道，需在落刀前统一目标的情况下，使用该 skill"


def test_description_protocol_accepts_real_chinese_literals():
    content = f"描述：{DESCRIPTION_ONE}\n\n{SKILL_BODY}"

    description, body = SemanticMemory._split_description_line(content)
    rendered = SemanticMemory._render_skill_file(
        StrategyCard(role="wolf", description=DESCRIPTION_ONE, content=SKILL_BODY)
    )

    assert description == DESCRIPTION_ONE
    assert body == SKILL_BODY
    assert f"描述：{DESCRIPTION_ONE}" in rendered


def test_add_card_generates_description_and_backend_preserves_it():
    semantic = SemanticMemory(backend=InMemoryBackend())
    content = "\u7b2c\u4e00\u5929\u6ca1\u6709\u4eba\u8df3\u9884\u8a00\u5bb6\u3002"

    card = semantic.add_card("wolf", content)
    retrieved = semantic.retrieve_for_role("wolf", top_k=1)[0]

    assert card.description == DESCRIPTION_ONE
    assert retrieved.description == DESCRIPTION_ONE
    assert retrieved.content == content


def test_render_skill_file_includes_description_line():
    card = StrategyCard(role="wolf", description=DESCRIPTION_ONE, content=SKILL_BODY)

    rendered = SemanticMemory._render_skill_file(card)

    assert f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}" in rendered
    assert rendered.rstrip().endswith(SKILL_BODY)


def test_render_skill_file_preserves_post_game_skill_markdown_without_description_line():
    content = (
        "# 第1轮狼队夜间刀口协商\n\n"
        "## 何时使用\n"
        "第1轮狼队私密频道，需在落刀前统一目标。\n\n"
        "## 公开行为\n"
        "先报建议刀口和理由。"
    )
    card = StrategyCard(role="wolf", description=DESCRIPTION_ONE, content=content)

    rendered = SemanticMemory._render_skill_file(card)

    assert f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}" not in rendered
    assert "## 何时使用" in rendered


def test_format_for_prompt_shows_description_only():
    semantic = SemanticMemory(backend=InMemoryBackend())
    semantic.add_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}")

    formatted = semantic.format_for_prompt("wolf")

    assert DESCRIPTION_ONE in formatted
    assert SKILL_BODY not in formatted
    assert "\u7f6e\u4fe1\u5ea6" not in formatted
    assert "weight" not in formatted


def test_backend_retrieve_normalizes_legacy_description():
    backend = InMemoryBackend()
    card = StrategyCard(role="wolf", description="\u7b2c\u4e00\u5929\u6ca1\u6709\u4eba\u8df3\u9884\u8a00\u5bb6", content=SKILL_BODY)
    backend.store(card.id, card.__dict__)
    semantic = SemanticMemory(backend=backend)

    retrieved = semantic.retrieve_for_role("wolf", top_k=1)[0]

    assert retrieved.description == DESCRIPTION_ONE


def test_find_similar_by_llm_description():
    compressor = StubCompressor("1")
    semantic = SemanticMemory(backend=InMemoryBackend(), compressor=compressor)
    first = semantic.add_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}")
    semantic.add_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_TWO}\n\n{SKILL_BODY}")

    matched = semantic.find_similar_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n\u5176\u4ed6\u7ecf\u9a8c")

    assert matched is not None
    assert matched.id == first.id
    assert compressor.prompts
    assert DESCRIPTION_ONE in compressor.prompts[0]
    assert DESCRIPTION_TWO in compressor.prompts[0]


def test_find_similar_llm_returns_no_match():
    semantic = SemanticMemory(backend=InMemoryBackend(), compressor=StubCompressor("\u65e0"))
    semantic.add_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}")

    matched = semantic.find_similar_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_TWO}\n\n\u5176\u4ed6\u7ecf\u9a8c")

    assert matched is None


def test_find_similar_llm_returns_real_chinese_no_match_literal():
    semantic = SemanticMemory(backend=InMemoryBackend(), compressor=StubCompressor("无"))
    semantic.add_card("wolf", f"描述：{DESCRIPTION_ONE}\n\n{SKILL_BODY}")

    matched = semantic.find_similar_card("wolf", f"描述：{DESCRIPTION_TWO}\n\n其他经验")

    assert matched is None


def test_find_similar_llm_parses_dirty_number_response():
    semantic = SemanticMemory(backend=InMemoryBackend(), compressor=StubCompressor("1. 可以合并"))
    first = semantic.add_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}")
    semantic.add_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_TWO}\n\n{SKILL_BODY}")

    matched = semantic.find_similar_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n\u5176\u4ed6\u7ecf\u9a8c")

    assert matched is not None
    assert matched.id == first.id


def test_find_similar_llm_dirty_non_number_falls_back_to_sequence_matcher():
    semantic = SemanticMemory(backend=InMemoryBackend(), compressor=StubCompressor("看起来是第一条"))
    first = semantic.add_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}")

    matched = semantic.find_similar_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n\u53e6\u4e00\u7248\u7b56\u7565")

    assert matched is not None
    assert matched.id == first.id


def test_find_similar_fallback_to_sequence_matcher():
    semantic = SemanticMemory(backend=InMemoryBackend(), compressor=StubCompressor(RuntimeError("boom")))
    first = semantic.add_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}")

    matched = semantic.find_similar_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n\u53e6\u4e00\u7248\u7b56\u7565")

    assert matched is not None
    assert matched.id == first.id


def test_existing_skill_markdown_uses_when_to_use_for_prompt_description(temp_skill_root):
    wolf_dir = temp_skill_root / "wolf"
    wolf_dir.mkdir(parents=True)
    skill_path = wolf_dir / "wolf_demo.md"
    skill_path.write_text(
        "---\n"
        "skill_id: wolf_demo\n"
        "prompt_role_key: wolf\n"
        "status: active\n"
        "weight: 1.0\n"
        "win_count: 0\n"
        "use_count: 0\n"
        "---\n\n"
        "# 第1轮狼队夜间刀口协商\n\n"
        "## 提取依据\n"
        "这段不能当成触发描述。\n\n"
        "## 何时使用\n"
        "第1轮狼队私密频道，需在落刀前统一目标。\n\n"
        "## 公开行为\n"
        "先报建议刀口和理由。\n",
        encoding="utf-8",
    )
    semantic = SemanticMemory()

    card = semantic.retrieve_for_role("wolf", top_k=1)[0]
    formatted = semantic.format_for_prompt("wolf")

    assert card.description == "第1轮狼队私密频道，需在落刀前统一目标的情况下，使用该 skill"
    assert card.content.startswith("# 第1轮狼队夜间刀口协商")
    assert "提取依据" not in formatted
    assert "第1轮狼队私密频道，需在落刀前统一目标" in formatted


def test_on_game_start_injects_description_not_full_content():
    manager = MemoryManager(
        EventLogger(),
        role="wolf",
        player_id="player_4",
        config=MemoryConfig(),
        semantic_backend=InMemoryBackend(),
    )
    manager.semantic.add_card("wolf", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}")

    manager.on_game_start("wolf")
    context = manager.working.get_context()

    assert DESCRIPTION_ONE in context
    assert SKILL_BODY not in context


def test_on_game_start_keeps_procedural_when_semantic_disabled():
    manager = MemoryManager(
        EventLogger(),
        role="villager",
        player_id="player_7",
        plan_name="bold",
        config=MemoryConfig(enable_semantic_memory=False),
        semantic_backend=InMemoryBackend(),
    )
    manager.semantic.add_card("villager", f"描述：{DESCRIPTION_ONE}\n\n{SKILL_BODY}")

    manager.on_game_start("villager")
    context = manager.working.get_context()

    assert DESCRIPTION_ONE not in context
    assert "程序记忆" in context
    assert "当前采用计划：bold" in context


def test_on_game_end_respects_global_memory_disabled():
    manager = MemoryManager(
        EventLogger(),
        role="villager",
        player_id="player_8",
        config=MemoryConfig(enabled=False, extract_semantic_on_game_end=True),
        semantic_backend=InMemoryBackend(),
    )

    manager.on_game_end(won=False)

    assert manager.semantic.retrieve_for_role("villager", top_k=10) == []


def test_decay_all_noop_when_under_limit(temp_skill_root):
    semantic = SemanticMemory()
    semantic.add_card("villager", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}")
    semantic.add_card("villager", f"\u63cf\u8ff0\uff1a{DESCRIPTION_TWO}\n\n{SKILL_BODY}")

    deleted = semantic.decay_all("villager", max_count=2)

    assert deleted == 0
    assert len(list((temp_skill_root / "villager").glob("*.md"))) == 2


def test_decay_all_removes_lowest_weight(temp_skill_root):
    semantic = SemanticMemory()
    low = semantic.add_card("villager", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}")
    high = semantic.add_card("villager", f"\u63cf\u8ff0\uff1a{DESCRIPTION_TWO}\n\n{SKILL_BODY}")
    low.weight = 0.2
    high.weight = 1.4
    semantic._write_skill_card(low)
    semantic._write_skill_card(high)

    deleted = semantic.decay_all("villager", max_count=1)
    remaining = semantic.retrieve_for_role("villager", top_k=10)

    assert deleted == 1
    assert len(remaining) == 1
    assert remaining[0].description == DESCRIPTION_TWO
    assert Path(remaining[0].path).is_file()
    assert not Path(low.path).exists()


def test_decay_all_removes_lowest_weight_from_backend():
    semantic = SemanticMemory(backend=InMemoryBackend())
    low = semantic.add_card("villager", f"\u63cf\u8ff0\uff1a{DESCRIPTION_ONE}\n\n{SKILL_BODY}")
    high = semantic.add_card("villager", f"\u63cf\u8ff0\uff1a{DESCRIPTION_TWO}\n\n{SKILL_BODY}")
    low.weight = 0.2
    high.weight = 1.4
    semantic._backend.store(low.id, low.__dict__)
    semantic._backend.store(high.id, high.__dict__)

    deleted = semantic.decay_all("villager", max_count=1)
    remaining = semantic.retrieve_for_role("villager", top_k=10)

    assert deleted == 1
    assert len(remaining) == 1
    assert remaining[0].description == DESCRIPTION_TWO


def test_decay_all_considers_more_than_top_100_backend_cards():
    semantic = SemanticMemory(backend=InMemoryBackend())
    for index in range(105):
        card = semantic.add_card("villager", f"\u7b2c{index}\u8f6e\u7ecf\u9a8c\u3002")
        card.weight = float(index)
        semantic._backend.store(card.id, card.__dict__)

    deleted = semantic.decay_all("villager", max_count=8)
    remaining = semantic.retrieve_for_role("villager", top_k=200)

    assert deleted == 97
    assert len(remaining) == 8
    assert [card.weight for card in remaining] == [104.0, 103.0, 102.0, 101.0, 100.0, 99.0, 98.0, 97.0]


def test_max_cards_different_limits_for_roles():
    manager = MemoryManager(
        EventLogger(),
        role="villager",
        player_id="player_5",
        config=MemoryConfig(semantic_max_cards_good=4, semantic_max_cards_wolf=7),
        semantic_backend=InMemoryBackend(),
    )

    assert manager._max_cards_for_role("villager") == 4
    assert manager._max_cards_for_role("wolf") == 7


def test_decay_called_on_game_end():
    manager = MemoryManager(
        EventLogger(),
        role="wolf",
        player_id="player_6",
        config=MemoryConfig(semantic_max_cards_good=3, semantic_max_cards_wolf=6),
        semantic_backend=InMemoryBackend(),
    )
    calls: list[tuple[str, int]] = []
    manager.semantic.decay_all = lambda role, max_count: calls.append((role, max_count)) or 0

    manager.on_game_end(won=False)

    assert calls == [("wolf", 6)]
