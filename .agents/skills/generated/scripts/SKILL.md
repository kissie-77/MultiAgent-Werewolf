---
name: scripts
description: "Skill for the Scripts area of MultiAgent-Werewolf. 4 symbols across 2 files."
---

# Scripts

4 symbols | 2 files | Cohesion: 60%

## When to Use

- Working with code in `scripts/`
- Understanding how run, main, play_game work
- Modifying scripts-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `scripts/run_game_with_replay.py` | _event_to_dict, run, main |
| `src/llm_werewolf/game_runtime/engine/base.py` | play_game |

## Entry Points

Start here when exploring this area:

- **`run`** (Function) — `scripts/run_game_with_replay.py:45`
- **`main`** (Function) — `scripts/run_game_with_replay.py:117`
- **`play_game`** (Method) — `src/llm_werewolf/game_runtime/engine/base.py:368`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `run` | Function | `scripts/run_game_with_replay.py` | 45 |
| `main` | Function | `scripts/run_game_with_replay.py` | 117 |
| `play_game` | Method | `src/llm_werewolf/game_runtime/engine/base.py` | 368 |
| `_event_to_dict` | Function | `scripts/run_game_with_replay.py` | 33 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Run → Get_camp` | cross_community | 7 |
| `Run → Role_name_is` | cross_community | 7 |
| `Main → Get_private_notes` | cross_community | 6 |
| `Main → Resolve_visible_to` | cross_community | 6 |
| `Main → _attach_agent_to_player` | cross_community | 4 |
| `Main → _event_to_dict` | intra_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Engine | 4 calls |
| Integration | 1 calls |

## How to Explore

1. `gitnexus_context({name: "run"})` — see callers and callees
2. `gitnexus_query({query: "scripts"})` — find related execution flows
3. Read key files listed above for implementation details
