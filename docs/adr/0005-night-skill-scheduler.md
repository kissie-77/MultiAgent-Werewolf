# ADR-0005: Night Skill Scheduler and Role Night Plans

## Status

Accepted (2026-05-20)

## Context

Night skills were collected in parallel via `get_night_actions` on all players, then wolf votes were resolved after `process_actions`. The Witch could not see `werewolf_target` when asked to save.

## Decision

1. Introduce `NightSkillScheduler` with ordered batches: pre-wolf → wolf votes → resolve target → witch + others.
2. Move LLM planning for Werewolf, Witch, Guard, Seer into `core/role_night_plans.py`.
3. Keep `Action` + `action_registry.py` for execution priority within a batch.

## Consequences

- Witch save prompt runs after `werewolf_target` is set.
- Extended wolf roles still use `get_night_actions` until migrated.
- Death abilities remain in `death_handler` with `DEATH_ABILITY_ROLE_NAMES`.
