"""Pure planning helpers for fleet orchestration (no I/O, no processes)."""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class InstanceSpec:
    """One backend (and optionally one paired frontend) in the fleet."""

    idx: int
    tag: str
    be_port: int
    fe_port: int | None
    be_env: dict[str, str]
    fe_env: dict[str, str] | None
    backend_url: str
    frontend_url: str | None


def plan_fleet(
    *,
    backends: int,
    frontends: int,
    be_base: int,
    fe_base: int,
    require_llm: bool,
) -> list[InstanceSpec]:
    """Plan ``backends`` backend instances and the first ``frontends`` paired frontends.

    Backend i listens on ``be_base + i`` with ``WEREWOLF_INSTANCE_TAG=i{i}``. Frontend i
    (when i < frontends) listens on ``fe_base + i`` and proxies ``/api`` to backend i.
    """
    if backends < 1:
        raise ValueError("backends must be >= 1")
    if frontends < 0 or frontends > backends:
        raise ValueError("frontends must be between 0 and backends")

    specs: list[InstanceSpec] = []
    for idx in range(backends):
        tag = f"i{idx}"
        be_port = be_base + idx
        be_env = {
            "WEREWOLF_INSTANCE_TAG": tag,
            "OBS_READY_REQUIRE_LLM": "1" if require_llm else "0",
        }
        has_fe = idx < frontends
        fe_port = fe_base + idx if has_fe else None
        fe_env = (
            {"VITE_API_PROXY": f"http://127.0.0.1:{be_port}"} if has_fe else None
        )
        specs.append(
            InstanceSpec(
                idx=idx,
                tag=tag,
                be_port=be_port,
                fe_port=fe_port,
                be_env=be_env,
                fe_env=fe_env,
                backend_url=f"http://127.0.0.1:{be_port}",
                frontend_url=f"http://127.0.0.1:{fe_port}" if has_fe else None,
            )
        )
    return specs


def build_backend_command(spec: InstanceSpec) -> list[str]:
    """uvicorn launch command for one backend (current Python interpreter)."""
    return [
        sys.executable,
        "-m",
        "llm_werewolf.interface.api.app",
        "--host",
        "127.0.0.1",
        "--port",
        str(spec.be_port),
    ]


def build_frontend_command(spec: InstanceSpec) -> list[str]:
    """Vite dev launch command for one frontend (run with cwd=frontend)."""
    if spec.fe_port is None:
        raise ValueError(f"instance {spec.idx} has no frontend")
    return ["npm", "run", "dev", "--", "--port", str(spec.fe_port), "--strictPort"]


@dataclass(frozen=True)
class BatchItem:
    """One game to start during a batch run."""

    seq: int
    backend_url: str
    delay_s: float


def plan_batch(
    *,
    count: int,
    backend_urls: list[str],
    stagger: float,
) -> list[BatchItem]:
    """Round-robin ``count`` games across ``backend_urls`` with a per-item start delay.

    Item ``seq`` targets ``backend_urls[seq % n]`` and is delayed ``seq * stagger``
    seconds from t0 (concurrency is enforced separately at execution time).
    """
    if count < 1:
        raise ValueError("count must be >= 1")
    if not backend_urls:
        raise ValueError("backend_urls must be non-empty")
    if stagger < 0:
        raise ValueError("stagger must be >= 0")
    n = len(backend_urls)
    return [
        BatchItem(seq=seq, backend_url=backend_urls[seq % n], delay_s=seq * stagger)
        for seq in range(count)
    ]
