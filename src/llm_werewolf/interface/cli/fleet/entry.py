"""`werewolf-fleet` CLI: `up` launches a multi-stack fleet; `batch` distributes games."""

from __future__ import annotations

import sys
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime
import contextlib

import fire

from llm_werewolf.interface.cli.fleet.batch import run_batch, summarize
from llm_werewolf.interface.cli.fleet.planner import InstanceSpec, plan_batch, plan_fleet
from llm_werewolf.interface.cli.fleet.supervisor import ProcessSupervisor


def build_log_dir(*, root: Path, stamp: str) -> Path:
    return Path(root) / "artifacts" / "fleet" / stamp


def _print_table(specs: list[InstanceSpec]) -> None:
    print("\n  idx | backend                  | frontend")
    print("  ----+--------------------------+-------------------------")
    for s in specs:
        fe = s.frontend_url or "(none)"
        print(f"  {s.idx:>3} | {s.backend_url:<24} | {fe}")
    print()


def up(
    backends: int = 2,
    frontends: int | None = None,
    be_base: int = 8010,
    fe_base: int = 5173,
    require_llm: bool = False,
    health_timeout: float = 60.0,
) -> None:
    """Launch ``backends`` backends + ``frontends`` frontends (default: == backends)."""
    if frontends is None:
        frontends = backends
    specs = plan_fleet(
        backends=backends,
        frontends=frontends,
        be_base=be_base,
        fe_base=fe_base,
        require_llm=require_llm,
    )
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = build_log_dir(root=Path.cwd(), stamp=stamp)
    sup = ProcessSupervisor(specs, log_dir=log_dir)
    print(f"[fleet] starting {backends} backend(s), {frontends} frontend(s); logs -> {log_dir}")
    sup.start_all()
    try:
        if sup.wait_healthy(timeout=health_timeout):
            print("[fleet] all backends healthy.")
        else:
            print("[fleet] WARNING: some backends did not become healthy; see logs.")
        _print_table(specs)
        print("[fleet] Ctrl-C to stop all processes.")
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[fleet] shutting down...")
    finally:
        sup.teardown()
        print("[fleet] all processes terminated.")


def batch(
    config: str = "demo-6",
    count: int = 4,
    be_base: int = 8010,
    backends: int = 2,
    concurrency: int = 2,
    stagger: float = 1.0,
) -> None:
    """Distribute ``count`` games across already-running backends and poll to terminal.

    Targets backends at ``be_base + i`` for i in range(``backends``). Start a fleet first
    with ``werewolf-fleet up --backends N`` (or point at any running backends).
    """
    backend_urls = [f"http://127.0.0.1:{be_base + i}" for i in range(backends)]
    items = plan_batch(count=count, backend_urls=backend_urls, stagger=stagger)
    print(f"[batch] {count} games across {backends} backend(s), concurrency={concurrency}")
    results = asyncio.run(run_batch(items, config_id=config, concurrency=concurrency))
    summary = summarize(results)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = build_log_dir(root=Path.cwd(), stamp=stamp)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "batch_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[batch] done: {summary['by_status']}  ->  {out}")


def entry() -> None:
    # Windows: keep zh/emoji output UTF-8.
    if hasattr(sys.stdout, "reconfigure"):
        with contextlib.suppress(Exception):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fire.Fire({"up": up, "batch": batch})


if __name__ == "__main__":
    entry()
