from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location


def _load_script_module():
    script_path = (
        Path(__file__).resolve().parents[2] / "scripts" / "run_real_provider_ab_experiment.py"
    )
    spec = spec_from_file_location("run_real_provider_ab_experiment", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_comparison_calculates_total_and_vote_intention_speedups() -> None:
    module = _load_script_module()

    comparison = module._comparison(
        {
            "label": "deepseek",
            "status": "completed",
            "winner": "werewolf",
            "rounds_played": 1,
            "duration_seconds": 100.0,
            "vote_intention_total_seconds": 40.0,
        },
        {
            "label": "deepseek",
            "status": "completed",
            "winner": "werewolf",
            "rounds_played": 1,
            "duration_seconds": 25.0,
            "vote_intention_total_seconds": 5.0,
        },
    )

    assert comparison["total_duration"]["saved"] == 75.0
    assert comparison["total_duration"]["speedup"] == 4.0
    assert comparison["total_duration"]["saved_percent"] == 75.0
    assert comparison["vote_intention_duration"]["saved"] == 35.0
    assert comparison["vote_intention_duration"]["speedup"] == 8.0
    assert comparison["before_winner"] == "werewolf"
    assert comparison["after_winner"] == "werewolf"
