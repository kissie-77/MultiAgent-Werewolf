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
    RoleSkillChecker,
    VictoryCheckerEvaluator,
)
from llm_werewolf.evaluation.metrics import build_summary
from llm_werewolf.evaluation.models import CheckResult, GameRunResult
from llm_werewolf.evaluation.recorder import EvaluationRecorder
from llm_werewolf.evaluation.reporter import EvaluationReporter
from llm_werewolf.evaluation.scenarios import EvaluationScenario


class EvaluationRunner:
    """Runs offline game correctness evaluations."""

    def __init__(self, output_dir: str | Path, scenarios: list[EvaluationScenario]) -> None:
        self.output_dir = Path(output_dir)
        self.scenarios = scenarios
        self.games_dir = self.output_dir / "games"

    async def run(self) -> list[GameRunResult]:
        """Run all configured scenarios and write reports."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.games_dir.mkdir(parents=True, exist_ok=True)
        self._write_manifest()

        results: list[GameRunResult] = []
        for scenario in self.scenarios:
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
        """Run one game for one scenario."""
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
            events.append(event)
            recorder.record_event(event)

        engine.on_event = on_event
        recorder.record_snapshot(engine.game_state, label="after_setup")

        try:
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
        final_winner = engine.game_state.winner if engine.game_state else None
        checks: list[CheckResult] = []
        checkers: list[tuple[Any, dict[str, Any]]] = [
            (RoleSkillChecker(), {"events": events}),
            (
                InformationIsolationChecker(),
                {"events": events, "observations_by_player": observations_by_player},
            ),
            (VictoryCheckerEvaluator(), {"events": events, "final_winner": final_winner}),
            (AsyncFlowChecker(), {"events": events}),
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
        payload = {
            "created_at": datetime.now().isoformat(),
            "scenarios": [scenario.model_dump(mode="json") for scenario in self.scenarios],
        }
        (self.output_dir / "manifest.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
