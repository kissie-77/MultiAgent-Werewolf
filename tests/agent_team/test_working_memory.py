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
