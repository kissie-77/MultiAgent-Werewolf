from typing import NoReturn

from llm_werewolf.agent_team.memory.working_memory import WorkingMemory


class FailingCompressor:
    def compress(self, items) -> NoReturn:
        raise RuntimeError("compression service unavailable")


def test_working_memory_tracks_dynamic_and_summaries() -> None:
    memory = WorkingMemory(max_rounds=3, max_dynamic_items=5)

    memory.add_dynamic("我投了3号", tag="decision")
    memory.add_dynamic("听到2号强跳预言家", tag="speech")

    context = memory.get_context()
    assert "【本轮记忆】" in context
    assert "我投了3号" in context

    summary = memory.end_round()
    assert "第1轮" in summary
    assert "做了1个决策" in summary
    assert "听到1段发言" in summary
    assert "【历史回顾】" in memory.get_context()


def test_working_memory_limits_dynamic_items() -> None:
    memory = WorkingMemory(max_dynamic_items=2)

    memory.add_dynamic("a", tag="event")
    memory.add_dynamic("b", tag="event")
    memory.add_dynamic("c", tag="event")

    context = memory.get_context()
    assert "- a" not in context
    assert "- b" in context
    assert "- c" in context


def test_dynamic_overflow_keeps_high_priority() -> None:
    memory = WorkingMemory(max_dynamic_items=2)

    memory.add_dynamic("普通发言", tag="speech", priority=1)
    memory.add_dynamic("验出狼人", tag="event", priority=2)
    memory.add_dynamic("又一条普通", tag="speech", priority=1)

    context = memory.get_context()
    assert "验出狼人" in context
    assert "又一条普通" in context
    assert "普通发言" not in context


def test_persistent_area_trims_by_char_limit() -> None:
    memory = WorkingMemory(max_persistent_chars=20)

    memory.add_persistent("短内容", tag="identity", priority=3)
    memory.add_persistent("这是一段比较长的常驻记忆内容", tag="semantic", priority=2)
    memory.add_persistent("又一条", tag="semantic", priority=1)

    total = sum(len(item.content) for item in memory._persistent)
    assert total <= 20


def test_persistent_area_keeps_at_least_one() -> None:
    memory = WorkingMemory(max_persistent_chars=5)

    memory.add_persistent("超出限制的长内容非常多", tag="identity", priority=3)

    assert len(memory._persistent) == 1


def test_protected_persistent_not_evicted() -> None:
    memory = WorkingMemory(max_persistent_chars=40)
    memory.upsert_persistent("【当前信念矩阵】一阶狼概率内容占位" * 2, tag="belief", priority=10)
    memory.add_persistent("skill-a", tag="semantic", priority=3)
    memory.add_persistent("skill-b", tag="semantic", priority=2)
    memory.add_persistent("skill-c", tag="semantic", priority=1)

    assert any(item.tag == "belief" for item in memory._persistent)


def test_upsert_persistent_replaces_same_tag() -> None:
    memory = WorkingMemory()
    memory.upsert_persistent("belief-v1", tag="belief", priority=10)
    memory.upsert_persistent("belief-v2", tag="belief", priority=10)

    belief_items = [item for item in memory._persistent if item.tag == "belief"]
    assert len(belief_items) == 1
    assert belief_items[0].content == "belief-v2"


def test_get_context_groups_belief_separately() -> None:
    memory = WorkingMemory()
    memory.upsert_persistent("矩阵摘要", tag="belief", priority=10)
    memory.add_persistent("程序记忆", tag="procedural", priority=3)

    context = memory.get_context()
    assert "【内心信念】" in context
    assert "矩阵摘要" in context
    assert "【稳定经验】" in context
    assert "程序记忆" in context


def test_get_context_groups_role_pool_as_fixed_game_info() -> None:
    memory = WorkingMemory()
    memory.upsert_persistent("【本局角色池】Werewolf x2, Villager x2", tag="role_pool", priority=8)
    memory.add_persistent("程序记忆", tag="procedural", priority=3)

    context = memory.get_context()

    assert "【本局固定信息】" in context
    assert "【本局角色池】Werewolf x2, Villager x2" in context
    assert "【稳定经验】" in context
    assert "程序记忆" in context
    stable_block = context.split("【稳定经验】", 1)[1]
    assert "【本局角色池】" not in stable_block


def test_get_context_can_exclude_belief_blocks() -> None:
    memory = WorkingMemory()
    memory.upsert_persistent("矩阵摘要", tag="belief", priority=10)
    memory.upsert_persistent("信念规则", tag="belief_rules", priority=10)
    memory.add_persistent("程序记忆", tag="procedural", priority=3)

    context = memory.get_context(include_belief=False)

    assert "【内心信念】" not in context
    assert "矩阵摘要" not in context
    assert "信念规则" not in context
    assert "【稳定经验】" in context
    assert "程序记忆" in context


def test_working_memory_falls_back_when_compressor_raises() -> None:
    memory = WorkingMemory(compressor=FailingCompressor())
    memory.add_dynamic("我投了3号", tag="decision")
    memory.add_dynamic("听到2号强跳预言家", tag="speech")

    summary = memory.end_round()

    assert "做了1个决策" in summary
    assert "听到1段发言" in summary
    assert "【历史回顾】" in memory.get_context()
