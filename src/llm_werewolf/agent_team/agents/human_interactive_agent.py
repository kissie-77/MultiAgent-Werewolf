"""人类交互 Agent：通过控制台输入数字（选座位 / 投票）与纯文本（发言）参与对局。

设计要点（最小侵入，保证 shell 输出与纯 Agent 局基本一致）：

- 本类**不**提供 ``agentscope_agent``，也**不**提供 ``get_structured_response``，
  因此 :func:`~llm_werewolf.agent_team.invocation.structured_invoke.agent_uses_structured_output`
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

import re
import asyncio

from pydantic import Field
from rich.console import Console

from llm_werewolf.agent_team.agents.base import BaseAgent

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
    "【本阶段输出】",
    "【公开发言信息边界】",
    "SeatChoiceDecision",
    "SpeechDecision",
    "VoteIntentionDecision",
    "WitchNightDecision",
    "MindStateDecision",
    "public_speech",
    "private_thought",
    "reason 必填",
    "不要输出其他文字",
    "不是列表序号",
    "【对话记忆 · MsgHub】",
    "【决策上下文 · MsgHub】",
    "【当前信念矩阵",
    "请结合公开信息与上述信念",
    "请仔细分析当前局势",
)

_BLOCK_NOISE_PREFIXES = (
    "【身份提示】",
    "【当前信念矩阵",
    "【内心信念】",
    "【信念/意向更新规则】",
    "【公开发言信息边界】",
    "【狼队共享战术面板",
    "【稳定经验】",
    "【历史回顾】",
    "【本轮记忆】",
    "最近离线决策摘要:",
)

_BLOCK_KEEP_PREFIXES = (
    "【本轮已听到的发言】",
    "【子阶段",
    "【任务】",
    "【投票】",
    "【可选",
    "可选目标",
    "可选放逐目标",
    "私密信息：",
    "场上玩家：",
    "当前阶段：",
    "当前轮次：",
    "存活概况：",
)

_MAX_ATTEMPTS = 3
_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
_OPTION_SEAT_RE = re.compile(r"^\s*-\s*座位\s*(\d+)")

# 决策类型
_KIND_WITCH = "witch"
_KIND_MULTI = "multi"
_KIND_YESNO = "yesno"
_KIND_SEAT = "seat"
_KIND_SPEECH = "speech"

_INVALID_SPEECH_FALLBACK = (
    "我这轮暂时弃发言，先听其他玩家的发言和投票，再根据后续信息判断。"
)


class HumanInteractiveAgent(BaseAgent):
    """控制台人类玩家。仅需按提示输入座位号 / 1或0 / 中文发言即可参与。"""

    model: str = Field(default="human")

    # ------------------------------------------------------------------
    # 展示与分类
    # ------------------------------------------------------------------

    @staticmethod
    def _marker_text(line: str) -> str:
        return line.strip().lstrip("- ").strip()

    @staticmethod
    def _render_speech_prompt(message: str) -> str:
        """人类玩家发言时只给输入提示；发言历史由正常日志展示。"""
        if "狼队友讨论" in message or "狼队夜聊" in message:
            return "请进行狼队夜聊发言。"
        if "警长竞选" in message:
            return "请进行警长竞选发言。"
        if "PK 发言" in message:
            return "请进行 PK 发言。"
        return "请进行白天公开发言。"

    @staticmethod
    def _render_action_prompt(message: str, kind: str) -> str:
        """人类行动只展示必要输入信息，不展示 Agent observation。"""
        kept: list[str] = []
        in_targets = False
        seen_identity = False

        for line in message.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("你是"):
                if not seen_identity:
                    kept.append(stripped)
                    seen_identity = True
                in_targets = False
                continue
            if stripped.startswith(("当前：", "当前回合：", "任务：", "问题：")):
                kept.append(stripped)
                in_targets = False
                continue
            if stripped.startswith(("可选目标", "可选放逐目标", "若选择 poison，可选毒杀目标")):
                kept.append(stripped)
                in_targets = True
                continue
            if in_targets:
                if stripped.startswith("- 座位"):
                    kept.append(stripped)
                    continue
                in_targets = False

            if kind == _KIND_WITCH and (
                "女巫" in stripped
                or "刀口" in stripped
                or "被狼人" in stripped
                or "击杀" in stripped
                or "解药已用完" in stripped
                or "解药不可用" in stripped
                or "不能选择 save" in stripped
                or "三选一" in stripped
                or "二选一" in stripped
            ):
                kept.append(stripped)

        rendered = "\n".join(kept).strip()
        return rendered or message.strip()

    def _render_prompt(self, message: str, *, kind: str | None = None) -> str:
        """剔除面向 LLM 的 schema / 策略噪声，留下人类玩家可见信息。"""
        if kind == _KIND_SPEECH:
            return self._render_speech_prompt(message)
        if kind in {_KIND_YESNO, _KIND_SEAT, _KIND_MULTI, _KIND_WITCH}:
            return self._render_action_prompt(message, kind)

        kept: list[str] = []
        skip_internal_block = False

        for line in message.splitlines():
            stripped = line.strip()
            marker_text = self._marker_text(line)

            if any(marker_text.startswith(prefix) for prefix in _BLOCK_NOISE_PREFIXES):
                skip_internal_block = True
                continue

            if marker_text in {"【对话记忆 · MsgHub】", "【决策上下文 · MsgHub】"}:
                skip_internal_block = True
                continue

            if skip_internal_block:
                if not stripped:
                    continue
                if (
                    marker_text.startswith("【")
                    or marker_text.endswith("：")
                    or any(marker_text.startswith(prefix) for prefix in _BLOCK_KEEP_PREFIXES)
                ):
                    skip_internal_block = False
                else:
                    continue

            if any(marker in line for marker in _NOISE_MARKERS):
                continue
            kept.append(line)

        rendered = "\n".join(kept).strip()
        return rendered or message.strip()

    @staticmethod
    def _classify(message: str) -> tuple[str, int, bool]:
        """根据 bridge 构建的 prompt 文本识别决策类型。

        Returns: (kind, num_targets, allow_skip)
        """
        if (
            "【子阶段·仅发言】" in message
            or "请仔细分析当前局势，发表你的观点" in message
            or "与狼队友讨论" in message
            or "公开讨论轮" in message
        ):
            return _KIND_SPEECH, 0, False

        if (
            "女巫请睁眼" in message
            or "三选一" in message
            or "二选一" in message
            or "救人(save)" in message
            or "毒人(poison)" in message
            or "WitchNightDecision" in message
        ):
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
    def _hint_plain(
        kind: str,
        n: int,
        allow_skip: bool,
        *,
        allow_witch_save: bool = True,
    ) -> str:
        """Plain-text input hint for browser UI (no Rich markup)."""
        if kind == _KIND_WITCH:
            if not allow_witch_save:
                return "可用毒药指定座位（如选择 3 号）；不行动请点「不行动」。"
            return "可救人、可毒指定座位，或不行动。"
        if kind == _KIND_MULTI:
            return f"请选择 {n} 个不同座位，确认后提交。"
        if kind == _KIND_YESNO:
            return "请选择「是」或「否」。"
        if kind == _KIND_SEAT:
            if allow_skip:
                return "点选目标座位；弃票/跳过请点「弃票」。"
            return "本回合必须选择一个有效目标。"
        return "请输入完整中文发言（至少 15 字，勿用重复字符或纯英文占位）。"

    @staticmethod
    def _title_for_kind(kind: str, message: str) -> str:
        if kind == _KIND_SPEECH:
            if "狼队友讨论" in message or "狼队夜聊" in message or "与狼队友讨论" in message:
                return "狼队夜聊"
            if "警长竞选" in message or "PK 发言" in message:
                return "警长竞选发言"
            return "公开发言"
        if kind == _KIND_WITCH:
            return "女巫行动"
        if kind == _KIND_YESNO:
            if "警长" in message or "竞选" in message:
                return "警长抉择"
            return "是 / 否"
        if kind == _KIND_MULTI:
            return "多选目标"
        if kind == _KIND_SEAT:
            if HumanInteractiveAgent._is_werewolf_kill_prompt(message):
                return "狼人刀人"
            if "投票" in message or "放逐" in message:
                return "投票放逐"
            if "查验" in message or "预言" in message:
                return "查验目标"
            return "选择目标"
        return "轮到你了"

    @staticmethod
    def _extract_self_role(message: str) -> str:
        m = re.search(r"身份为\s*([A-Za-z][A-Za-z ]*)", message)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _extract_kill_target_seat(message: str) -> int | None:
        m = re.search(r"今晚狼人目标是\s*Player\s*(\d+)", message, re.IGNORECASE)
        return int(m.group(1)) if m else None

    @staticmethod
    def _extract_remaining_potions(message: str, kind: str) -> dict[str, bool] | None:
        if kind != _KIND_WITCH:
            return None
        save = HumanInteractiveAgent._witch_save_allowed(message)
        poison_blocked = any(
            marker in message
            for marker in ("毒药已用完", "毒药已耗尽", "毒药不可用", "不能下毒")
        )
        return {"save": bool(save), "poison": not poison_blocked}

    @staticmethod
    def _extract_target_meta(message: str) -> list[dict[str, object]]:
        meta: list[dict[str, object]] = []
        for line in message.splitlines():
            m = re.match(r"\s*-\s*座位\s*(\d+)[：:]\s*([^（(]+)", line)
            if m:
                meta.append({"seat": int(m.group(1)), "name": m.group(2).strip()})
        return meta

    @staticmethod
    def _question_for(kind: str, title: str, message: str) -> str:
        if kind == _KIND_WITCH:
            seat = HumanInteractiveAgent._extract_kill_target_seat(message)
            if seat is not None:
                return f"今夜 {seat} 号被狼人袭击，是否用解药？"
            return "今夜女巫行动：用药或跳过。"
        if kind == _KIND_YESNO:
            return f"{title}：是 / 否。"
        return f"请选择一名目标（{title}）。"

    @staticmethod
    def prepare_web_prompt(message: str) -> dict[str, object]:
        """Sanitize an engine prompt for browser human UI."""
        kind, n, allow_skip = HumanInteractiveAgent._classify(message)
        allow_witch_save = kind == _KIND_WITCH and HumanInteractiveAgent._witch_save_allowed(message)
        if kind == _KIND_SPEECH:
            prompt = HumanInteractiveAgent._render_speech_prompt(message)
        elif kind in {_KIND_YESNO, _KIND_SEAT, _KIND_MULTI, _KIND_WITCH}:
            prompt = HumanInteractiveAgent._render_action_prompt(message, kind)
        else:
            prompt = HumanInteractiveAgent(name="_web")._render_prompt(message, kind=kind)
        return {
            "kind": kind,
            "prompt": prompt,
            "ui_hint": HumanInteractiveAgent._hint_plain(
                kind, n, allow_skip, allow_witch_save=allow_witch_save
            ),
            "title": HumanInteractiveAgent._title_for_kind(kind, message),
            "allow_skip": allow_skip,
            "allow_witch_save": allow_witch_save,
            "multi_count": n if kind == _KIND_MULTI else 0,
            "self_role": HumanInteractiveAgent._extract_self_role(message),
            "kill_target_seat": HumanInteractiveAgent._extract_kill_target_seat(message),
            "remaining_potions": HumanInteractiveAgent._extract_remaining_potions(message, kind),
            "question": HumanInteractiveAgent._question_for(
                kind, HumanInteractiveAgent._title_for_kind(kind, message), message
            ),
            "target_meta": HumanInteractiveAgent._extract_target_meta(message),
        }

    @staticmethod
    def _hint(kind: str, n: int, allow_skip: bool, *, allow_witch_save: bool = True) -> str:
        if kind == _KIND_WITCH:
            if not allow_witch_save:
                return "[dim]毒人输入「毒 座位号」(如 毒 3)；不行动输入 0 或直接回车。[/dim]"
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

    @staticmethod
    def _is_werewolf_kill_prompt(message: str) -> bool:
        return "狼人请睁眼" in message or "今晚你要刀谁" in message

    @staticmethod
    def _confirmation(
        kind: str, normalized: str, *, is_werewolf_kill: bool = False
    ) -> str:
        if kind == _KIND_SPEECH:
            return f"已提交发言：{normalized}"
        if kind == _KIND_WITCH:
            if normalized == "none":
                return "已提交：今晚不行动"
            return f"已提交女巫行动：{normalized}"
        if kind == _KIND_YESNO:
            return f"已提交选择：{'是' if normalized == '1' else '否'}"
        if normalized == "0":
            return "已提交：跳过 / 弃票"
        if kind == _KIND_SEAT and is_werewolf_kill:
            return f"已提交你的狼刀票：座位 {normalized}；最终刀口以狼队结算为准"
        return f"已提交目标：座位 {normalized}"

    @staticmethod
    def _fallback_after_invalid(kind: str, allow_skip: bool) -> str:
        if kind == _KIND_SPEECH:
            return _INVALID_SPEECH_FALLBACK
        if kind == _KIND_WITCH:
            return "none"
        if kind == _KIND_YESNO:
            return "0"
        if kind == _KIND_SEAT and allow_skip:
            return "0"
        return ""

    @staticmethod
    def _print_waiting_hint() -> None:
        console.print("[dim]等待其他玩家决策...[/dim]")

    # ------------------------------------------------------------------
    # 校验 + 归一化为 bridge 解析器期望的字符串
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_option_seats(message: str) -> set[int]:
        seats: set[int] = set()
        for line in message.splitlines():
            if match := _OPTION_SEAT_RE.match(line):
                seats.add(int(match.group(1)))
        return seats

    @staticmethod
    def _witch_save_allowed(message: str) -> bool:
        if "救人(save)" not in message and "救今晚刀口" not in message:
            return False
        return not any(
            marker in message
            for marker in (
                "解药已用完",
                "解药已耗尽",
                "解药不可用",
                "不能救",
                "不能选择 save",
                "没有可救刀口",
            )
        )

    @staticmethod
    def _looks_like_valid_speech(text: str) -> bool:
        if len(text) < 15:
            return False
        if not _CHINESE_RE.search(text):
            return False
        compact = re.sub(r"\s+", "", text)
        if not compact:
            return False
        unique_chars = set(compact)
        return not len(unique_chars) <= 3

    @staticmethod
    def _normalize(
        kind: str,
        n: int,
        allow_skip: bool,
        raw: str,
        *,
        option_seats: set[int] | None = None,
        allow_witch_save: bool = True,
    ) -> tuple[str | None, str]:
        text = raw.strip()
        low = text.lower()

        if kind == _KIND_SPEECH:
            if not HumanInteractiveAgent._looks_like_valid_speech(text):
                return None, "请输入完整的中文发言（至少 15 字，不能是重复字符或纯英文占位）。"
            return text, ""

        if kind == _KIND_YESNO:
            if (
                text == "0"
                or low in {"n", "no"}
                or any(k in text for k in ("否", "不", "拒绝", "弃"))
            ):
                return "0", ""
            if (
                text == "1"
                or low in {"y", "yes"}
                or any(k in text for k in ("是", "好", "同意", "参加", "愿意", "要"))
            ):
                return "1", ""
            return None, "请输入 1 表示「是」，0 表示「否」。"

        if kind == _KIND_WITCH:
            if text in {"", "0"} or "不行动" in text or "none" in low or "跳过" in text:
                return "none", ""
            if "救" in text or "save" in low:
                if not allow_witch_save:
                    return None, "解药已用完或本夜没有可救刀口，不能救人；请输入 毒 座位号 或 0。"
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
            if option_seats:
                invalid = [num for num in nums if int(num) not in option_seats]
                if invalid:
                    return None, f"座位 {', '.join(invalid)} 不在可选目标中，请重新输入。"
            return " ".join(nums), ""

        # kind == seat
        nums = re.findall(r"\d+", text)
        if not nums:
            return None, "请输入一个座位号数字。"
        seat = int(nums[0])
        if seat == 0 and not allow_skip:
            return None, "本回合必须选择一个有效目标，不能跳过。"
        if option_seats and seat not in option_seats:
            allowed = ", ".join(str(s) for s in sorted(option_seats))
            return None, f"座位 {seat} 不在可选目标中，请输入：{allowed}。"
        return str(seat), ""

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def get_response(self, message: str) -> str:
        kind, n, allow_skip = self._classify(message)
        option_seats = self._extract_option_seats(message)
        allow_witch_save = kind == _KIND_WITCH and self._witch_save_allowed(message)
        is_werewolf_kill = kind == _KIND_SEAT and self._is_werewolf_kill_prompt(message)
        console.print(f"\n[bold cyan]──── 轮到你（{self.name}）────[/bold cyan]")
        console.print(self._render_prompt(message, kind=kind))
        console.print(self._hint(kind, n, allow_skip, allow_witch_save=allow_witch_save))

        raw = ""
        for _ in range(_MAX_ATTEMPTS):
            try:
                raw = (await asyncio.to_thread(input, ">>> ")).strip()
            except (EOFError, KeyboardInterrupt):
                console.print("[yellow](未读取到输入，按跳过 / 兜底处理)[/yellow]")
                return ""
            normalized, error = self._normalize(
                kind,
                n,
                allow_skip,
                raw,
                option_seats=option_seats,
                allow_witch_save=allow_witch_save,
            )
            if normalized is not None:
                confirmation = self._confirmation(
                    kind,
                    normalized,
                    is_werewolf_kill=is_werewolf_kill,
                )
                console.print(f"[green]{confirmation}[/green]")
                self._print_waiting_hint()
                return normalized
            console.print(f"[yellow]{error}[/yellow]")
        fallback = self._fallback_after_invalid(kind, allow_skip)
        console.print("[yellow](超过重试次数，按跳过 / 兜底处理)[/yellow]")
        self._print_waiting_hint()
        return fallback
