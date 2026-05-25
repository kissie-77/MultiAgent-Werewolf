"""Textual-backed human input provider for TUI games."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.strategy.decisions import SpeechDecision, WitchNightDecision

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import PlayerProtocol


class TextualInputApp(Protocol):
    async def request_human_input(self, prompt: str, *, mode: str) -> str: ...

    def show_human_feedback(self, message: str) -> None: ...


class TextualHumanInputProvider:
    """HumanInputProvider implementation that waits on a Textual input box."""

    def __init__(self, app: TextualInputApp) -> None:
        self._app = app

    async def choose_seat(
        self,
        *,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        allow_skip: bool,
        context: str,
    ) -> PlayerProtocol | None:
        target_by_seat = {
            seat: player
            for player in possible_targets
            if (seat := WerewolfAdapterBridge.get_player_seat(player)) is not None
        }
        if not target_by_seat:
            if allow_skip:
                return None
            msg = "No selectable targets with resolvable seats."
            raise ValueError(msg)

        prompt = self._build_seat_prompt(
            role_name=role_name,
            context=context,
            action_description=action_description,
            target_by_seat=target_by_seat,
            allow_skip=allow_skip,
        )

        while True:
            answer = (await self._app.request_human_input(prompt, mode="number")).strip()
            if not answer.isdigit():
                self._app.show_human_feedback("请输入数字编号。")
                continue

            seat = int(answer)
            if allow_skip and seat == 0:
                return None
            if seat in target_by_seat:
                return target_by_seat[seat]

            self._app.show_human_feedback("编号不在可选范围内，请重试。")

    async def choose_yes_no(self, *, role_name: str, question: str, context: str) -> bool:
        prompt = "\n".join(["输入：1=是，2=否", f"[{role_name}] {context}", question])
        while True:
            answer = (await self._app.request_human_input(prompt, mode="number")).strip()
            if answer == "1":
                return True
            if answer == "2":
                return False
            self._app.show_human_feedback("请输入 1 或 2。")

    async def choose_witch_action(
        self,
        *,
        role_name: str,
        can_see_victim: bool,
        victim_line: str | None,
        poison_targets: list[PlayerProtocol],
        context: str,
    ) -> WitchNightDecision:
        options: list[tuple[str, str]] = []
        if can_see_victim:
            options.append(("save", "使用解药"))
        if poison_targets:
            options.append(("poison", "使用毒药"))
        options.append(("none", "不行动"))

        option_summary = "，".join(
            f"{index}={label}" for index, (_, label) in enumerate(options, 1)
        )
        prompt_lines = [f"女巫行动：{option_summary}", f"[{role_name}] {context}"]
        if can_see_victim and victim_line:
            prompt_lines.append(victim_line)
        prompt = "\n".join(prompt_lines)

        while True:
            answer = (await self._app.request_human_input(prompt, mode="number")).strip()
            if not answer.isdigit():
                self._app.show_human_feedback("请输入数字编号。")
                continue

            index = int(answer) - 1
            if not 0 <= index < len(options):
                self._app.show_human_feedback("编号不在可选范围内，请重试。")
                continue

            action = options[index][0]
            if action == "save":
                return WitchNightDecision(action="save", seat=0, reason=None)
            if action == "none":
                return WitchNightDecision(action="none", seat=0, reason=None)

            target = await self.choose_seat(
                role_name=role_name,
                action_description="选择毒杀目标",
                possible_targets=poison_targets,
                allow_skip=False,
                context=context,
            )
            seat = WerewolfAdapterBridge.get_player_seat(target) if target is not None else 0
            return WitchNightDecision(action="poison", seat=seat or 0, reason=None)

    async def choose_multi_targets(
        self,
        *,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        num_targets: int,
        context: str,
    ) -> list[PlayerProtocol]:
        target_by_seat = {
            seat: player
            for player in possible_targets
            if (seat := WerewolfAdapterBridge.get_player_seat(player)) is not None
        }
        if len(target_by_seat) < num_targets:
            msg = (
                f"Cannot choose {num_targets} distinct targets from "
                f"{len(target_by_seat)} available targets."
            )
            raise ValueError(msg)

        selected: list[PlayerProtocol] = []
        remaining = list(possible_targets)
        while len(selected) < num_targets:
            target = await self.choose_seat(
                role_name=role_name,
                action_description=action_description,
                possible_targets=remaining,
                allow_skip=False,
                context=context,
            )
            if target is None:
                continue
            selected.append(target)
            remaining = [player for player in remaining if player != target]

        return selected

    async def speak(
        self,
        *,
        context: str,
        instruction: str,
        phase: str,
        round_number: int,
    ) -> SpeechDecision:
        prompt = "\n".join([f"[{phase} 第 {round_number} 轮] {context}", instruction])
        while True:
            speech = (await self._app.request_human_input(prompt, mode="text")).strip()
            if speech:
                return SpeechDecision.model_construct(
                    public_speech=speech,
                    private_thought=None,
                )
            self._app.show_human_feedback("发言不能为空。")

    def _build_seat_prompt(
        self,
        *,
        role_name: str,
        context: str,
        action_description: str,
        target_by_seat: dict[int, PlayerProtocol],
        allow_skip: bool,
    ) -> str:
        option_parts = []
        if allow_skip:
            option_parts.append("0=跳过")
        option_parts.extend(
            f"{seat}={player.name}" for seat, player in sorted(target_by_seat.items())
        )
        lines = [
            f"输入目标编号：{', '.join(option_parts)}",
            f"[{role_name}] {context}",
            action_description,
        ]
        return "\n".join(lines)
