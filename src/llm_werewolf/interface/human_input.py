from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Any

from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.game_runtime.types import PlayerProtocol
from llm_werewolf.strategy.decisions import SpeechDecision, WitchNightDecision


def is_human_agent(agent: Any) -> bool:
    return getattr(agent, "model", "").lower() == "human"


class HumanInputProvider(Protocol):
    async def choose_seat(
        self,
        *,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        allow_skip: bool,
        context: str,
    ) -> PlayerProtocol | None: ...

    async def choose_yes_no(self, *, role_name: str, question: str, context: str) -> bool: ...

    async def choose_witch_action(
        self,
        *,
        role_name: str,
        can_see_victim: bool,
        victim_line: str | None,
        poison_targets: list[PlayerProtocol],
        context: str,
    ) -> WitchNightDecision: ...

    async def choose_multi_targets(
        self,
        *,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        num_targets: int,
        context: str,
    ) -> list[PlayerProtocol]: ...

    async def speak(
        self,
        *,
        context: str,
        instruction: str,
        phase: str,
        round_number: int,
    ) -> SpeechDecision: ...


class ShellHumanInputProvider:
    def __init__(
        self,
        input_fn: Callable[[str], str] = input,
        write_fn: Callable[[str], None] = print,
    ) -> None:
        self._input = input_fn
        self._write = write_fn

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

        self._write("")
        self._write(f"[{role_name}] {context}")
        self._write(action_description)
        if allow_skip:
            self._write("0. 跳过")
        for seat, player in sorted(target_by_seat.items()):
            self._write(f"{seat}. {player.name}")

        while True:
            answer = self._input("请输入编号: ").strip()
            if not answer.isdigit():
                self._write("请输入数字编号。")
                continue

            seat = int(answer)
            if allow_skip and seat == 0:
                return None
            if seat in target_by_seat:
                return target_by_seat[seat]

            self._write("编号不在可选范围内，请重试。")

    async def choose_yes_no(self, *, role_name: str, question: str, context: str) -> bool:
        self._write("")
        self._write(f"[{role_name}] {context}")
        self._write(question)
        self._write("1. 是")
        self._write("2. 否")

        while True:
            answer = self._input("请输入编号: ").strip()
            if answer == "1":
                return True
            if answer == "2":
                return False
            self._write("请输入 1 或 2。")

    async def choose_witch_action(
        self,
        *,
        role_name: str,
        can_see_victim: bool,
        victim_line: str | None,
        poison_targets: list[PlayerProtocol],
        context: str,
    ) -> WitchNightDecision:
        self._write("")
        self._write(f"[{role_name}] {context}")
        if can_see_victim and victim_line:
            self._write(victim_line)

        options: list[tuple[str, str]] = []
        if can_see_victim:
            options.append(("save", "使用解药"))
        if poison_targets:
            options.append(("poison", "使用毒药"))
        options.append(("none", "不行动"))

        for index, (_, label) in enumerate(options, start=1):
            self._write(f"{index}. {label}")

        while True:
            answer = self._input("请输入编号: ").strip()
            if not answer.isdigit():
                self._write("请输入数字编号。")
                continue

            index = int(answer) - 1
            if not 0 <= index < len(options):
                self._write("编号不在可选范围内，请重试。")
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
        self._write("")
        self._write(f"[{phase} 第 {round_number} 轮] {context}")
        self._write(instruction)

        while True:
            speech = self._input("请输入发言: ").strip()
            if speech:
                return SpeechDecision.model_construct(
                    public_speech=speech,
                    private_thought=None,
                )
            self._write("发言不能为空。")
