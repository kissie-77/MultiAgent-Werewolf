---
name: interface
description: "Skill for the Interface area of MultiAgent-Werewolf. 20 symbols across 11 files."
---

# Interface

20 symbols | 11 files | Cohesion: 89%

## When to Use

- Working with code in `src/`
- Understanding how create_agent, load_config, create_players_from_config work
- Modifying interface-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/interface/test_bootstrap.py` | _six_demo_players, test_create_players_demo_never_agentscope_class, test_wire_agentscope_calls_bind_after_setup, test_wire_agentscope_backend_is_the_only_llm_backend |
| `src/llm_werewolf/interface/bootstrap.py` | create_players_from_config, wire_agentscope_after_setup, prepare_game_roster |
| `src/llm_werewolf/interface/finalize_run.py` | _event_to_dict, persist_run_artifacts, finalize_run |
| `src/llm_werewolf/interface/cli.py` | main, _run_main |
| `src/llm_werewolf/interface/cli_overrides.py` | parse_seat_list, apply_human_seats |
| `src/llm_werewolf/agent_team/base.py` | create_agent |
| `src/llm_werewolf/game_runtime/game_state.py` | get_dead_players |
| `src/llm_werewolf/game_runtime/utils.py` | load_config |
| `src/llm_werewolf/interface/modes.py` | resolve_config_path |
| `src/llm_werewolf/interface/player_count.py` | resize_players_config |

## Entry Points

Start here when exploring this area:

- **`create_agent`** (Function) — `src/llm_werewolf/agent_team/base.py:93`
- **`load_config`** (Function) — `src/llm_werewolf/game_runtime/utils.py:7`
- **`create_players_from_config`** (Function) — `src/llm_werewolf/interface/bootstrap.py:42`
- **`wire_agentscope_after_setup`** (Function) — `src/llm_werewolf/interface/bootstrap.py:59`
- **`prepare_game_roster`** (Function) — `src/llm_werewolf/interface/bootstrap.py:73`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `create_agent` | Function | `src/llm_werewolf/agent_team/base.py` | 93 |
| `load_config` | Function | `src/llm_werewolf/game_runtime/utils.py` | 7 |
| `create_players_from_config` | Function | `src/llm_werewolf/interface/bootstrap.py` | 42 |
| `wire_agentscope_after_setup` | Function | `src/llm_werewolf/interface/bootstrap.py` | 59 |
| `prepare_game_roster` | Function | `src/llm_werewolf/interface/bootstrap.py` | 73 |
| `main` | Function | `src/llm_werewolf/interface/cli.py` | 24 |
| `parse_seat_list` | Function | `src/llm_werewolf/interface/cli_overrides.py` | 12 |
| `apply_human_seats` | Function | `src/llm_werewolf/interface/cli_overrides.py` | 28 |
| `persist_run_artifacts` | Function | `src/llm_werewolf/interface/finalize_run.py` | 23 |
| `finalize_run` | Function | `src/llm_werewolf/interface/finalize_run.py` | 40 |
| `resolve_config_path` | Function | `src/llm_werewolf/interface/modes.py` | 49 |
| `resize_players_config` | Function | `src/llm_werewolf/interface/player_count.py` | 16 |
| `main` | Function | `src/llm_werewolf/interface/tui.py` | 17 |
| `test_create_players_demo_never_agentscope_class` | Function | `tests/interface/test_bootstrap.py` | 16 |
| `test_wire_agentscope_calls_bind_after_setup` | Function | `tests/interface/test_bootstrap.py` | 23 |
| `test_wire_agentscope_backend_is_the_only_llm_backend` | Function | `tests/interface/test_bootstrap.py` | 37 |
| `get_dead_players` | Method | `src/llm_werewolf/game_runtime/game_state.py` | 157 |
| `_run_main` | Function | `src/llm_werewolf/interface/cli.py` | 146 |
| `_event_to_dict` | Function | `src/llm_werewolf/interface/finalize_run.py` | 11 |
| `_six_demo_players` | Function | `tests/interface/test_bootstrap.py` | 12 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → Get_camp` | cross_community | 6 |
| `Main → Role_name_is` | cross_community | 6 |
| `Main → Get_camp` | cross_community | 6 |
| `Main → Role_name_is` | cross_community | 6 |
| `Main → Get_private_notes` | cross_community | 5 |
| `Main → Get_private_notes` | cross_community | 5 |
| `Main → Resolve_visible_to` | cross_community | 4 |
| `Main → Resolve_visible_to` | cross_community | 4 |
| `Run_llm_replay → Load_config` | cross_community | 4 |
| `Main → _attach_agent_to_player` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Engine | 8 calls |
| Integration | 2 calls |
| Scripts | 1 calls |
| Agent_team | 1 calls |

## How to Explore

1. `gitnexus_context({name: "create_agent"})` — see callers and callees
2. `gitnexus_query({query: "interface"})` — find related execution flows
3. Read key files listed above for implementation details
