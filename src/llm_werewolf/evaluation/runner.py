import asyncio
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_werewolf.core import GameEngine
from llm_werewolf.core.agent import DemoAgent
from llm_werewolf.core.config import GameConfig
from llm_werewolf.core.role_registry import create_roles
from llm_werewolf.core.types import Event, EventType
from llm_werewolf.evaluation.checkers import (
    AsyncFlowChecker,
    InformationIsolationChecker,
    PromptBadCaseChecker,
    RoleSkillChecker,
    VictoryCheckerEvaluator,
)
from llm_werewolf.evaluation.metrics import build_summary
from llm_werewolf.evaluation.models import CheckResult, GameRunResult
from llm_werewolf.evaluation.recorder import EvaluationRecorder
from llm_werewolf.evaluation.reporter import EvaluationReporter
from llm_werewolf.evaluation.scenarios import EvaluationScenario


class EvaluationRunner:
    """离线评测运行器。

    runner 是整个 evaluation 包的编排层：
    1. 根据场景创建游戏。
    2. 接管事件回调并写入 recorder。
    3. 用超时保护运行 `play_game()`。
    4. 跑 checker 并生成最终报告。
    """

    def __init__(self, output_dir: str | Path, scenarios: list[EvaluationScenario]) -> None:
        self.output_dir = Path(output_dir)
        self.scenarios = scenarios
        self.games_dir = self.output_dir / "games"

    async def run(self) -> list[GameRunResult]:
        """运行所有场景并写出批量报告。"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.games_dir.mkdir(parents=True, exist_ok=True)
        self._write_manifest()

        results: list[GameRunResult] = []
        for scenario in self.scenarios:
            # repetition 用于同一场景跑多局；每局 seed 递增，保证既可复现又有变化。
            for repetition in range(scenario.repetitions):
                seed = scenario.seed + repetition
                game_id = f"{scenario.name}-{seed}-{repetition + 1}"
                results.append(await self.run_scenario(scenario, game_id=game_id, seed=seed))

        summary = build_summary(results)
        EvaluationReporter(self.output_dir).write(summary, results)
        return results

    async def run_scenario(
        self,
        scenario: EvaluationScenario,
        game_id: str,
        seed: int,
    ) -> GameRunResult:
        """运行单局游戏并返回摘要结果。

        这个方法必须保证“单局失败不影响整批评测”：
        所有超时、崩溃和 observation 构建异常都会被记录，然后继续返回 GameRunResult。
        """
        random.seed(seed)
        game_dir = self.games_dir / game_id
        recorder = EvaluationRecorder(game_dir)
        started = time.perf_counter()
        engine = self._build_engine(scenario)
        events: list[Event] = []
        observations_by_player: dict[str, str] = {}
        crashed = False
        timed_out = False
        error_type: str | None = None
        error_message: str | None = None

        def on_event(event: Event) -> None:
            # 接管 GameEngine 事件出口：内存中保留一份给 checker，磁盘写一份给复盘。
            events.append(event)
            recorder.record_event(event)

        engine.on_event = on_event
        # setup 后立即保存快照，方便确认初始角色、玩家状态和配置。
        recorder.record_snapshot(engine.game_state, label="after_setup")

        try:
            # wait_for 是异步流程正确性评测的安全网：游戏卡住会变成 timeout 产物。
            await asyncio.wait_for(engine.play_game(), timeout=scenario.timeout_seconds)
        except asyncio.TimeoutError as exc:
            timed_out = True
            error_type = type(exc).__name__
            error_message = f"Game exceeded timeout of {scenario.timeout_seconds} seconds"
            recorder.record_error(
                exc,
                phase=engine.game_state.phase.value if engine.game_state else None,
                round_number=engine.game_state.round_number if engine.game_state else None,
            )
        except Exception as exc:
            crashed = True
            error_type = type(exc).__name__
            error_message = str(exc)
            recorder.record_error(
                exc,
                phase=engine.game_state.phase.value if engine.game_state else None,
                round_number=engine.game_state.round_number if engine.game_state else None,
            )

        if engine.game_state is not None:
            for player in engine.game_state.players:
                try:
                    # 收集每个玩家最终 observation，用于检查私有事件是否泄露。
                    observations_by_player[player.player_id] = engine.build_player_observation(player)
                except Exception as exc:
                    if not crashed:
                        crashed = True
                        error_type = type(exc).__name__
                        error_message = str(exc)
                    recorder.record_error(
                        exc,
                        phase=engine.game_state.phase.value,
                        round_number=engine.game_state.round_number,
                        role_name=player.get_role_name(),
                    )

        # final 快照无论成功、崩溃还是超时都尽量保存，便于比较终局状态。
        recorder.record_snapshot(engine.game_state, label="final")
        checks = self._run_checkers(events, observations_by_player, engine)
        recorder.finalize_checks(checks)

        completed = not crashed and not timed_out and engine.game_state is not None and bool(engine.game_state.winner)
        duration = time.perf_counter() - started
        return GameRunResult(
            game_id=game_id,
            scenario_name=scenario.name,
            seed=seed,
            completed=completed,
            crashed=crashed,
            timed_out=timed_out,
            winner=engine.game_state.winner if engine.game_state else None,
            rounds_played=engine.game_state.round_number if engine.game_state else 0,
            duration_seconds=duration,
            error_type=error_type,
            error_message=error_message,
            checks=checks,
        )

    def _build_engine(self, scenario: EvaluationScenario) -> GameEngine:
        """按场景构建一局离线游戏。

        第一版固定使用 DemoAgent，避免真实模型 API 成本和随机延迟影响系统正确性评测。
        """
        config = GameConfig(
            num_players=scenario.num_players,
            role_names=scenario.role_names,
        )
        agents = [
            DemoAgent(name=f"EvalPlayer{i}", model="demo")
            for i in range(1, scenario.num_players + 1)
        ]
        roles = create_roles(config.role_names)
        engine = GameEngine(config, language=scenario.language)
        engine.setup_game(players=agents, roles=roles)
        return engine

    def _run_checkers(
        self,
        events: list[Event],
        observations_by_player: dict[str, str],
        engine: GameEngine,
    ) -> list[CheckResult]:
        """运行所有正确性 checker。

        checker 自身不应该让评测中断；如果 checker 代码抛异常，也会转成失败结果。
        """
        final_winner = engine.game_state.winner if engine.game_state else None
        player_roles = {}
        player_camps = {}
        if engine.game_state:
            player_roles = {
                player.player_id: player.get_role_name() for player in engine.game_state.players
            }
            player_camps = {
                player.player_id: player.get_camp() for player in engine.game_state.players
            }
        checks: list[CheckResult] = []
        checkers: list[tuple[Any, dict[str, Any]]] = [
            (RoleSkillChecker(), {"events": events}),
            (
                InformationIsolationChecker(),
                {"events": events, "observations_by_player": observations_by_player},
            ),
            (VictoryCheckerEvaluator(), {"events": events, "final_winner": final_winner}),
            (AsyncFlowChecker(), {"events": events}),
            (
                PromptBadCaseChecker(),
                {
                    "events": events,
                    "player_roles": player_roles,
                    "player_camps": player_camps,
                },
            ),
        ]

        for checker, kwargs in checkers:
            try:
                checks.extend(checker.check(**kwargs))
            except Exception as exc:
                checks.append(
                    CheckResult(
                        checker=checker.__class__.__name__,
                        passed=False,
                        message=f"Checker raised {type(exc).__name__}: {exc}",
                    )
                )

        checks.extend(self._error_event_checks(events))
        return checks

    def _error_event_checks(self, events: list[Event]) -> list[CheckResult]:
        """把游戏内部记录的 ERROR 事件转成评测失败。

        有些角色动作异常会被引擎捕获并记录为 EventType.ERROR，不会导致 play_game 崩溃。
        如果不把这些事件纳入 checks，报告会误以为该局完全健康。
        """
        results: list[CheckResult] = []
        for event in events:
            if event.event_type != EventType.ERROR:
                continue
            role_name = event.data.get("role") or event.data.get("role_name")
            results.append(
                CheckResult(
                    checker="RuntimeErrorEventChecker",
                    passed=False,
                    message=event.data.get("error", event.message),
                    data={
                        "phase": event.phase,
                        "round_number": event.round_number,
                        "player_id": event.data.get("player_id"),
                        "role_name": role_name,
                        "error_type": event.data.get("error_type"),
                    },
                )
            )
        return results

    def _write_manifest(self) -> None:
        """写本次评测批次的元数据，记录场景和创建时间。"""
        payload = {
            "created_at": datetime.now().isoformat(),
            "scenarios": [scenario.model_dump(mode="json") for scenario in self.scenarios],
        }
        (self.output_dir / "manifest.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
