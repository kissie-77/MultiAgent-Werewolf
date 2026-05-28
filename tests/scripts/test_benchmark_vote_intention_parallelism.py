from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from llm_werewolf.strategy.vote_intention import VoteIntentionEntry


def _load_script_module():
    script_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "benchmark_vote_intention_parallelism.py"
    )
    spec = spec_from_file_location("benchmark_vote_intention_parallelism", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_intention_to_dict_serializes_dataclass_entries() -> None:
    module = _load_script_module()
    entry = VoteIntentionEntry(
        player_id="p1",
        player_name="P1",
        seat=0,
        target_id=None,
        target_name=None,
        reason="test",
    )

    assert module._intention_to_dict(entry) == {
        "player_id": "p1",
        "player_name": "P1",
        "seat": 0,
        "target_id": None,
        "target_name": None,
        "reason": "test",
    }
