# CLI Human vs LLM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a usable CLI/shell mode where one human player can play against LLM players by entering only numbers for decisions and plain text for speeches.

**Architecture:** Add a dedicated human input provider and route human decisions through it before the LLM bridge. Keep AgentScope / MsgHub for LLM memory, but decouple real roundtable speech collection from AgentScope participant filtering so human speech is never skipped.

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio, pydantic, rich, existing `llm_werewolf` runtime.

---

## File Structure

- Create: `src/llm_werewolf/interface/human_input.py`
  - Owns `HumanInputProvider`, `ShellHumanInputProvider`, and `is_human_agent`.
  - No game-rule execution. It only displays choices, reads shell input, validates, and returns decision objects.
- Modify: `src/llm_werewolf/game_runtime/phase_interaction.py`
  - Adds provider injection and routes human decisions to provider.
- Modify: `src/llm_werewolf/agent_team/information_hub.py`
  - Lets `run_roundtable()` collect human speaker text even when no AgentScope participants exist.
  - Broadcasts collected public speeches to LLM participants when present.
- Modify: `src/llm_werewolf/interface/modes.py`
  - Adds `human_mixed / badge_flow`.
- Modify: `src/llm_werewolf/interface/cli.py`
  - Injects `ShellHumanInputProvider` in human mixed mode.
  - Switches presenter to the single human player's `viewer_id`.
- Modify: `src/llm_werewolf/ui/console_presenter.py`
  - Shows visible private night events to the human viewer instead of swallowing them all.
- Create: `configs/human-mixed-deepseek.yaml`
  - 1 human player and 11 DeepSeek players.
- Create/modify tests:
  - `tests/interface/test_human_input.py`
  - `tests/game_runtime/test_phase_interaction_human.py`
  - `tests/agent_team/test_information_hub_human_roundtable.py`
  - `tests/ui/test_console_presenter.py`
  - `tests/interface/test_modes.py`
  - `tests/interface/test_cli_human_mode.py`

---

### Task 1: Shell Human Input Provider

**Files:**
- Create: `tests/interface/test_human_input.py`
- Create: `src/llm_werewolf/interface/human_input.py`

- [ ] **Step 1: Write failing provider tests**

Create `tests/interface/test_human_input.py` with:

```python
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles.villager import Villager
from llm_werewolf.interface.human_input import ShellHumanInputProvider, is_human_agent
from llm_werewolf.agent_team.base import HumanAgent, DemoAgent


def _players() -> list[Player]:
    return [
        Player("player_1", "Human", Villager),
        Player("player_2", "Bot2", Villager),
        Player("player_3", "Bot3", Villager),
    ]


def _provider_with_answers(*answers: str) -> ShellHumanInputProvider:
    iterator = iter(answers)
    return ShellHumanInputProvider(
        input_fn=lambda _prompt: next(iterator),
        write_fn=lambda _line: None,
    )


async def test_choose_seat_retries_until_valid_seat() -> None:
    provider = _provider_with_answers("abc", "9", "2")
    targets = _players()[1:]

    selected = await provider.choose_seat(
        role_name="Guard",
        action_description="选择一名玩家守护",
        possible_targets=targets,
        allow_skip=False,
        context="你是守卫。",
    )

    assert selected == targets[0]


async def test_choose_seat_returns_none_when_skip_allowed() -> None:
    provider = _provider_with_answers("0")

    selected = await provider.choose_seat(
        role_name="Villager",
        action_description="投票",
        possible_targets=_players()[1:],
        allow_skip=True,
        context="白天投票。",
    )

    assert selected is None


async def test_speak_accepts_plain_short_text_without_brackets() -> None:
    provider = _provider_with_answers("我觉得2号比较可疑")

    decision = await provider.speak(
        context="白天讨论。",
        instruction="请发言。",
        phase="day_discussion",
        round_number=1,
    )

    assert decision.public_speech == "我觉得2号比较可疑"
    assert decision.private_thought is None


async def test_choose_yes_no_uses_numbered_options() -> None:
    provider = _provider_with_answers("x", "2")

    selected = await provider.choose_yes_no(
        role_name="Blood Moon Apostle",
        question="是否变身？",
        context="队友已阵亡。",
    )

    assert selected is False


async def test_choose_witch_action_poison_then_target() -> None:
    provider = _provider_with_answers("2", "3")
    targets = _players()[1:]

    decision = await provider.choose_witch_action(
        role_name="Witch",
        can_see_victim=True,
        victim_line="今晚狼人刀口：Bot2（2号）。",
        poison_targets=targets,
        context="解药：可用。毒药：可用。",
    )

    assert decision.action == "poison"
    assert decision.seat == 3


async def test_choose_multi_targets_collects_distinct_targets() -> None:
    provider = _provider_with_answers("2", "2", "3")
    targets = _players()

    selected = await provider.choose_multi_targets(
        role_name="Cupid",
        action_description="选择两名玩家结为情侣",
        possible_targets=targets,
        num_targets=2,
        context="首夜行动。",
    )

    assert [player.player_id for player in selected] == ["player_2", "player_3"]


def test_is_human_agent_checks_model_name() -> None:
    assert is_human_agent(HumanAgent(name="Human", model="human"))
    assert not is_human_agent(DemoAgent(name="Bot", model="demo"))
    assert not is_human_agent(None)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
pytest tests\interface\test_human_input.py -q
```

Expected: FAIL because `llm_werewolf.interface.human_input` does not exist.

- [ ] **Step 3: Implement `human_input.py`**

Create `src/llm_werewolf/interface/human_input.py`:

```python
"""Shell input support for human-controlled CLI players."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TYPE_CHECKING

from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.strategy.decisions import SpeechDecision, WitchNightDecision

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import AgentProtocol, PlayerProtocol


def is_human_agent(agent: AgentProtocol | None) -> bool:
    """Return whether an agent represents a shell human."""
    return bool(agent and getattr(agent, "model", "").lower() == "human")


class HumanInputProvider(Protocol):
    """Input contract used by runtime code when the actor is human."""

    async def choose_seat(
        self,
        *,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        allow_skip: bool,
        context: str = "",
    ) -> PlayerProtocol | None:
        ...

    async def choose_yes_no(
        self,
        *,
        role_name: str,
        question: str,
        context: str = "",
    ) -> bool:
        ...

    async def choose_witch_action(
        self,
        *,
        role_name: str,
        can_see_victim: bool,
        victim_line: str,
        poison_targets: list[PlayerProtocol],
        context: str = "",
    ) -> WitchNightDecision:
        ...

    async def choose_multi_targets(
        self,
        *,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        num_targets: int,
        context: str = "",
    ) -> list[PlayerProtocol]:
        ...

    async def speak(
        self,
        *,
        context: str,
        instruction: str = "",
        phase: str = "",
        round_number: int = 0,
    ) -> SpeechDecision:
        ...


class ShellHumanInputProvider:
    """Blocking shell implementation for one local human player."""

    def __init__(
        self,
        *,
        input_fn: Callable[[str], str] = input,
        write_fn: Callable[[str], None] | None = None,
    ) -> None:
        self._input_fn = input_fn
        self._write_fn = write_fn or print

    def _write(self, line: str = "") -> None:
        self._write_fn(line)

    def _prompt(self) -> str:
        return self._input_fn("> ").strip()

    @staticmethod
    def _seat(player: PlayerProtocol) -> int:
        return WerewolfAdapterBridge.get_player_seat(player) or 0

    def _show_context(self, context: str) -> None:
        if context.strip():
            self._write(context.strip())

    def _show_targets(self, possible_targets: list[PlayerProtocol], allow_skip: bool) -> None:
        self._write("可选目标：")
        if allow_skip:
            self._write("0. 跳过/弃票")
        for player in possible_targets:
            status = "存活" if player.is_alive() else "死亡"
            self._write(f"{self._seat(player)}号 {player.name} {status}")

    async def choose_seat(
        self,
        *,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        allow_skip: bool,
        context: str = "",
    ) -> PlayerProtocol | None:
        self._write(f"\n[{role_name}] {action_description}")
        self._show_context(context)
        self._show_targets(possible_targets, allow_skip)
        valid = {self._seat(player): player for player in possible_targets}
        while True:
            raw = self._prompt()
            if not raw.isdigit():
                self._write("请输入数字。")
                continue
            seat = int(raw)
            if seat == 0 and allow_skip:
                return None
            if seat == 0:
                self._write("该行动必须选择目标，不能输入 0。")
                continue
            target = valid.get(seat)
            if target is not None:
                return target
            seats = ", ".join(str(number) for number in sorted(valid))
            self._write(f"目标不在候选范围内。有效座位：{seats}。")

    async def choose_yes_no(
        self,
        *,
        role_name: str,
        question: str,
        context: str = "",
    ) -> bool:
        self._write(f"\n[{role_name}] {question}")
        self._show_context(context)
        self._write("1. 是")
        self._write("2. 否")
        while True:
            raw = self._prompt()
            if raw == "1":
                return True
            if raw == "2":
                return False
            self._write("请输入 1 或 2。")

    async def choose_witch_action(
        self,
        *,
        role_name: str,
        can_see_victim: bool,
        victim_line: str,
        poison_targets: list[PlayerProtocol],
        context: str = "",
    ) -> WitchNightDecision:
        self._write(f"\n[{role_name}] 女巫行动")
        self._show_context(context)
        if victim_line.strip():
            self._write(victim_line.strip())
        actions: dict[str, str] = {}
        index = 1
        if can_see_victim:
            actions[str(index)] = "save"
            self._write(f"{index}. 使用解药")
            index += 1
        if poison_targets:
            actions[str(index)] = "poison"
            self._write(f"{index}. 使用毒药")
            index += 1
        actions[str(index)] = "none"
        self._write(f"{index}. 不行动")

        while True:
            raw = self._prompt()
            action = actions.get(raw)
            if action is None:
                self._write("请输入菜单中的数字。")
                continue
            if action == "save":
                return WitchNightDecision(action="save", seat=0, reason=None)
            if action == "none":
                return WitchNightDecision(action="none", seat=0, reason=None)
            target = await self.choose_seat(
                role_name=role_name,
                action_description="选择毒药目标",
                possible_targets=poison_targets,
                allow_skip=False,
                context="",
            )
            return WitchNightDecision(action="poison", seat=self._seat(target), reason=None)

    async def choose_multi_targets(
        self,
        *,
        role_name: str,
        action_description: str,
        possible_targets: list[PlayerProtocol],
        num_targets: int,
        context: str = "",
    ) -> list[PlayerProtocol]:
        selected: list[PlayerProtocol] = []
        for index in range(1, num_targets + 1):
            remaining = [
                player
                for player in possible_targets
                if player.player_id not in {chosen.player_id for chosen in selected}
            ]
            target = await self.choose_seat(
                role_name=role_name,
                action_description=f"{action_description}：请选择第 {index} 个目标",
                possible_targets=remaining,
                allow_skip=False,
                context=context if index == 1 else "",
            )
            selected.append(target)
        return selected

    async def speak(
        self,
        *,
        context: str,
        instruction: str = "",
        phase: str = "",
        round_number: int = 0,
    ) -> SpeechDecision:
        self._write(f"\n[发言] 第 {round_number} 轮 {phase}")
        self._show_context(context)
        if instruction.strip():
            self._write(instruction.strip())
        self._write("请输入发言内容：")
        while True:
            speech = self._prompt()
            if speech:
                return SpeechDecision.model_construct(
                    public_speech=speech,
                    private_thought=None,
                )
            self._write("发言不能为空，请重新输入。")
```

- [ ] **Step 4: Run provider tests**

Run:

```powershell
pytest tests\interface\test_human_input.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit provider task**

Run:

```powershell
git add src\llm_werewolf\interface\human_input.py tests\interface\test_human_input.py
git commit -m "feat: add shell human input provider"
```

---

### Task 2: PhaseInteraction Human Routing

**Files:**
- Create: `tests/game_runtime/test_phase_interaction_human.py`
- Modify: `src/llm_werewolf/game_runtime/phase_interaction.py`

- [ ] **Step 1: Write failing PhaseInteraction tests**

Create `tests/game_runtime/test_phase_interaction_human.py`:

```python
from unittest.mock import AsyncMock

from llm_werewolf.agent_team.base import DemoAgent, HumanAgent
from llm_werewolf.game_runtime.phase_interaction import PhaseInteraction
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles.villager import Villager
from llm_werewolf.strategy.decisions import SpeechDecision, WitchNightDecision


class FakeHumanInputProvider:
    def __init__(self, target):
        self.target = target

    async def choose_seat(self, **_kwargs):
        return self.target

    async def choose_yes_no(self, **_kwargs):
        return True

    async def choose_witch_action(self, **_kwargs):
        return WitchNightDecision(action="none", seat=0, reason=None)

    async def choose_multi_targets(self, **_kwargs):
        return [self.target]

    async def speak(self, **_kwargs):
        return SpeechDecision.model_construct(public_speech="我是人类发言", private_thought=None)


def _player(player_id: str, name: str, agent):
    return Player(player_id, name, Villager, agent=agent, ai_model=agent.model)


async def test_human_seat_choice_uses_provider_not_hub() -> None:
    human = _player("player_1", "Human", HumanAgent(name="Human", model="human"))
    target = _player("player_2", "Bot2", DemoAgent(name="Bot2", model="demo"))
    hub = AsyncMock()
    interaction = PhaseInteraction(hub)
    interaction.set_human_input_provider(FakeHumanInputProvider(target))

    selected = await interaction.request_seat_choice(
        human,
        human.agent,
        "Guard",
        "守护一名玩家",
        [target],
    )

    assert selected == target
    hub.request_private_seat_choice.assert_not_called()


async def test_llm_seat_choice_still_uses_hub() -> None:
    actor = _player("player_1", "Bot1", DemoAgent(name="Bot1", model="demo"))
    target = _player("player_2", "Bot2", DemoAgent(name="Bot2", model="demo"))
    hub = AsyncMock()
    hub.request_private_seat_choice.return_value = target
    interaction = PhaseInteraction(hub)

    selected = await interaction.request_seat_choice(
        actor,
        actor.agent,
        "Guard",
        "守护一名玩家",
        [target],
    )

    assert selected == target
    hub.request_private_seat_choice.assert_awaited_once()


async def test_human_speech_uses_provider() -> None:
    human = _player("player_1", "Human", HumanAgent(name="Human", model="human"))
    target = _player("player_2", "Bot2", DemoAgent(name="Bot2", model="demo"))
    interaction = PhaseInteraction(AsyncMock())
    interaction.set_human_input_provider(FakeHumanInputProvider(target))

    decision = await interaction.request_speech(
        human,
        human.agent,
        context="白天讨论",
        instruction="请发言",
        phase="day_discussion",
        round_number=1,
    )

    assert decision.public_speech == "我是人类发言"


async def test_human_branch_without_provider_raises_clear_error() -> None:
    human = _player("player_1", "Human", HumanAgent(name="Human", model="human"))
    interaction = PhaseInteraction(AsyncMock())

    try:
        await interaction.request_yes_no(
            human,
            human.agent,
            role_name="Blood Moon Apostle",
            question="是否变身？",
        )
    except RuntimeError as exc:
        assert "HumanInputProvider" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
pytest tests\game_runtime\test_phase_interaction_human.py -q
```

Expected: FAIL because `PhaseInteraction.set_human_input_provider` does not exist.

- [ ] **Step 3: Modify `PhaseInteraction`**

In `src/llm_werewolf/game_runtime/phase_interaction.py`, add imports:

```python
from llm_werewolf.interface.human_input import HumanInputProvider, is_human_agent
```

Update the class constructor and add helpers:

```python
    def __init__(
        self,
        hub: InformationHub,
        human_input_provider: HumanInputProvider | None = None,
    ) -> None:
        self._hub = hub
        self._human_input_provider = human_input_provider

    def set_human_input_provider(self, provider: HumanInputProvider | None) -> None:
        self._human_input_provider = provider

    def _require_human_input_provider(self) -> HumanInputProvider:
        if self._human_input_provider is None:
            msg = "HumanInputProvider is required for human-controlled players"
            raise RuntimeError(msg)
        return self._human_input_provider
```

At the start of `request_seat_choice()` insert:

```python
        if is_human_agent(agent):
            return await self._require_human_input_provider().choose_seat(
                role_name=role_name,
                action_description=action_description,
                possible_targets=possible_targets,
                allow_skip=allow_skip,
                context=additional_context,
            )
```

At the start of `request_witch_night_choice()` insert:

```python
        if is_human_agent(agent):
            return await self._require_human_input_provider().choose_witch_action(
                role_name=role_name,
                can_see_victim=can_see_victim,
                victim_line=victim_line,
                poison_targets=poison_targets,
                context=additional_context,
            )
```

At the start of `request_yes_no()` insert:

```python
        if is_human_agent(agent):
            return await self._require_human_input_provider().choose_yes_no(
                role_name=role_name,
                question=question,
                context=context,
            )
```

At the start of `request_multi_targets()` insert:

```python
        if is_human_agent(agent):
            return await self._require_human_input_provider().choose_multi_targets(
                role_name=role_name,
                action_description=action_description,
                possible_targets=possible_targets,
                num_targets=num_targets,
                context=additional_context,
            )
```

At the start of `request_speech()` insert:

```python
        if is_human_agent(agent):
            return await self._require_human_input_provider().speak(
                context=context,
                instruction=instruction,
                phase=phase,
                round_number=round_number,
            )
```

Update the `run_roundtable()` call to pass the provider:

```python
        return await self._hub.run_roundtable(
            speakers,
            channel=channel,
            context_builder=context_builder,
            instruction=instruction,
            phase=phase,
            round_number=round_number,
            audience=audience,
            opening_announcement=opening_announcement,
            on_speech=on_speech,
            vote_intention_tracker=vote_intention_tracker,
            on_vote_intention_record=on_vote_intention_record,
            human_input_provider=self._human_input_provider,
        )
```

- [ ] **Step 4: Run PhaseInteraction tests**

Run:

```powershell
pytest tests\game_runtime\test_phase_interaction_human.py -q
```

Expected: PASS.

- [ ] **Step 5: Run existing action selector tests**

Run:

```powershell
pytest tests\game_runtime\test_action_selector.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit PhaseInteraction task**

Run:

```powershell
git add src\llm_werewolf\game_runtime\phase_interaction.py tests\game_runtime\test_phase_interaction_human.py
git commit -m "feat: route human decisions through input provider"
```

---

### Task 3: Human Roundtable Speech in InformationHub

**Files:**
- Create: `tests/agent_team/test_information_hub_human_roundtable.py`
- Modify: `src/llm_werewolf/agent_team/information_hub.py`

- [ ] **Step 1: Write failing roundtable tests**

Create `tests/agent_team/test_information_hub_human_roundtable.py`:

```python
from llm_werewolf.agent_team.base import HumanAgent
from llm_werewolf.agent_team.information_hub import InformationHub
from llm_werewolf.agent_team.visibility import VisibilityChannel
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles.villager import Villager
from llm_werewolf.strategy.decisions import SpeechDecision


class FakeSpeechProvider:
    async def speak(self, **_kwargs):
        return SpeechDecision.model_construct(
            public_speech="我是人类玩家的公开发言",
            private_thought=None,
        )


def _human_player() -> Player:
    agent = HumanAgent(name="Human", model="human")
    return Player("player_1", "Human", Villager, agent=agent, ai_model="human")


async def test_roundtable_calls_human_speaker_even_without_react_agents() -> None:
    player = _human_player()
    hub = InformationHub()
    hub.set_context_provider(
        build_observation=lambda _player: "filtered observation",
        get_alive_players=lambda: [player],
    )
    speeches = []

    routed = await hub.run_roundtable(
        [player],
        channel=VisibilityChannel.PUBLIC,
        context_builder=lambda _speaker: "context",
        instruction="请发言",
        phase="day_discussion",
        round_number=1,
        on_speech=lambda speaker, decision, route: speeches.append(
            (speaker, decision.public_speech, route)
        ),
        human_input_provider=FakeSpeechProvider(),
    )

    assert routed == []
    assert speeches == [(player, "我是人类玩家的公开发言", None)]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
pytest tests\agent_team\test_information_hub_human_roundtable.py -q
```

Expected: FAIL because `run_roundtable()` does not accept `human_input_provider`.

- [ ] **Step 3: Modify `InformationHub.run_roundtable()` signature**

Add imports:

```python
from llm_werewolf.interface.human_input import HumanInputProvider, is_human_agent
```

Update the signature:

```python
        on_vote_intention_record: Callable[[SpeechVoteIntentionRecord], None]
        | None = None,
        human_input_provider: HumanInputProvider | None = None,
    ) -> list[RoutedMessage]:
```

- [ ] **Step 4: Split real audience from MsgHub participants**

Replace the initial audience block in `run_roundtable()` with:

```python
        alive = self._get_alive_players() if self._get_alive_players else []
        audience_players = MessageRouter.resolve_audience_players(
            channel,
            alive,
            custom_audience=audience,
        )
        msg_hub_players = [
            player for player in audience_players if self._react_agent(player) is not None
        ]
        react_agents = [
            agent for agent in (self._react_agent(player) for player in msg_hub_players) if agent
        ]
```

Use `msg_hub_players` for `_collect_vote_intentions()` so human players are not asked for private vote-intention analysis:

```python
                prior_intentions = await self._collect_vote_intentions(
                    msg_hub_players,
                    anchor=VoteIntentionAnchor.INITIAL,
                    context_builder=context_builder,
                    phase=phase,
                    round_number=round_number,
                )
```

And later:

```python
                    after_intentions = await self._collect_vote_intentions(
                        msg_hub_players,
                        anchor=VoteIntentionAnchor.AFTER_SPEECH,
                        context_builder=context_builder,
                        phase=phase,
                        round_number=round_number,
                        last_speaker=speaker,
                    )
```

- [ ] **Step 5: Add a human-aware speech collector inside `run_roundtable()`**

Inside `run_roundtable()`, before opening MsgHub, add:

```python
        async def _speaker_decision(speaker: PlayerProtocol) -> SpeechDecision:
            context = context_builder(speaker)
            context = "\n\n".join([
                context,
                EngineContexts.hub_roundtable_memory_notice(channel.value),
            ])
            if speaker.agent is not None and is_human_agent(speaker.agent):
                if human_input_provider is None:
                    msg = "HumanInputProvider is required for human roundtable speech"
                    raise RuntimeError(msg)
                return await human_input_provider.speak(
                    context=context,
                    instruction=instruction,
                    phase=phase,
                    round_number=round_number,
                )

            from llm_werewolf.strategy.phase_outputs import resolve_roundtable_phase

            rt_phase = resolve_roundtable_phase(
                channel=channel.value,
                phase=phase,
            )
            return await WerewolfAdapterBridge.request_speech(
                speaker.agent,
                context,
                instruction,
                roundtable_phase=rt_phase,
            )
```

- [ ] **Step 6: Remove the early return and run speakers with optional hub**

Replace `if not react_agents: return routed_messages` and the speaker loop with this structure:

```python
        async def _run_speaker_loop(hub: MsgHub | None) -> None:
            prior_intentions: dict[str, VoteIntentionEntry] = {}
            if hub is not None and vote_intention_tracker is not None:
                prior_intentions = await self._collect_vote_intentions(
                    msg_hub_players,
                    anchor=VoteIntentionAnchor.INITIAL,
                    context_builder=context_builder,
                    phase=phase,
                    round_number=round_number,
                )
                vote_intention_tracker.add_snapshot(
                    VoteIntentionSnapshot(
                        round_number=round_number,
                        phase=phase,
                        channel=channel.value,
                        anchor=VoteIntentionAnchor.INITIAL,
                        speaker_id="",
                        speaker_name="（讨论开始）",
                        intentions=prior_intentions,
                    )
                )

            for speaker in speakers:
                if not speaker.is_alive() or speaker.agent is None:
                    continue

                decision = await _speaker_decision(speaker)
                react_self = self._react_agent(speaker)
                routed: RoutedMessage | None = None

                if hub is not None and react_self and decision.private_thought:
                    await self._deliver_private(react_self, speaker.name, decision.private_thought)

                if decision.public_speech.strip():
                    if hub is not None:
                        routed = await self._broadcast_public(
                            hub,
                            speaker,
                            decision.public_speech.strip(),
                            channel,
                            phase,
                            round_number,
                            audience_players,
                        )
                        routed.private_thought = decision.private_thought
                        routed_messages.append(routed)

                if speaker.agent:
                    speaker.agent.add_decision(
                        f"Round {round_number} ({channel.value}): "
                        f"You said: {decision.public_speech}"
                    )

                if on_speech:
                    on_speech(speaker, decision, routed)

                if hub is not None and vote_intention_tracker is not None:
                    after_intentions = await self._collect_vote_intentions(
                        msg_hub_players,
                        anchor=VoteIntentionAnchor.AFTER_SPEECH,
                        context_builder=context_builder,
                        phase=phase,
                        round_number=round_number,
                        last_speaker=speaker,
                    )
                    record = vote_intention_tracker.record_speech_block(
                        round_number=round_number,
                        phase=phase,
                        channel=channel.value,
                        speaker=speaker,
                        public_speech=decision.public_speech.strip(),
                        before=prior_intentions,
                        after=after_intentions,
                    )
                    prior_intentions = after_intentions
                    if on_vote_intention_record:
                        on_vote_intention_record(record)

        if react_agents:
            async with MsgHub(
                participants=react_agents,
                enable_auto_broadcast=False,
                name=f"roundtable-{channel.value}-r{round_number}",
            ) as hub:
                if opening_announcement:
                    await self._broadcast_moderator(
                        hub,
                        opening_announcement,
                        channel=channel,
                        phase=phase,
                        round_number=round_number,
                    )
                await _run_speaker_loop(hub)
        else:
            await _run_speaker_loop(None)

        return routed_messages
```

When applying this snippet, preserve the existing `on_vote_intention_record` initial snapshot behavior if the project still needs that replay line. The key behavior is that human speaker collection must run even when `react_agents` is empty.

- [ ] **Step 7: Run roundtable tests**

Run:

```powershell
pytest tests\agent_team\test_information_hub_human_roundtable.py -q
```

Expected: PASS.

- [ ] **Step 8: Run hub context tests**

Run:

```powershell
pytest tests\game_runtime\test_hub_decision_context.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit roundtable task**

Run:

```powershell
git add src\llm_werewolf\agent_team\information_hub.py tests\agent_team\test_information_hub_human_roundtable.py
git commit -m "fix: include human speakers in roundtable"
```

---

### Task 4: CLI Mode, Human Viewer, and Config

**Files:**
- Modify: `tests/interface/test_modes.py`
- Create: `tests/interface/test_cli_human_mode.py`
- Create: `tests/ui/test_console_presenter.py`
- Modify: `src/llm_werewolf/interface/modes.py`
- Modify: `src/llm_werewolf/interface/cli.py`
- Modify: `src/llm_werewolf/ui/console_presenter.py`
- Create: `configs/human-mixed-deepseek.yaml`

- [ ] **Step 1: Add mode and presenter tests**

Append to `tests/interface/test_modes.py`:

```python
def test_human_mixed_badge_flow_resolves_deepseek_config() -> None:
    assert resolve_config_path(participation="human_mixed", rules="badge_flow") == Path(
        "configs/human-mixed-deepseek.yaml"
    )
```

Create `tests/interface/test_cli_human_mode.py`:

```python
from unittest.mock import MagicMock

import pytest

from llm_werewolf.agent_team.base import DemoAgent, HumanAgent
from llm_werewolf.game_runtime.player import Player
from llm_werewolf.game_runtime.roles.villager import Villager
from llm_werewolf.interface.cli import _find_single_human_player


def _player(player_id: str, name: str, agent):
    return Player(player_id, name, Villager, agent=agent, ai_model=agent.model)


def test_find_single_human_player_returns_only_human() -> None:
    human = _player("player_1", "Human", HumanAgent(name="Human", model="human"))
    bot = _player("player_2", "Bot", DemoAgent(name="Bot", model="demo"))
    game_state = MagicMock(players=[human, bot])

    assert _find_single_human_player(game_state) == human


def test_find_single_human_player_rejects_missing_human() -> None:
    bot = _player("player_2", "Bot", DemoAgent(name="Bot", model="demo"))
    game_state = MagicMock(players=[bot])

    with pytest.raises(ValueError, match="exactly one human"):
        _find_single_human_player(game_state)


def test_find_single_human_player_rejects_multiple_humans() -> None:
    first = _player("player_1", "Human1", HumanAgent(name="Human1", model="human"))
    second = _player("player_2", "Human2", HumanAgent(name="Human2", model="human"))
    game_state = MagicMock(players=[first, second])

    with pytest.raises(ValueError, match="exactly one human"):
        _find_single_human_player(game_state)
```

Create `tests/ui/test_console_presenter.py`:

```python
from llm_werewolf.game_runtime.types import Event, EventType, GamePhase
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.ui import console_presenter as presenter_module
from llm_werewolf.ui.console_presenter import ConsolePresenter


def test_human_viewer_sees_own_private_night_event(monkeypatch) -> None:
    printed: list[str] = []
    monkeypatch.setattr(
        presenter_module.console,
        "print",
        lambda *args, **_kwargs: printed.append(" ".join(str(arg) for arg in args)),
    )
    presenter = ConsolePresenter(Locale("zh-CN"))
    event = Event(
        event_type=EventType.SEER_CHECKED,
        round_number=1,
        phase=GamePhase.NIGHT,
        message="预言家查验了 2 号，结果为好人。",
        data={"player_id": "player_1"},
        visible_to=["player_1"],
    )

    presenter.present_event(event, viewer_id="player_1")

    assert any("预言家查验" in line for line in printed)


def test_human_viewer_does_not_see_other_private_event(monkeypatch) -> None:
    printed: list[str] = []
    monkeypatch.setattr(
        presenter_module.console,
        "print",
        lambda *args, **_kwargs: printed.append(" ".join(str(arg) for arg in args)),
    )
    presenter = ConsolePresenter(Locale("zh-CN"))
    event = Event(
        event_type=EventType.SEER_CHECKED,
        round_number=1,
        phase=GamePhase.NIGHT,
        message="预言家查验了 2 号，结果为好人。",
        data={"player_id": "player_2"},
        visible_to=["player_2"],
    )

    presenter.present_event(event, viewer_id="player_1")

    assert printed == []
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
pytest tests\interface\test_modes.py tests\interface\test_cli_human_mode.py tests\ui\test_console_presenter.py -q
```

Expected: FAIL because the mode, CLI helper, and private night display behavior are missing.

- [ ] **Step 3: Add human_mixed mode**

In `src/llm_werewolf/interface/modes.py`, add this entry to `_MODE_CONFIGS`:

```python
    (
        "human_mixed",
        "badge_flow",
    ): GameMode(
        participation="human_mixed",
        rules="badge_flow",
        config_path=Path("configs/human-mixed-deepseek.yaml"),
        description="12 人 CLI 人类玩家 + DeepSeek LLM 对局。",
    ),
```

- [ ] **Step 4: Add DeepSeek human mixed config**

Create `configs/human-mixed-deepseek.yaml`:

```yaml
language: zh-CN
agent_backend: agentscope
default_plan: default

players:
  - name: HumanPlayer
    model: human
  - name: Player2
    model: deepseek-v4-flash
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
  - name: Player3
    model: deepseek-v4-flash
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
  - name: Player4
    model: deepseek-v4-flash
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
  - name: Player5
    model: deepseek-v4-flash
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
  - name: Player6
    model: deepseek-v4-flash
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
  - name: Player7
    model: deepseek-v4-flash
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
  - name: Player8
    model: deepseek-v4-flash
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
  - name: Player9
    model: deepseek-v4-flash
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
  - name: Player10
    model: deepseek-v4-flash
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
  - name: Player11
    model: deepseek-v4-flash
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
  - name: Player12
    model: deepseek-v4-flash
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
```

- [ ] **Step 5: Add CLI helper and provider injection**

In `src/llm_werewolf/interface/cli.py`, add imports:

```python
from llm_werewolf.interface.human_input import ShellHumanInputProvider, is_human_agent
from llm_werewolf.game_runtime.types import PlayerProtocol
```

Add helper near `_run_main()`:

```python
def _find_single_human_player(game_state) -> PlayerProtocol:
    human_players = [
        player for player in game_state.players if is_human_agent(player.agent)
    ]
    if len(human_players) != 1:
        msg = "human_mixed CLI mode requires exactly one human player"
        raise ValueError(msg)
    return human_players[0]
```

In `main()`, keep `engine.on_event = presenter.present_event` before `setup_game()`, then after `wire_agentscope_after_setup(engine, players_config)` add:

```python
    if participation == "human_mixed":
        if engine.game_state is None:
            raise RuntimeError("Game state was not initialized")
        human_player = _find_single_human_player(engine.game_state)
        engine.phase_interaction.set_human_input_provider(ShellHumanInputProvider())
        engine.on_event = lambda event: presenter.present_event(
            event,
            viewer_id=human_player.player_id,
        )
```

- [ ] **Step 6: Fix human viewer night event display**

In `src/llm_werewolf/ui/console_presenter.py`, replace:

```python
        if viewer_id is not None and self._is_night_action_event(event.event_type):
            return
```

with:

```python
        if viewer_id is not None and self._is_night_action_event(event.event_type):
            console.print(event.message, style=self._get_event_style(event.event_type))
            return
```

This keeps invisible events filtered by the previous `is_visible_to()` check while showing private events that belong to the human viewer.

- [ ] **Step 7: Run mode, CLI helper, and presenter tests**

Run:

```powershell
pytest tests\interface\test_modes.py tests\interface\test_cli_human_mode.py tests\ui\test_console_presenter.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit CLI mode task**

Run:

```powershell
git add configs\human-mixed-deepseek.yaml src\llm_werewolf\interface\modes.py src\llm_werewolf\interface\cli.py src\llm_werewolf\ui\console_presenter.py tests\interface\test_modes.py tests\interface\test_cli_human_mode.py tests\ui\test_console_presenter.py
git commit -m "feat: add CLI human mixed mode"
```

---

### Task 5: Focused Regression Pass

**Files:**
- Modify only files needed to fix failures from these commands.

- [ ] **Step 1: Run focused human-mode test group**

Run:

```powershell
pytest tests\interface\test_human_input.py tests\game_runtime\test_phase_interaction_human.py tests\agent_team\test_information_hub_human_roundtable.py tests\interface\test_modes.py tests\interface\test_cli_human_mode.py tests\ui\test_console_presenter.py -q
```

Expected: PASS.

- [ ] **Step 2: Run existing affected tests**

Run:

```powershell
pytest tests\interface\test_bootstrap.py tests\agent_team\test_base.py tests\game_runtime\test_hub_decision_context.py tests\game_runtime\test_action_selector.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```powershell
pytest -q
```

Expected: PASS with coverage at or above the configured 80% threshold.

- [ ] **Step 4: Commit regression fixes if any files changed**

If Step 1-3 required fixes, run:

```powershell
git status --short
git add src\llm_werewolf tests configs
git commit -m "test: cover CLI human mixed flow"
```

Expected: the commit includes only changes made while resolving regression failures.

---

### Task 6: Codex Subagent Human Player Smoke

**Files:**
- No required code changes.
- Save run logs under `runs/` if useful.

- [ ] **Step 1: Prepare terminal encoding and API key**

Run in PowerShell:

```powershell
chcp 65001
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONUNBUFFERED='1'
if (-not $env:DEEPSEEK_API_KEY) { throw 'Set DEEPSEEK_API_KEY before smoke run' }
```

Expected: terminal accepts UTF-8 game output and DeepSeek calls can authenticate.

- [ ] **Step 2: Start CLI human mixed game**

Run:

```powershell
python -m llm_werewolf.interface.cli --participation=human_mixed --rules=badge_flow
```

Expected: game starts, asks the human player for numbered skill/decision input or plain speech when the human actor is active.

- [ ] **Step 3: Dispatch a Codex subagent as scripted human player**

Use a fresh subagent with this instruction:

```text
You are testing a CLI Werewolf game as the single human player.
Read each shell prompt and respond only as a human player would:
- If the prompt asks for a skill, vote, yes/no, or target, enter only one number.
- If the prompt asks for speech, enter one short Chinese sentence without brackets or JSON.
- When unsure, choose the first valid non-skip target.
Stop after the game has covered at least one night decision, one day speech, and one vote, or after the main agent asks you to stop.
```

Expected: the subagent enters numeric choices and plain Chinese speech without `[[...]]` or JSON.

- [ ] **Step 4: Inspect smoke output**

Check the terminal/log for these facts:

```text
Human skill/vote prompts accept bare numbers.
Human speech appears in PLAYER_SPEECH or visible discussion output.
No prompt requires [[...]], JSON, or generate_response from the human.
No human invalid input is randomly replaced by a target.
The human viewer does not see hidden role identities or unrelated private night actions.
```

Expected: all facts are true.

- [ ] **Step 5: Record smoke result**

If the smoke finds issues, write a short note in the final implementation summary and fix them before claiming completion. If no issues appear, include the command and observed coverage in the final response.

---

## Self-Review

- Spec coverage:
  - Numeric skill/vote input is covered by Task 1 and Task 2.
  - Plain speech input is covered by Task 1, Task 2, and Task 3.
  - Human speech entering roundtable events is covered by Task 3.
  - Human viewer privacy is covered by Task 4.
  - `human_mixed` startup is covered by Task 4.
  - Codex subagent human smoke is covered by Task 6.
- Placeholder scan:
  - The plan contains no placeholder sections or replacement tokens.
- Type consistency:
  - `HumanInputProvider` method names match all `PhaseInteraction` calls.
  - `WitchNightDecision` and `SpeechDecision.model_construct()` match existing decision models.
  - `human_input_provider` is passed only through `PhaseInteraction.run_roundtable()` into `InformationHub.run_roundtable()`.
