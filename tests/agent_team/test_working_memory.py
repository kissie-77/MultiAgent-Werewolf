from llm_werewolf.agent_team.memory.working_memory import WorkingMemory


def test_working_memory_tracks_dynamic_and_summaries():
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


def test_working_memory_limits_dynamic_items():
    memory = WorkingMemory(max_dynamic_items=2)

    memory.add_dynamic("a", tag="event")
    memory.add_dynamic("b", tag="event")
    memory.add_dynamic("c", tag="event")

    context = memory.get_context()
    assert "- a" not in context
    assert "- b" in context
    assert "- c" in context


def test_dynamic_overflow_keeps_high_priority():
    memory = WorkingMemory(max_dynamic_items=2)

    memory.add_dynamic("普通发言", tag="speech", priority=1)
    memory.add_dynamic("验出狼人", tag="event", priority=2)
    memory.add_dynamic("又一条普通", tag="speech", priority=1)

    context = memory.get_context()
    assert "验出狼人" in context
    assert "又一条普通" in context
    assert "普通发言" not in context


def test_persistent_area_trims_by_char_limit():
    memory = WorkingMemory(max_persistent_chars=20)

    memory.add_persistent("短内容", tag="identity", priority=3)
    memory.add_persistent("这是一段比较长的常驻记忆内容", tag="semantic", priority=2)
    memory.add_persistent("又一条", tag="semantic", priority=1)

    total = sum(len(item.content) for item in memory._persistent)
    assert total <= 20


def test_persistent_area_keeps_at_least_one():
    memory = WorkingMemory(max_persistent_chars=5)

    memory.add_persistent("超出限制的长内容非常多", tag="identity", priority=3)

    assert len(memory._persistent) == 1
