"""Benchmark vote-intention fan-out at different concurrency levels."""

from __future__ import annotations

import sys
import json
import time
import random
from typing import Any
import asyncio
from pathlib import Path
import argparse
from datetime import datetime
from dataclasses import asdict, is_dataclass

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_PATH = _PROJECT_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.support.utils import load_config
from llm_werewolf.interface.cli.runtime.bootstrap import prepare_game_roster, wire_agentscope_after_setup
from llm_werewolf.strategy.voting.intention import VoteIntentionAnchor
from llm_werewolf.evaluation.core.time_analysis import compare_roundtable_parallelism


def _load_api_key(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").strip()
    if "=" in raw:
        return raw.split("=", 1)[1].strip().strip("\"'")
    return raw.strip().strip("\"'")


def _intention_to_dict(entry: Any) -> dict[str, Any]:
    if hasattr(entry, "model_dump"):
        return entry.model_dump(mode="json")
    if is_dataclass(entry):
        return asdict(entry)
    return dict(entry)


def _build_engine(config_path: Path, concurrency: int, seed: int) -> GameEngine:
    random.seed(seed)
    players_config = load_config(config_path)
    players_config = players_config.model_copy(update={"vote_intention_concurrency": concurrency})
    players, roles, game_config = prepare_game_roster(players_config)
    engine = GameEngine(game_config, language=players_config.language)
    engine.setup_game(players=players, roles=roles)
    wire_agentscope_after_setup(engine, players_config)
    if engine.game_state is None:
        msg = "GameEngine.setup_game did not initialize game_state"
        raise RuntimeError(msg)
    engine.game_state.round_number = 1
    return engine


async def _run_once(config_path: Path, concurrency: int, seed: int) -> dict[str, Any]:
    engine = _build_engine(config_path, concurrency, seed)
    assert engine.game_state is not None
    alive = engine.game_state.get_alive_players()

    started_at = datetime.now()
    started = time.perf_counter()
    intentions = await engine.information_hub._collect_vote_intentions(
        alive,
        anchor=VoteIntentionAnchor.INITIAL,
        context_builder=engine._build_discussion_context,
        phase="benchmark_vote_intention",
        round_number=1,
    )
    duration_seconds = time.perf_counter() - started
    finished_at = datetime.now()
    return {
        "concurrency": concurrency,
        "seed": seed,
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "duration_seconds": duration_seconds,
        "player_count": len(alive),
        "intention_count": len(intentions),
        "intentions": {
            player_id: _intention_to_dict(entry) for player_id, entry in intentions.items()
        },
    }


async def _main_async(args: argparse.Namespace) -> None:
    if args.api_key_file:
        import os

        if not os.getenv(args.api_key_env):
            os.environ[args.api_key_env] = _load_api_key(args.api_key_file)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    runs = []
    for concurrency in args.concurrency:
        print(f"[benchmark] running concurrency={concurrency}")
        result = await _run_once(args.config, concurrency, args.seed)
        runs.append(result)
        out_path = args.output_dir / f"vote_intentions-c{concurrency}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"[benchmark] concurrency={concurrency} "
            f"duration={result['duration_seconds']:.2f}s "
            f"intentions={result['intention_count']}"
        )

    theoretical = None
    if len(args.concurrency) >= 2:
        seconds_per_http = args.seconds_per_http
        theoretical = compare_roundtable_parallelism(
            num_players=runs[0]["player_count"],
            before_concurrency=args.concurrency[0],
            after_concurrency=args.concurrency[-1],
            seconds_per_http=seconds_per_http,
            http_round_trips_per_decision=args.http_round_trips_per_decision,
        )
    summary = {
        "config": str(args.config),
        "seed": args.seed,
        "runs": [
            {
                "concurrency": run["concurrency"],
                "duration_seconds": run["duration_seconds"],
                "intention_count": run["intention_count"],
            }
            for run in runs
        ],
    }
    if len(runs) >= 2:
        before = runs[0]["duration_seconds"]
        after = runs[-1]["duration_seconds"]
        summary["measured"] = {
            "before_concurrency": runs[0]["concurrency"],
            "after_concurrency": runs[-1]["concurrency"],
            "saved_seconds": before - after,
            "speedup": before / after if after else None,
            "saved_percent": ((before - after) / before * 100) if before else 0,
        }
    if theoretical:
        summary["theoretical_roundtable"] = {
            "before_seconds": theoretical.before.wall_seconds,
            "after_seconds": theoretical.after.wall_seconds,
            "saved_seconds": theoretical.saved_seconds,
            "speedup": theoretical.speedup,
            "saved_percent": theoretical.saved_percent,
        }

    summary_path = args.output_dir / "benchmark_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[benchmark] summary -> {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/llm-6p-doubao.yaml"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("runs") / "vote-intention-parallelism-benchmark"
    )
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 6])
    parser.add_argument("--seed", type=int, default=20260528)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--api-key-env", default="ARK_API_KEY")
    parser.add_argument("--seconds-per-http", type=float, default=10.0)
    parser.add_argument("--http-round-trips-per-decision", type=int, default=2)
    args = parser.parse_args()
    asyncio.run(_main_async(args))


if __name__ == "__main__":
    main()
