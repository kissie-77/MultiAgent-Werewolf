"""对局计时器：非侵入式测量一局狼人杀的墙钟与 LLM HTTP 往返开销。

**自包含**（不依赖 llm_werewolf 包内的任何计时模块），这样同一个脚本可以用来测
before(main/src) 与 after(worktree/src) 两个代码状态的同一套指标——只需切换
``PYTHONPATH`` 指向不同的源码树，游戏代码随之改变，而计时逻辑保持一致。

只在 openai 边界打补丁（``AsyncCompletions.create``，沿用 _play/latency_decomp.py
已验证可行的方式），记录每次**物理 HTTP 往返**的 wall/tokens/finish_reason/
tool_calls。结构化决策的"第二次纯文本往返"会自然表现为同一逻辑决策下多出来的一次
HTTP，从而被 ``n_http`` 捕获。补丁内只累加、不 ``print``（rich/logfire 会捕获
stdout，调用内 print 会抛错并打断模型调用——见项目记忆 game-http-instrumentation
-stdout-gotcha）。

用法::

    PYTHONPATH=<arm>/src ARK_API_KEY=<key> PYTHONUTF8=1 \\
        python _play/timed_game.py --config configs/llm-6p-doubao.yaml \\
        --out runs_timing/after.json --label after --seed 12345
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import time
from pathlib import Path
from typing import Any, Callable

import openai.resources.chat.completions as _OC

# 进程内当前激活的计时器；被打补丁的 create 用它来记录。
_ACTIVE: "GameTimer | None" = None
_ORIG_CREATE: Callable | None = None


def _pct(values: list[float], q: float) -> float | None:
    """线性插值分位数（q∈[0,1]），避免引入额外依赖。"""
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return round(s[0], 3)
    k = (len(s) - 1) * q
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return round(s[int(k)], 3)
    return round(s[f] + (s[c] - s[f]) * (k - f), 3)


async def _wrapped_create(self, *args: Any, **kwargs: Any):  # noqa: ANN001
    """打补丁后的 AsyncCompletions.create：测量物理 HTTP 往返。只累加、不 print。"""
    timer = _ACTIVE
    t_start = time.perf_counter()
    resp = await _ORIG_CREATE(self, *args, **kwargs)  # type: ignore[misc]
    dt = time.perf_counter() - t_start
    if timer is None:
        return resp
    rec: dict[str, Any] = {
        "label": timer._label,
        "wall_s": round(dt, 3),
        "rel_start": round(t_start - (timer._t0 or t_start), 3),
    }
    try:
        usage = getattr(resp, "usage", None)
        if usage is not None:
            rec["prompt_tokens"] = getattr(usage, "prompt_tokens", None)
            rec["completion_tokens"] = getattr(usage, "completion_tokens", None)
            ctd = getattr(usage, "completion_tokens_details", None)
            if ctd is not None:
                rec["reasoning_tokens"] = getattr(ctd, "reasoning_tokens", None)
        choices = getattr(resp, "choices", None) or []
        if choices:
            msg = getattr(choices[0], "message", None)
            rec["finish_reason"] = getattr(choices[0], "finish_reason", None)
            tcs = getattr(msg, "tool_calls", None) if msg else None
            rec["n_tool_calls"] = len(tcs) if tcs else 0
        rec["max_tokens_req"] = kwargs.get("max_tokens")
    except Exception as exc:  # noqa: BLE001
        rec["inspect_error"] = str(exc)[:120]
    timer.http_calls.append(rec)
    return resp


class GameTimer:
    """单局测量器：HTTP 调用记录 + 事件时间线 + 派生指标。"""

    def __init__(self) -> None:
        self.http_calls: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self._t0: float | None = None
        self._t_stop: float | None = None
        self._label: str = "play"
        self._orig_on_event: Callable[[Any], None] | None = None
        self.meta: dict[str, Any] = {}

    def install_http(self) -> None:
        """把本计时器设为当前激活者，并对 OpenAI create 打补丁（幂等，类级）。"""
        global _ACTIVE, _ORIG_CREATE
        _ACTIVE = self
        if _ORIG_CREATE is None:
            _ORIG_CREATE = _OC.AsyncCompletions.create
            _OC.AsyncCompletions.create = _wrapped_create  # type: ignore[assignment]

    def wrap_engine(self, engine: Any) -> None:
        """串接 ``engine.on_event``：先记录时间戳，再调用原处理器。"""
        self._orig_on_event = getattr(engine, "on_event", None)

        def _tap(event: Any) -> None:
            self._record_event(event)
            if self._orig_on_event is not None:
                self._orig_on_event(event)

        engine.on_event = _tap

    def _record_event(self, event: Any) -> None:
        now = time.perf_counter()
        t0 = self._t0
        phase = getattr(event, "phase", None)
        etype = getattr(event, "event_type", None)
        self.events.append(
            {
                "t": round(now - t0, 3) if t0 is not None else 0.0,
                "type": getattr(etype, "value", str(etype)),
                "round": getattr(event, "round_number", None),
                "phase": getattr(phase, "value", str(phase)),
            }
        )

    def start(self) -> None:
        self._t0 = time.perf_counter()

    def stop(self) -> None:
        self._t_stop = time.perf_counter()

    def set_label(self, label: str) -> None:
        self._label = label

    def _agg(self, calls: list[dict[str, Any]]) -> dict[str, Any]:
        walls = [c["wall_s"] for c in calls if "wall_s" in c]
        return {
            "n_http": len(calls),
            "total_wall_s": round(sum(walls), 1),
            "mean_wall_s": round(sum(walls) / len(walls), 3) if walls else None,
            "p50_wall_s": _pct(walls, 0.50),
            "p95_wall_s": _pct(walls, 0.95),
            "max_wall_s": round(max(walls), 3) if walls else None,
            "sum_prompt_tokens": sum(c.get("prompt_tokens") or 0 for c in calls),
            "sum_completion_tokens": sum(c.get("completion_tokens") or 0 for c in calls),
            "sum_reasoning_tokens": sum(c.get("reasoning_tokens") or 0 for c in calls),
            "n_finish_length": sum(1 for c in calls if c.get("finish_reason") == "length"),
            "n_with_tool_call": sum(1 for c in calls if c.get("n_tool_calls")),
            "n_no_tool_call": sum(1 for c in calls if not c.get("n_tool_calls")),
        }

    def report(self) -> dict[str, Any]:
        t0 = self._t0 or 0.0
        total = (
            (self._t_stop - t0)
            if (self._t_stop is not None and self._t0 is not None)
            else (self.events[-1]["t"] if self.events else 0.0)
        )
        rounds_seen = sorted({e["round"] for e in self.events if isinstance(e["round"], int)})
        per_round = []
        for rnd in rounds_seen:
            ts = [e["t"] for e in self.events if e["round"] == rnd]
            per_round.append(
                {"round": rnd, "span_s": round(max(ts) - min(ts), 1), "n_events": len(ts)}
            )
        n_rounds = len(rounds_seen)
        overall = self._agg(self.http_calls)
        return {
            "meta": self.meta,
            "total_wall_s": round(total, 1),
            "http_overall": overall,
            "derived": {
                "n_rounds": n_rounds,
                "http_per_round": round(overall["n_http"] / n_rounds, 1) if n_rounds else None,
                "wall_per_round_s": round(total / n_rounds, 1) if n_rounds else None,
                "http_share_of_wall": round(
                    sum(c["wall_s"] for c in self.http_calls) / total, 3
                )
                if total
                else None,
                # 第二次往返画像：无工具调用的 HTTP 占比（结构化决策的"纯文本第二次往返"
                # 正是这类）。修复后该计数应大幅下降。
                "frac_http_without_tool_call": round(
                    overall["n_no_tool_call"] / overall["n_http"], 3
                )
                if overall["n_http"]
                else None,
            },
            "per_round": per_round,
            "n_events": len(self.events),
        }

    def dump(self, path: str | Path) -> dict[str, Any]:
        report = self.report()
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report


async def run_timed_game(
    config_path: str,
    out_path: str,
    *,
    label: str,
    seed: int | None,
    setup_only: bool = False,
    max_seconds: float | None = None,
) -> dict[str, Any]:
    """以计时器包裹运行一整局（跳过控制台展示与赛后分析，隔离对局墙钟）。

    ``setup_only=True`` 时只构建配置 / 名单 / 角色 / Agent 与 prompt 绑定（全程离线，
    OpenAIChatModel 构造不联网），用于在烧真实 API 之前廉价校验整条接线。
    """
    # 延迟导入：游戏代码由 PYTHONPATH 决定（before=main/src，after=worktree/src）。
    from llm_werewolf.game_runtime import GameEngine
    from llm_werewolf.game_runtime.utils import load_config
    from llm_werewolf.interface.bootstrap import (
        prepare_game_roster,
        wire_agentscope_after_setup,
    )

    if seed is not None:
        random.seed(seed)  # 让角色洗牌在两臂间一致，减少一个方差来源。

    players_config = load_config(config_path=Path(config_path))
    agents, roles, game_config = prepare_game_roster(players_config)

    engine = GameEngine(game_config, language=players_config.language)
    engine.on_event = lambda _event: None  # 静默：不接控制台展示，降低噪声。

    timer = GameTimer()
    timer.meta = {
        "label": label,
        "config": config_path,
        "num_players": len(players_config.players),
        "seed": seed,
        "model": players_config.players[0].model,
    }
    timer.set_label(label)
    timer.wrap_engine(engine)

    engine.setup_game(players=agents, roles=roles)
    wire_agentscope_after_setup(engine, players_config)

    if setup_only:
        info = {
            "setup_only": True,
            "num_players": len(agents),
            "roles": sorted(r.__class__.__name__ for r in roles),
            "model": timer.meta["model"],
        }
        print(f"[{label}] setup-only OK: {info}")
        return info

    timer.install_http()
    timer.start()
    timed_out = False
    try:
        if max_seconds:
            result = await asyncio.wait_for(engine.play_game(), timeout=max_seconds)
        else:
            result = await engine.play_game()
    except (asyncio.TimeoutError, TimeoutError):
        # 兜底：单次调用无超时（报告 ⑤），整局加一个总预算防止无人值守时挂死。
        timed_out = True
        result = f"<TIMED_OUT after {max_seconds}s>"
    finally:
        timer.stop()

    timer.meta["timed_out"] = timed_out
    timer.meta["result"] = result if isinstance(result, str) else str(result)
    report = timer.dump(out_path)

    # 同时落一份事件流转写，供质量评审 agent 对比两臂的发言 / 投票 / 死亡 / 胜负。
    _dump_transcript(engine, Path(out_path).with_suffix(".events.jsonl"))
    return report


def _dump_transcript(engine: Any, path: Path) -> None:
    from llm_werewolf.evaluation.post_game.event_adapter import event_to_dict

    logger = getattr(engine, "event_logger", None)
    if logger is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for event in getattr(logger, "events", []):
            fh.write(json.dumps(event_to_dict(event), ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Time a single werewolf game.")
    parser.add_argument("--config", required=True, help="Path to players YAML config.")
    parser.add_argument("--out", required=True, help="Path to write timing JSON.")
    parser.add_argument("--label", default="play", help="Arm label, e.g. before/after.")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed for role shuffling so both arms get identical roles.",
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Validate config/roster/agent wiring offline; no game, no API calls.",
    )
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=None,
        help="Overall per-game wall-clock budget; game is cancelled if exceeded.",
    )
    args = parser.parse_args()
    report = asyncio.run(
        run_timed_game(
            args.config,
            args.out,
            label=args.label,
            seed=args.seed,
            setup_only=args.setup_only,
            max_seconds=args.max_seconds,
        )
    )
    if report.get("setup_only"):
        return
    summary = report["http_overall"]
    # 仅在运行结束后 print（不在被打补丁的 create 内）——安全。
    print(
        f"[{args.label}] total_wall_s={report['total_wall_s']} "
        f"n_http={summary['n_http']} n_rounds={report['derived']['n_rounds']} "
        f"frac_no_tool_call={report['derived']['frac_http_without_tool_call']} "
        f"-> {args.out}"
    )


if __name__ == "__main__":
    main()
