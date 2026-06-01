import asyncio
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_werewolf.agent_team.agents.base import DemoAgent
from llm_werewolf.evaluation.core.checkers import (
    AsyncFlowChecker,
    DecisionConsistencyChecker,
    InformationIsolationChecker,
    PromptBadCaseChecker,
    RoleSkillChecker,
    VictoryCheckerEvaluator,
)
from llm_werewolf.evaluation.core.metrics import build_summary
from llm_werewolf.evaluation.core.models import CheckResult, GameRunResult
from llm_werewolf.evaluation.core.recorder import EvaluationRecorder
from llm_werewolf.evaluation.core.reporter import EvaluationReporter
from llm_werewolf.evaluation.core.scenarios import EvaluationScenario
from llm_werewolf.evaluation.leaderboard.entry_builder import build_entry, write_entry_bundle
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.config import GameConfig
from llm_werewolf.game_runtime.registries.role_registry import create_roles
from llm_werewolf.game_runtime.types import Event, EventType
from llm_werewolf.interface.bootstrap import create_information_hub


class EvaluationRunner:
    """离线评测运行器。"""

    def __init__(
        self,
        output_dir: str | Path,
        scenarios: list[EvaluationScenario],
        *,
        version_id: str | None = None,
        model: str = "unknown",
        prompt_version: str = "unknown",
        skill_version: str = "baseline",
        notes: list[str] | None = None,
        previous_run_dir: str | None = None,
        previous_skill_snapshot_path: str | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.scenarios = scenarios
        self.games_dir = self.output_dir / "games"
        self.version_id = version_id
        self.model = model
        self.prompt_version = prompt_version
        self.skill_version = skill_version
        self.notes = notes or []
        self.previous_run_dir = previous_run_dir
        self.previous_skill_snapshot_path = previous_skill_snapshot_path

    async def run(self) -> list[GameRunResult]:
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
        self._write_experiment_artifacts()
        return results

    async def run_scenario(
        self,
        scenario: EvaluationScenario,
        game_id: str,
        seed: int,
    ) -> GameRunResult:
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
        if engine.game_state and engine.game_state.vote_intention_tracker is not None:
            records = engine.game_state.vote_intention_tracker.export_records()
            recorder.record_vote_intentions(records)
            from llm_werewolf.evaluation.core.vote_swing_analysis import ensure_vote_intentions_jsonl

            events_for_intentions = [event.model_dump(mode="json") for event in events]
            ensure_vote_intentions_jsonl(game_dir, records=records, events=events_for_intentions)

        events_path = game_dir / "events.jsonl"
        if events_path.is_file() and events_path.stat().st_size > 0:
            try:
                from llm_werewolf.evaluation.post_game.pipeline import run_post_game_pipeline

                await run_post_game_pipeline(
                    game_dir,
                    engine=engine,
                    prompt_version=self.prompt_version,
                    skip_llm=True,
                )
            except Exception as exc:
                recorder.record_error(
                    exc,
                    phase=engine.game_state.phase.value if engine.game_state else None,
                    round_number=engine.game_state.round_number if engine.game_state else None,
                )

        checks = self._run_checkers(events, observations_by_player, engine)
        recorder.finalize_checks(checks)

        completed = (
            not crashed
            and not timed_out
            and engine.game_state is not None
            and bool(engine.game_state.winner)
        )
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
        config = GameConfig(num_players=scenario.num_players, role_names=scenario.role_names)
        agents = [
            DemoAgent(
                name=f"EvalPlayer{i}",
                model="demo",
                seed=scenario.seed,
                mode="deterministic",
            )
            for i in range(1, scenario.num_players + 1)
        ]
        roles = create_roles(config.role_names)
        engine = GameEngine(
            config,
            language=scenario.language,
            information_hub=create_information_hub(),
        )
        engine.setup_game(players=agents, roles=roles)
        return engine

    def _run_checkers(
        self,
        events: list[Event],
        observations_by_player: dict[str, str],
        engine: GameEngine,
    ) -> list[CheckResult]:
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
            (DecisionConsistencyChecker(), {"events": events}),
            (
                PromptBadCaseChecker(),
                {"events": events, "player_roles": player_roles, "player_camps": player_camps},
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
                        "phase": event.phase.value if hasattr(event.phase, "value") else str(event.phase),
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

    def _write_experiment_artifacts(self) -> None:
        scenario_name = self.scenarios[0].name if self.scenarios else "unknown"
        entry = build_entry(
            self.output_dir,
            version_id=self.version_id,
            model=self.model,
            prompt_version=self.prompt_version,
            skill_version=self.skill_version,
            scenario=scenario_name,
            notes=self.notes,
        )
        write_entry_bundle(
            self.output_dir,
            entry,
            previous_run_dir=self.previous_run_dir,
            previous_skill_snapshot_path=self.previous_skill_snapshot_path,
        )
