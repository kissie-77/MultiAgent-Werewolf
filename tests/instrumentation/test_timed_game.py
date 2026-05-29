"""对局计时器聚合逻辑的单元测试（不联网、不跑游戏）。

计时器是自包含脚本 scripts/timed_game.py（需对 before/after 两臂用同一份代码），
因此通过 sys.path 导入它，只测纯聚合（_pct / report）。HTTP 打补丁与真实对局由
线上 A/B 运行验证。
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import timed_game  # noqa: E402


def test_pct_linear_interpolation() -> None:
    assert timed_game._pct([], 0.5) is None
    assert timed_game._pct([10.0], 0.5) == 10.0
    assert timed_game._pct([10.0, 20.0, 30.0, 40.0], 0.5) == 25.0
    assert timed_game._pct([10.0, 20.0, 30.0, 40.0], 1.0) == 40.0


def test_report_counts_http_rounds_and_no_tool_call_fraction() -> None:
    timer = timed_game.GameTimer()
    timer._t0 = 1000.0
    timer._t_stop = 1100.0  # total_wall_s = 100.0
    timer.meta = {"label": "after"}
    # 三次 HTTP：两次带工具调用（结构化首轮），一次不带（"纯文本第二次往返"画像）。
    timer.http_calls = [
        {
            "wall_s": 8.0,
            "n_tool_calls": 1,
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "finish_reason": "tool_calls",
            "rel_start": 1.0,
        },
        {
            "wall_s": 5.0,
            "n_tool_calls": 1,
            "prompt_tokens": 120,
            "completion_tokens": 15,
            "finish_reason": "tool_calls",
            "rel_start": 30.0,
        },
        {
            "wall_s": 12.0,
            "n_tool_calls": 0,
            "prompt_tokens": 130,
            "completion_tokens": 700,
            "finish_reason": "stop",
            "rel_start": 60.0,
        },
    ]
    timer.events = [
        {"t": 0.5, "type": "x", "round": 1, "phase": "day"},
        {"t": 40.0, "type": "x", "round": 1, "phase": "night"},
        {"t": 70.0, "type": "x", "round": 2, "phase": "day"},
    ]

    report = timer.report()

    assert report["total_wall_s"] == 100.0
    overall = report["http_overall"]
    assert overall["n_http"] == 3
    assert overall["n_with_tool_call"] == 2
    assert overall["n_no_tool_call"] == 1
    assert overall["sum_completion_tokens"] == 735
    assert report["derived"]["n_rounds"] == 2
    assert report["derived"]["frac_http_without_tool_call"] == round(1 / 3, 3)
    # http 墙钟占比 = (8+5+12)/100 = 0.25
    assert report["derived"]["http_share_of_wall"] == 0.25
