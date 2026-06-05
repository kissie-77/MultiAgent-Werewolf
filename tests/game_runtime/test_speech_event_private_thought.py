def test_log_public_speech_includes_private_thought():
    from types import SimpleNamespace
    from llm_werewolf.game_runtime.engine.day_phase import DayPhaseMixin
    from llm_werewolf.strategy.contracts.decisions import SpeechDecision

    captured = {}

    class _Engine(DayPhaseMixin):
        def __init__(self):
            self.game_state = object()  # truthy
            self.locale = SimpleNamespace(get=lambda *a, **k: "msg")

        def _log_event(self, event_type, message, data=None, visible_to=None):
            captured["data"] = data

    speaker = SimpleNamespace(player_id="player_3", name="P3")
    decision = SpeechDecision.model_construct(public_speech="我怀疑5号", private_thought="其实更怕3号")
    _Engine()._log_public_speech(speaker, decision)

    assert captured["data"]["speech"] == "我怀疑5号"
    assert captured["data"]["private_thought"] == "其实更怕3号"
