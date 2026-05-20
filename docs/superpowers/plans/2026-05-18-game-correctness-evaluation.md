# Game Correctness Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first-pass offline evaluation system that detects game-system correctness issues in roles, information isolation, victory logic, and async flow.

**Architecture:** Add a focused `llm_werewolf.evaluation` package with stable data models, event/state recording, checkers, metrics, reporting, and an async runner. The CLI entry point runs deterministic demo scenarios without external API keys and writes replay-ready artifacts under `eval_runs/`.

**Tech Stack:** Python 3.10+, Pydantic v2, asyncio, JSONL/JSON/CSV/Markdown files, existing `GameEngine`, `EventLogger`, `serialize_game_state`, `DemoAgent`, and `fire`.

---

### Task 1: Evaluation Data Models

**Files:**
- Create: `src/llm_werewolf/evaluation/__init__.py`
- Create: `src/llm_werewolf/evaluation/models.py`
- Test: `tests/evaluation/test_models.py`

- [ ] **Step 1: Write the failing model tests**

Create `tests/evaluation/test_models.py` with tests for `CheckSeverity`, `CheckResult`, `GameRunResult`, and `EvaluationSummary`.

- [ ] **Step 2: Run model tests and verify they fail**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation/test_models.py -q`
Expected: FAIL because `llm_werewolf.evaluation` does not exist.

- [ ] **Step 3: Implement minimal Pydantic models**

Create `src/llm_werewolf/evaluation/models.py` with enums and models for check results, game run metadata, and aggregate summaries. Include counters for completed/crashed/timeout games and violation counts.

- [ ] **Step 4: Re-run model tests**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation/test_models.py -q`
Expected: PASS.

### Task 2: Recorder

**Files:**
- Create: `src/llm_werewolf/evaluation/recorder.py`
- Test: `tests/evaluation/test_recorder.py`

- [ ] **Step 1: Write recorder tests**

Create tests that instantiate a recorder in a temp game directory, record an event, snapshot a simple game state, record an exception, and assert `events.jsonl`, `snapshots.jsonl`, and `errors.jsonl` are written as JSON lines.

- [ ] **Step 2: Run recorder tests and verify they fail**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation/test_recorder.py -q`
Expected: FAIL because `EvaluationRecorder` does not exist.

- [ ] **Step 3: Implement recorder**

Create `EvaluationRecorder` with `record_event(event)`, `record_snapshot(game_state, label)`, `record_error(exc, phase, round_number, role_name)`, and `finalize_checks(results)` methods. Use `Event.model_dump(mode="json")` and `serialize_game_state(game_state).model_dump(mode="json")`.

- [ ] **Step 4: Re-run recorder tests**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation/test_recorder.py -q`
Expected: PASS.

### Task 3: Correctness Checkers

**Files:**
- Create: `src/llm_werewolf/evaluation/checkers.py`
- Test: `tests/evaluation/test_checkers.py`

- [ ] **Step 1: Write checker tests**

Create tests for:
- private event leakage detection when an observation text contains a private message for another player
- phase order violation detection for illegal phase jumps
- victory mismatch detection when final winner differs from `GAME_ENDED` event data
- role-skill checker detecting missing structured fields on role action events

- [ ] **Step 2: Run checker tests and verify they fail**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation/test_checkers.py -q`
Expected: FAIL because checker classes do not exist.

- [ ] **Step 3: Implement checkers**

Create `InformationIsolationChecker`, `AsyncFlowChecker`, `VictoryCheckerEvaluator`, and `RoleSkillChecker`. Each checker returns `list[CheckResult]` and never raises for malformed input. Use the existing `EventType` and `GamePhase` enums where possible.

- [ ] **Step 4: Re-run checker tests**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation/test_checkers.py -q`
Expected: PASS.

### Task 4: Scenarios and Runner

**Files:**
- Create: `src/llm_werewolf/evaluation/scenarios.py`
- Create: `src/llm_werewolf/evaluation/runner.py`
- Test: `tests/evaluation/test_runner.py`

- [ ] **Step 1: Write runner tests**

Create tests that run one 6-player smoke scenario with demo agents into a temp output directory, assert the run completes or records a controlled failure, and assert manifest, per-game artifacts, summary, metrics, and report are present.

- [ ] **Step 2: Run runner tests and verify they fail**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation/test_runner.py -q`
Expected: FAIL because runner and scenario modules do not exist.

- [ ] **Step 3: Implement scenarios**

Create `EvaluationScenario` with fields `name`, `num_players`, `role_names`, `language`, `seed`, `timeout_seconds`, and `repetitions`. Provide `smoke_6p_basic()` and `regression_default_demo()` constructors.

- [ ] **Step 4: Implement runner**

Create `EvaluationRunner.run()` and `run_scenario()`. Build demo agents, create roles, seed `random`, configure `GameEngine`, attach the recorder to `engine.on_event`, run `engine.play_game()` with `asyncio.wait_for`, record snapshots before and after the run, then run all checkers.

- [ ] **Step 5: Re-run runner tests**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation/test_runner.py -q`
Expected: PASS.

### Task 5: Metrics and Reports

**Files:**
- Create: `src/llm_werewolf/evaluation/metrics.py`
- Create: `src/llm_werewolf/evaluation/reporter.py`
- Test: `tests/evaluation/test_reporter.py`

- [ ] **Step 1: Write metrics/reporter tests**

Create tests that pass two `GameRunResult` objects into the metrics layer and assert `completion_rate`, `crash_rate`, `timeout_rate`, and violation counters are correct. Assert reporter writes `summary.json`, `metrics.csv`, and `report.md`.

- [ ] **Step 2: Run reporter tests and verify they fail**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation/test_reporter.py -q`
Expected: FAIL because metrics/reporter modules do not exist.

- [ ] **Step 3: Implement metrics and reporter**

Implement `build_summary(results)` and `EvaluationReporter.write(summary, results)`. Markdown report must include total games, completion/crash/timeout rates, violation counts, and top errors.

- [ ] **Step 4: Re-run reporter tests**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation/test_reporter.py -q`
Expected: PASS.

### Task 6: CLI Entry Point

**Files:**
- Create: `src/llm_werewolf/eval_cli.py`
- Modify: `pyproject.toml`
- Test: `tests/evaluation/test_eval_cli.py`

- [ ] **Step 1: Write CLI tests**

Create tests that call the CLI `main` function with `output_dir`, `scenario="smoke_6p_basic"`, and `games=1`, then assert output files are created.

- [ ] **Step 2: Run CLI tests and verify they fail**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation/test_eval_cli.py -q`
Expected: FAIL because `llm_werewolf.eval_cli` and `werewolf-eval` do not exist.

- [ ] **Step 3: Implement CLI**

Create `eval_cli.py` with `main(output_dir="eval_runs", scenario="smoke_6p_basic", games=10, timeout_seconds=30)` and `entry()` using `fire.Fire(main)`. Add `werewolf-eval = "llm_werewolf.eval_cli:entry"` to `[project.scripts]`.

- [ ] **Step 4: Re-run CLI tests**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation/test_eval_cli.py -q`
Expected: PASS.

### Task 7: Integration Verification

**Files:**
- Modify only if a test exposes a real integration defect in files touched above.

- [ ] **Step 1: Run focused evaluation test suite**

Run: `uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation -q`
Expected: PASS.

- [ ] **Step 2: Run one real CLI evaluation**

Run: `uv run werewolf-eval --scenario smoke_6p_basic --games 1 --timeout_seconds 20 --output_dir eval_runs/dev-smoke`
Expected: command exits successfully and writes `eval_runs/dev-smoke/report.md`.

- [ ] **Step 3: Run default demo regression capture**

Run: `uv run werewolf-eval --scenario regression_default_demo --games 1 --timeout_seconds 20 --output_dir eval_runs/dev-regression`
Expected: command exits successfully even if the game records a role/runtime error; report includes crash/error counters instead of aborting the batch.

- [ ] **Step 4: Run status check**

Run: `git status --short`
Expected: only intended evaluation files and generated ignored artifacts, if any, appear.

### Task 8: Commit

**Files:**
- All evaluation implementation and tests from Tasks 1-7.

- [ ] **Step 1: Review diff**

Run: `git diff -- src/llm_werewolf/evaluation src/llm_werewolf/eval_cli.py tests/evaluation pyproject.toml docs/superpowers/plans/2026-05-18-game-correctness-evaluation.md`
Expected: diff contains only the planned evaluation system.

- [ ] **Step 2: Commit implementation**

Run:

```bash
git add src/llm_werewolf/evaluation src/llm_werewolf/eval_cli.py tests/evaluation pyproject.toml docs/superpowers/plans/2026-05-18-game-correctness-evaluation.md
git commit -m "feat: add game correctness evaluation"
```

Expected: commit succeeds.
