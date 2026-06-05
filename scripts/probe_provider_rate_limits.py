"""Probe OpenAI-compatible provider rate limits with bounded concurrency.

The probe intentionally sends tiny chat-completion requests outside the game
loop so rate-limit signals are not mixed with Werewolf branching behavior.
It never prints API keys.
"""

from __future__ import annotations

import os
import sys
import json
import math
import time
from typing import TYPE_CHECKING, Any
import asyncio
from pathlib import Path
import argparse
from datetime import datetime
from dataclasses import asdict, dataclass

from dotenv import load_dotenv
from openai import AsyncOpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from llm_werewolf.game_runtime.support.utils import load_config

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.config import PlayerConfig


@dataclass
class ProbeResult:
    ok: bool
    duration_seconds: float
    error_type: str | None = None
    error_message: str | None = None
    status_code: int | None = None


def _classify_error(exc: BaseException) -> str:
    status_code = getattr(exc, "status_code", None)
    message = str(exc).lower()

    if status_code == 429 or "too many requests" in message or "rate limit" in message:
        return "rate_limit"
    if any(token in message for token in ("quota", "balance", "insufficient", "billing")):
        return "quota"
    if isinstance(exc, TimeoutError) or "timeout" in message or "timed out" in message:
        return "timeout"
    if status_code in {401, 403} or any(
        token in message for token in ("unauthorized", "forbidden", "api key")
    ):
        return "auth"
    if any(token in message for token in ("connect", "connection", "network", "read error")):
        return "network"
    return "other"


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil((percentile / 100.0) * len(ordered)) - 1)
    return ordered[min(index, len(ordered) - 1)]


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 3)


def _summarize_level(
    *,
    provider: str,
    model: str,
    concurrency: int,
    results: list[ProbeResult],
    baseline_p95_seconds: float | None = None,
    wall_seconds: float | None = None,
) -> dict[str, Any]:
    ok_durations = [result.duration_seconds for result in results if result.ok]
    success = len(ok_durations)
    total = len(results)
    error_counts: dict[str, int] = {}
    for result in results:
        if result.ok:
            continue
        key = result.error_type or "other"
        error_counts[key] = error_counts.get(key, 0) + 1

    p95 = _percentile(ok_durations, 95)
    avg = sum(ok_durations) / success if success else None
    effective_wall = wall_seconds or (max(ok_durations) if ok_durations else None)
    throughput = (success / effective_wall) if effective_wall and effective_wall > 0 else None
    success_rate = (success / total) if total else 0.0
    soft_limited = False
    if baseline_p95_seconds and p95 is not None and p95 > baseline_p95_seconds * 3:
        soft_limited = True
    if error_counts.get("rate_limit", 0) > 0 or success_rate < 0.95:
        soft_limited = True

    return {
        "provider": provider,
        "model": model,
        "concurrency": concurrency,
        "success": success,
        "total": total,
        "success_rate": _round(success_rate),
        "errors_rate_limit": error_counts.get("rate_limit", 0),
        "errors_quota": error_counts.get("quota", 0),
        "errors_timeout": error_counts.get("timeout", 0),
        "errors_auth": error_counts.get("auth", 0),
        "errors_network": error_counts.get("network", 0),
        "errors_other": error_counts.get("other", 0),
        "avg_seconds": _round(avg),
        "p95_seconds": _round(p95),
        "max_seconds": _round(max(ok_durations) if ok_durations else None),
        "wall_seconds": _round(effective_wall),
        "throughput_rps": _round(throughput),
        "soft_limited": soft_limited,
    }


def _provider_from_config(
    config_path: Path, provider_label: str | None
) -> tuple[str, PlayerConfig]:
    players_config = load_config(config_path)
    for player in players_config.players:
        if player.model in {"demo", "human"}:
            continue
        if not player.base_url or not player.api_key_env:
            continue
        return provider_label or config_path.stem, player
    msg = f"No API-backed player found in {config_path}"
    raise ValueError(msg)


async def _run_request(
    *, client: AsyncOpenAI, model: str, prompt: str, max_tokens: int, request_timeout: float
) -> ProbeResult:
    started = time.perf_counter()
    try:
        await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0,
            ),
            timeout=request_timeout,
        )
        return ProbeResult(ok=True, duration_seconds=time.perf_counter() - started)
    except BaseException as exc:
        return ProbeResult(
            ok=False,
            duration_seconds=time.perf_counter() - started,
            error_type=_classify_error(exc),
            error_message=str(exc)[:500],
            status_code=getattr(exc, "status_code", None),
        )


async def _run_level(
    *,
    client: AsyncOpenAI,
    provider: str,
    model: str,
    concurrency: int,
    requests_per_level: int,
    prompt: str,
    max_tokens: int,
    request_timeout: float,
    baseline_p95_seconds: float | None,
) -> tuple[dict[str, Any], list[ProbeResult]]:
    semaphore = asyncio.Semaphore(concurrency)

    async def one_request() -> ProbeResult:
        async with semaphore:
            return await _run_request(
                client=client,
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                request_timeout=request_timeout,
            )

    started = time.perf_counter()
    results = await asyncio.gather(*(one_request() for _ in range(requests_per_level)))
    wall_seconds = time.perf_counter() - started
    summary = _summarize_level(
        provider=provider,
        model=model,
        concurrency=concurrency,
        results=results,
        baseline_p95_seconds=baseline_p95_seconds,
        wall_seconds=wall_seconds,
    )
    return summary, results


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def _main_async(args: argparse.Namespace) -> None:
    if args.env_file:
        load_dotenv(args.env_file, override=False)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    provider, player = _provider_from_config(args.config, args.provider_label)
    api_key = os.getenv(player.api_key_env or "")
    if not api_key:
        msg = f"API key not found in environment variable {player.api_key_env}"
        raise RuntimeError(msg)

    client = AsyncOpenAI(api_key=api_key, base_url=player.base_url, timeout=args.request_timeout)

    summaries: list[dict[str, Any]] = []
    raw_results: dict[str, list[dict[str, Any]]] = {}
    baseline_p95: float | None = None
    for concurrency in args.concurrency:
        print(f"[probe] provider={provider} model={player.model} concurrency={concurrency}")
        summary, results = await _run_level(
            client=client,
            provider=provider,
            model=player.model,
            concurrency=concurrency,
            requests_per_level=args.requests_per_level,
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            request_timeout=args.request_timeout,
            baseline_p95_seconds=baseline_p95,
        )
        if baseline_p95 is None and summary["p95_seconds"] is not None:
            baseline_p95 = float(summary["p95_seconds"])
        summaries.append(summary)
        raw_results[str(concurrency)] = [asdict(result) for result in results]
        print(
            "[probe-result] "
            f"success={summary['success']}/{summary['total']} "
            f"429={summary['errors_rate_limit']} quota={summary['errors_quota']} "
            f"avg={summary['avg_seconds']}s p95={summary['p95_seconds']}s "
            f"rps={summary['throughput_rps']} soft_limited={summary['soft_limited']}"
        )
        if args.cooldown_seconds:
            await asyncio.sleep(args.cooldown_seconds)

    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "config": str(args.config),
        "provider": provider,
        "model": player.model,
        "base_url": player.base_url,
        "api_key_env": player.api_key_env,
        "requests_per_level": args.requests_per_level,
        "max_tokens": args.max_tokens,
        "request_timeout": args.request_timeout,
        "summaries": summaries,
        "raw_results": raw_results,
    }
    _write_json(args.output_dir / "rate_limit_probe_summary.json", payload)
    print(f"[summary] {args.output_dir / 'rate_limit_probe_summary.json'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--provider-label")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs")
        / f"provider-rate-limit-probe-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
    )
    parser.add_argument("--concurrency", nargs="+", type=int, default=[1, 2, 4, 6])
    parser.add_argument("--requests-per-level", type=int, default=6)
    parser.add_argument("--cooldown-seconds", type=float, default=10.0)
    parser.add_argument("--request-timeout", type=float, default=90.0)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument(
        "--prompt", default="Reply with exactly one short sentence: rate limit probe ok."
    )
    asyncio.run(_main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
