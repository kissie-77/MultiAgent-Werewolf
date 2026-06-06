import sys
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location


def _load_script_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "probe_provider_rate_limits.py"
    spec = spec_from_file_location("probe_provider_rate_limits", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeHTTPError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def test_classify_error_detects_rate_limit_and_quota() -> None:
    module = _load_script_module()

    assert module._classify_error(FakeHTTPError("Too Many Requests", 429)) == "rate_limit"
    assert module._classify_error(FakeHTTPError("quota exceeded")) == "quota"
    assert module._classify_error(TimeoutError("request timeout")) == "timeout"
    assert module._classify_error(FakeHTTPError("401 unauthorized", 401)) == "auth"


def test_summarize_level_calculates_latency_and_soft_limit() -> None:
    module = _load_script_module()
    results = [
        module.ProbeResult(ok=True, duration_seconds=1.0),
        module.ProbeResult(ok=True, duration_seconds=2.0),
        module.ProbeResult(ok=True, duration_seconds=10.0),
        module.ProbeResult(ok=False, duration_seconds=0.5, error_type="rate_limit"),
    ]

    summary = module._summarize_level(
        provider="doubao",
        model="model-a",
        concurrency=4,
        results=results,
        baseline_p95_seconds=2.0,
    )

    assert summary["provider"] == "doubao"
    assert summary["success"] == 3
    assert summary["total"] == 4
    assert summary["errors_rate_limit"] == 1
    assert summary["avg_seconds"] == 4.333
    assert summary["p95_seconds"] == 10.0
    assert summary["soft_limited"] is True
