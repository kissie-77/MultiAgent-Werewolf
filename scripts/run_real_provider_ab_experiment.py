"""Run real provider A/B games for vote-intention concurrency.

This script is intentionally narrow: it runs full games, measures total wall
time plus vote-intention collection time, and writes artifacts for comparison.
It does not print API keys.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
import time
import traceback
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.serialization import serialize_game_state
from llm_werewolf.game_runtime.utils import load_config
from llm_werewolf.interface.bootstrap import (
    prepare_game_roster,
    wire_agentscope_after_setup,
)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _event_to_dict(event: Any) -> dict[str, Any]:
    return {
        "event_type": event.event_type.value,
        "timestamp": event.timestamp.isoformat(),
        "round_number": event.round_number,
        "phase": event.phase.value if hasattr(event.phase, "value") else str(event.phase),
        "message": event.message,
        "data": _jsonable(event.data),
        "visible_to": event.visible_to,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _install_vote_intention_timer(engine: GameEngine) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    original = engine.information_hub._collect_vote_intentions

    async def timed_collect(observers: list[Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            result = await original(observers, *args, **kwargs)
            ok = True
            error = None
            return result
        except Exception as exc:
            ok = False
            error = repr(exc)
            raise
        finally:
            elapsed = time.perf_counter() - started
            records.append(
                {
                    "duration_seconds": elapsed,
                    "observer_count": len(observers),
                    "result_count": len(result) if ok else 0,
                    "anchor": str(kwargs.get("anchor", "")),
                    "phase": kwargs.get("phase", ""),
                    "round_number": kwargs.get("round_number", 0),
                    "ok": ok,
                    "error": error,
                }
            )

    engine.information_hub._collect_vote_intentions = timed_collect  # type: ignore[method-assign]
    return records


async def _run_one(
    *,
    label: str,
    config_path: Path,
    concurrency: int,
    seed: int,
    output_dir: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    run_id = f"{label}-c{concurrency}"
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "run.log"
    logging.basicConfig(
        filename=log_path,
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )

    started_at = datetime.now().isoformat(timespec="seconds")
    started = time.perf_counter()
    summary: dict[str, Any] = {
        "run_id": run_id,
        "label": label,
        "config": str(config_path),
        "concurrency": concurrency,
        "seed": seed,
        "started_at": started_at,
        "status": "running",
    }
    vote_timing: list[dict[str, Any]] = []
    engine: GameEngine | None = None

    async def play() -> str:
        nonlocal engine, vote_timing
        random.seed(seed)
        players_config = load_config(config_path)
        players_config = players_config.model_copy(
            update={"vote_intention_concurrency": concurrency}
        )
        players, roles, game_config = prepare_game_roster(players_config)
        engine = GameEngine(game_config, language=players_config.language)
        engine.on_event = lambda event: None
        engine.setup_game(players=players, roles=roles)
        wire_agentscope_after_setup(engine, players_config)
        vote_timing = _install_vote_intention_timer(engine)
        return await engine.play_game()

    try:
        result_text = await asyncio.wait_for(play(), timeout=timeout_seconds)
        status = "completed"
        error = None
    except TimeoutError:
        result_text = ""
        status = "timeout"
        error = f"timed out after {timeout_seconds}s"
    except Exception as exc:
        result_text = ""
        status = "failed"
        error = repr(exc)
        (run_dir / "traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")

    duration = time.perf_counter() - started
    events = engine.event_logger.events if engine is not None else []
    state = engine.game_state if engine is not None else None
    winner = getattr(state, "winner", None) if state is not None else None
    rounds = getattr(state, "round_number", None) if state is not None else None

    with (run_dir / "events.jsonl").open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(_event_to_dict(event), ensure_ascii=False) + "\n")

    if state is not None:
        _write_json(run_dir / "final_snapshot.json", serialize_game_state(state))
        tracker = getattr(state, "vote_intention_tracker", None)
        if tracker is not None:
            tracker.save_jsonl(run_dir / "vote_intentions.jsonl")

    total_vote_time = sum(item["duration_seconds"] for item in vote_timing)
    summary.update(
        {
            "status": status,
            "error": error,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "duration_seconds": duration,
            "result_text": result_text,
            "winner": winner,
            "rounds_played": rounds,
            "event_count": len(events),
            "vote_intention_batch_count": len(vote_timing),
            "vote_intention_total_seconds": total_vote_time,
            "vote_intention_max_batch_seconds": max(
                [item["duration_seconds"] for item in vote_timing],
                default=0.0,
            ),
            "vote_intention_result_count": sum(item["result_count"] for item in vote_timing),
        }
    )
    _write_json(run_dir / "vote_intention_timing.json", vote_timing)
    _write_json(run_dir / "summary.json", summary)
    print(
        f"[done] {run_id} status={status} total={duration:.2f}s "
        f"vote_intentions={total_vote_time:.2f}s batches={len(vote_timing)}"
    )
    return summary


def _parse_case(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("case must be label=path")
    label, path = raw.split("=", 1)
    return label.strip(), Path(path.strip())


def _comparison(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    def gain(field: str) -> dict[str, float | None]:
        b = float(before.get(field) or 0.0)
        a = float(after.get(field) or 0.0)
        if b <= 0 or a <= 0:
            return {"before": b, "after": a, "saved": None, "speedup": None}
        return {
            "before": b,
            "after": a,
            "saved": b - a,
            "speedup": b / a,
            "saved_percent": ((b - a) / b) * 100,
        }

    return {
        "label": before["label"],
        "total_duration": gain("duration_seconds"),
        "vote_intention_duration": gain("vote_intention_total_seconds"),
        "before_status": before["status"],
        "after_status": after["status"],
        "before_winner": before.get("winner"),
        "after_winner": after.get("winner"),
        "before_rounds": before.get("rounds_played"),
        "after_rounds": after.get("rounds_played"),
    }


async def _main_async(args: argparse.Namespace) -> None:
    if args.env_file:
        load_dotenv(args.env_file, override=False)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for label, config_path in args.case:
        for concurrency in args.concurrency:
            print(f"[run] {label} c{concurrency} config={config_path}")
            result = await _run_one(
                label=label,
                config_path=config_path,
                concurrency=concurrency,
                seed=args.seed,
                output_dir=args.output_dir,
                timeout_seconds=args.timeout_seconds,
            )
            results.append(result)

    comparisons = []
    for label, _config_path in args.case:
        by_c = {item["concurrency"]: item for item in results if item["label"] == label}
        if 1 in by_c and 6 in by_c:
            comparisons.append(_comparison(by_c[1], by_c[6]))

    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "seed": args.seed,
        "concurrency": args.concurrency,
        "results": results,
        "comparisons": comparisons,
    }
    _write_json(args.output_dir / "summary.json", payload)
    print(f"[summary] {args.output_dir / 'summary.json'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case",
        action="append",
        required=True,
        type=_parse_case,
        help="Provider case in label=path form.",
    )
    parser.add_argument(
        "--concurrency",
        nargs="+",
        type=int,
        default=[1, 6],
    )
    parser.add_argument("--seed", type=int, default=20260528)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs")
        / f"real-provider-ab-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
    )
    asyncio.run(_main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
