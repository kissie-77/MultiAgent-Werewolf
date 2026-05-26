---
name: config
description: "Skill for the Config area of MultiAgent-Werewolf. 12 symbols across 2 files."
---

# Config

12 symbols | 2 files | Cohesion: 100%

## When to Use

- Working with code in `tests/`
- Understanding how test_use_agentscope_backend_default, test_rejects_removed_single_call_llm_backends, test_accepts_agentscope_backend_value work
- Modifying config-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/config/test_agent_backend.py` | _six_demo_players, test_use_agentscope_backend_default, test_rejects_removed_single_call_llm_backends, test_accepts_agentscope_backend_value, test_prompt_version_defaults_to_v2 (+2) |
| `src/llm_werewolf/game_runtime/config/presets.py` | _validate_player_count, _allocate_werewolf_roles, _allocate_villager_roles, _get_timeouts, create_game_config_from_player_count |

## Entry Points

Start here when exploring this area:

- **`test_use_agentscope_backend_default`** (Function) — `tests/config/test_agent_backend.py:11`
- **`test_rejects_removed_single_call_llm_backends`** (Function) — `tests/config/test_agent_backend.py:16`
- **`test_accepts_agentscope_backend_value`** (Function) — `tests/config/test_agent_backend.py:26`
- **`test_prompt_version_defaults_to_v2`** (Function) — `tests/config/test_agent_backend.py:35`
- **`test_prompt_version_normalizes_case`** (Function) — `tests/config/test_agent_backend.py:40`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_use_agentscope_backend_default` | Function | `tests/config/test_agent_backend.py` | 11 |
| `test_rejects_removed_single_call_llm_backends` | Function | `tests/config/test_agent_backend.py` | 16 |
| `test_accepts_agentscope_backend_value` | Function | `tests/config/test_agent_backend.py` | 26 |
| `test_prompt_version_defaults_to_v2` | Function | `tests/config/test_agent_backend.py` | 35 |
| `test_prompt_version_normalizes_case` | Function | `tests/config/test_agent_backend.py` | 40 |
| `test_rejects_invalid_prompt_version` | Function | `tests/config/test_agent_backend.py` | 49 |
| `create_game_config_from_player_count` | Function | `src/llm_werewolf/game_runtime/config/presets.py` | 85 |
| `_six_demo_players` | Function | `tests/config/test_agent_backend.py` | 7 |
| `_validate_player_count` | Function | `src/llm_werewolf/game_runtime/config/presets.py` | 3 |
| `_allocate_werewolf_roles` | Function | `src/llm_werewolf/game_runtime/config/presets.py` | 20 |
| `_allocate_villager_roles` | Function | `src/llm_werewolf/game_runtime/config/presets.py` | 38 |
| `_get_timeouts` | Function | `src/llm_werewolf/game_runtime/config/presets.py` | 69 |

## How to Explore

1. `gitnexus_context({name: "test_use_agentscope_backend_default"})` — see callers and callees
2. `gitnexus_query({query: "config"})` — find related execution flows
3. Read key files listed above for implementation details
