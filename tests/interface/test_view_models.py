def test_view_response_roundtrip():
    from llm_werewolf.interface.api.models.view import (
        ViewResponse, ViewSnapshot, ViewPlayer, ViewEvent,
    )

    resp = ViewResponse(
        cursor=2,
        status="running",
        snapshot=ViewSnapshot(
            day=1, phase="day_discussion", phase_label="第1天 · 讨论",
            winner=None, alive_count=6, dead_count=0, sheriff_seat=None,
            players=[ViewPlayer(seat=1, name="P1", role="预言家", camp="villager",
                                is_alive=True, is_sheriff=False, model="deepseek-chat")],
        ),
        events=[ViewEvent(seq=1, type="speech", round=1, phase="day_discussion",
                          text="我怀疑5号", reveal="now", visibility="public")],
    )
    dumped = resp.model_dump()
    assert dumped["cursor"] == 2
    assert dumped["snapshot"]["players"][0]["role"] == "预言家"
    assert dumped["events"][0]["type"] == "speech"
    # spec §5.2: the wire field is `round`, not the legacy `day`.
    assert dumped["events"][0]["round"] == 1
    assert "day" not in dumped["events"][0]
