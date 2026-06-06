# Contributing

This project is organized around six backend-facing areas plus UI:

- `agent_team`: Agent construction, memory, communication, and skill runtime support.
- `game_runtime`: Werewolf rules, phases, roles, actions, observations, and prompts used during play.
- `strategy`: prompt versions, decision schemas, belief state, and strategy utilities.
- `evaluation`: post-game review, scoring, leaderboard, A/B comparison, evolution, and evidence reports.
- `interface`: CLI/API/TUI entrypoints and runtime bootstrapping.
- `ui`: frontend and presentation layer.

## Development Rules

- Keep changes inside the owning area whenever possible.
- Do not bypass information isolation. Private night events must not appear in unauthorized player observations.
- Add tests for new evaluation artifacts, prompt-version behavior, and game-rule changes.
- Prefer deterministic rule-based checks for grading evidence; use LLM analysis as an optional enrichment layer.
- Do not commit generated caches such as `__pycache__`, `.pytest_cache`, or temporary run artifacts.

## Useful Commands

```powershell
uv run pytest tests/evaluation --no-cov
uv run python -m llm_werewolf.interface.cli.evidence --eval_root artifacts/eval_runs
uv run python -m llm_werewolf.interface.cli.evolution cycle --rounds 2 --games_per_round 3
```

## Review Checklist

- The game can still complete a smoke evaluation.
- `InformationIsolationChecker` has no critical leaks.
- Post-game artifacts are written without blocking the whole pipeline when one optional step fails.
- Prompt or skill changes are versioned and traceable.
- If an evolution claim is made, include A/B evidence and the exact run directories.
