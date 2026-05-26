---
name: integration
description: "Skill for the Integration area of MultiAgent-Werewolf. 7 symbols across 4 files."
---

# Integration

7 symbols | 4 files | Cohesion: 52%

## When to Use

- Working with code in `tests/`
- Understanding how engine_with_speech_event, test_game_initialization, test_game_state_initialization work
- Modifying integration-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/integration/test_game_flow.py` | test_game_initialization, test_game_state_initialization, test_role_assignment |
| `src/llm_werewolf/game_runtime/engine/base.py` | setup_game, assign_roles |
| `tests/evaluation/test_recorder.py` | _build_engine |
| `tests/game_runtime/test_hub_decision_context.py` | engine_with_speech_event |

## Entry Points

Start here when exploring this area:

- **`engine_with_speech_event`** (Function) — `tests/game_runtime/test_hub_decision_context.py:20`
- **`test_game_initialization`** (Function) — `tests/integration/test_game_flow.py:7`
- **`test_game_state_initialization`** (Function) — `tests/integration/test_game_flow.py:27`
- **`test_role_assignment`** (Function) — `tests/integration/test_game_flow.py:42`
- **`setup_game`** (Method) — `src/llm_werewolf/game_runtime/engine/base.py:121`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `engine_with_speech_event` | Function | `tests/game_runtime/test_hub_decision_context.py` | 20 |
| `test_game_initialization` | Function | `tests/integration/test_game_flow.py` | 7 |
| `test_game_state_initialization` | Function | `tests/integration/test_game_flow.py` | 27 |
| `test_role_assignment` | Function | `tests/integration/test_game_flow.py` | 42 |
| `setup_game` | Method | `src/llm_werewolf/game_runtime/engine/base.py` | 121 |
| `assign_roles` | Method | `src/llm_werewolf/game_runtime/engine/base.py` | 161 |
| `_build_engine` | Function | `tests/evaluation/test_recorder.py` | 16 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → Resolve_visible_to` | cross_community | 7 |
| `Run → Get_private_notes` | cross_community | 7 |
| `Main → Get_camp` | cross_community | 6 |
| `Main → Role_name_is` | cross_community | 6 |
| `Main → Get_camp` | cross_community | 6 |
| `Main → Role_name_is` | cross_community | 6 |
| `Main → _attach_agent_to_player` | cross_community | 6 |
| `Main → Get_private_notes` | cross_community | 6 |
| `Main → Get_private_notes` | cross_community | 5 |
| `Main → Get_private_notes` | cross_community | 5 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Engine | 5 calls |

## How to Explore

1. `gitnexus_context({name: "engine_with_speech_event"})` — see callers and callees
2. `gitnexus_query({query: "integration"})` — find related execution flows
3. Read key files listed above for implementation details
