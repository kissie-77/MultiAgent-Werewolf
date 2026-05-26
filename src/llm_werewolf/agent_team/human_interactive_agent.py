"""人类交互 Agent：通过控制台输入数字（选座位 / 投票）与纯文本（发言）参与对局。

设计要点（最小侵入，保证 shell 输出与纯 Agent 局基本一致）：

- 本类**不**提供 ``agentscope_agent``，也**不**提供 ``get_structured_response``，
  因此 :func:`~llm_werewolf.agent_team.structured_invoke.agent_uses_structured_output`
  返回 ``False``，``WerewolfAdapterBridge`` 的所有决策都会回落到 ``get_response``
  文本路径（见 bridge.py 中各 ``request_*`` 方法的非结构化分支）。
- 人类玩家通过 ``ConsolePresenter`` 的对局日志“观战”，本 Agent 只在“轮到你”时
  打印精简后的行动提示。``get_response`` 会**识别当前决策类型**（选座 / 多选 /
  是否 / 女巫 / 发言），给出针对性提示，**校验并归一化**人类输入后再交给 bridge
  解析——这样人类只需按提示输入，而不必了解 ``[[N]]`` / ``救`` / ``毒`` 等内部格式。
  非法输入会就地重试（有限次），避免静默落到随机兜底。
- ``get_response`` 用 ``asyncio.to_thread`` 包裹内置 ``input``，避免阻塞 asyncio
  事件循环。读到 EOF（如管道输入耗尽）或被中断时返回空串，交由引擎的跳过 /
  兜底逻辑处理（不会死循环）。
"""

from __future__ import annotations

import asyncio
import re

from pydantic import Field
from rich.console import Console

from llm_werewolf.agent_team.base import BaseAgent

console = Console()

# 写给 LLM 的结构化输出约束行，对人类无意义，展示时过滤掉以降噪。
_NOISE_MARKERS = (
    "generate_response",
    "Schema",
    "schema",
    "structured",
    "（兼容模式）",
    "禁止用 [[",
    "禁止 [[",
    "【输出方式】",
    "【信息隔离】",
    "【本任务输出",
    "不要输出其他文字",
    "不是列表序号",
)

_MAX_ATTEMPTS = 3

# 决策类型
_KIND_WITCH = "witch"
_KIND_MULTI = "multi"
_KIND_YESNO = "yesno"
_KIND_SEAT = "seat"
_KIND_SPEECH = "speech"


class HumanInteractiveAgent(BaseAgent):
    """控制台人类玩家。仅需按提示输入座位号 / 1或0 / 中文发言即可参与。"""

    model: str = Field(default="human")

    # ------------------------------------------------------------------
    # 展示与分类
    # ------------------------------------------------------------------

    def _render_prompt(self, message: str) -> str:
        """剔除面向 LLM 的 schema 噪声行，留下人类可读的行动提示。"""
        kept = [
            line
            for line in message.splitlines()
            if not any(marker in line for marker in _NOISE_MARKERS)
        ]
        rendered = "\n".join(kept).strip()
        return rendered or message.strip()

    @staticmethod
    def _classify(message: str) -> tuple[str, int, bool]:
        """根据 bridge 构建的 prompt 文本识别决策类型。

        Returns: (kind, num_targets, allow_skip)
        """
        if "三选一" in message or "救人(save)" in message:
            return _KIND_WITCH, 0, False

        multi = re.search(r"选择\s*(\d+)\s*个不同目标", message) or re.search(
            r"回复\s*(\d+)\s*个全局座位号", message
        )
        if multi:
            return _KIND_MULTI, int(multi.group(1)), False

        if "[[1]] 表示是" in message or ("表示是" in message and "表示否" in message):
            return _KIND_YESNO, 0, False

        if (
            "请只回复目标玩家的全局座位号" in message
            or "投票意向采集" in message
            or "可选目标" in message
            or "可选放逐目标" in message
        ):
            allow_skip = "座位 0" in message or "投票意向采集" in message
            return _KIND_SEAT, 0, allow_skip

        return _KIND_SPEECH, 0, False

    @staticmethod
    def _hint(kind: str, n: int, allow_skip: bool) -> str:
        if kind == _KIND_WITCH:
            return "[dim]救人输入「救」；毒人输入「毒 座位号」(如 毒 3)；不行动输入 0 或直接回车。[/dim]"
        if kind == _KIND_MULTI:
            return f"[dim]请输入 {n} 个不同座位号，用空格分隔，例如 3 5。[/dim]"
        if kind == _KIND_YESNO:
            return "[dim]请输入 1 表示「是」，0 表示「否」。[/dim]"
        if kind == _KIND_SEAT:
            if allow_skip:
                return "[dim]请输入目标座位号(如 3)；不行动 / 弃票输入 0。[/dim]"
            return "[dim]请输入目标座位号(如 3)，本回合必须选择。[/dim]"
        return "[dim]请输入你的发言（完整中文，至少 15 字）。[/dim]"

    # ------------------------------------------------------------------
    # 校验 + 归一化为 bridge 解析器期望的字符串
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(kind: str, n: int, allow_skip: bool, raw: str) -> tuple[str | None, str]:
        text = raw.strip()
        low = text.lower()

        if kind == _KIND_SPEECH:
            if len(text) < 15:
                return None, "发言太短，请输入完整的中文发言（至少 15 字）。"
            return text, ""

        if kind == _KIND_YESNO:
            if text == "0" or low in {"n", "no"} or any(k in text for k in ("否", "不", "拒绝", "弃")):
                return "0", ""
            if text == "1" or low in {"y", "yes"} or any(
                k in text for k in ("是", "好", "同意", "参加", "愿意", "要")
            ):
                return "1", ""
            return None, "请输入 1 表示「是」，0 表示「否」。"

        if kind == _KIND_WITCH:
            if text in {"", "0"} or "不行动" in text or "none" in low or "跳过" in text:
                return "none", ""
            if "救" in text or "save" in low:
                return "救", ""
            if "毒" in text or "poison" in low:
                nums = re.findall(r"\d+", text)
                if not nums:
                    return None, "毒人请指定座位号，例如：毒 3。"
                return f"毒 [[{nums[0]}]]", ""
            return None, "请输入：救（用解药）/ 毒 座位号（用毒药）/ 0（不行动）。"

        if kind == _KIND_MULTI:
            nums = re.findall(r"\d+", text)
            if len(nums) != n or len(set(nums)) != n:
                return None, f"请输入 {n} 个不同的座位号，用空格分隔，例如 3 5。"
            return " ".join(nums), ""

        # kind == seat
        nums = re.findall(r"\d+", text)
        if not nums:
            return None, "请输入一个座位号数字。"
        seat = int(nums[0])
        if seat == 0 and not allow_skip:
            return None, "本回合必须选择一个有效目标，不能跳过。"
        return str(seat), ""

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def get_response(self, message: str) -> str:
        kind, n, allow_skip = self._classify(message)
        console.print(f"\n[bold cyan]──── 轮到你（{self.name}）────[/bold cyan]")
        console.print(self._render_prompt(message))
        console.print(self._hint(kind, n, allow_skip))

        raw = ""
        for _ in range(_MAX_ATTEMPTS):
            try:
                raw = (await asyncio.to_thread(input, ">>> ")).strip()
            except (EOFError, KeyboardInterrupt):
                console.print("[yellow](未读取到输入，按跳过 / 兜底处理)[/yellow]")
                return ""
            normalized, error = self._normalize(kind, n, allow_skip, raw)
            if normalized is not None:
                return normalized
            console.print(f"[yellow]{error}[/yellow]")
        # 超过重试次数：交回原始输入，由 bridge 走其兜底逻辑（避免死循环）。
        return raw
