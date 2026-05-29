---
name: strategy
description: "Skill for the Strategy area of MultiAgent-Werewolf. 33 symbols across 10 files."
---

# Strategy

33 symbols | 10 files | Cohesion: 91%

## When to Use

- Working with code in `src/`
- Understanding how get_registry, resolve_plan_text, test_resolve_plan_text_comes_from_prompt_manager work
- Modifying strategy-related functionality

## Key Files

| File                                               | Symbols                                                                                                                                                   |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/llm_werewolf/strategy/prompt_registry.py`     | variable_path, get_text, get_role_card, resolve, role_card_by_prompt_key (+6)                                                                             |
| `tests/strategy/test_vote_intention.py`            | test_tracker_record_speech_block, \_entry, test_compute_vote_swings_detects_changes, test_compute_vote_swings_none_to_target, test_format_intentions_line |
| `src/llm_werewolf/game_runtime/prompts/manager.py` | get_role_strategy_config, get_role_strategy_configs, build_prompt_key_strategy_prompt, resolve_plan_text                                                  |
| `src/llm_werewolf/strategy/vote_intention.py`      | compute_vote_swings, record_speech_block, export_records, save_jsonl                                                                                      |
| `src/llm_werewolf/strategy/role_prompts.py`        | \_hydrate_role_prompts_from_registry, get_all_plans, get_plan_by_name                                                                                     |
| `src/llm_werewolf/agent_team/agentscope_agent.py`  | \_get_role_config, role_name                                                                                                                              |
| `src/llm_werewolf/agent_team/factory.py`           | resolve_plan_text                                                                                                                                         |
| `tests/game_runtime/test_prompt_manager.py`        | test_resolve_plan_text_comes_from_prompt_manager                                                                                                          |
| `tests/strategy/test_game_prompts.py`              | test_plan_strategies                                                                                                                                      |
| `tests/strategy/test_role_prompts.py`              | test_game_prompts_and_plan_strategies_available                                                                                                           |

## Entry Points

Start here when exploring this area:

- **`get_registry`** (Function) — `src/llm_werewolf/strategy/prompt_registry.py:134`
- **`resolve_plan_text`** (Function) — `src/llm_werewolf/agent_team/factory.py:32`
- **`test_resolve_plan_text_comes_from_prompt_manager`** (Function) — `tests/game_runtime/test_prompt_manager.py:28`
- **`test_plan_strategies`** (Function) — `tests/strategy/test_game_prompts.py:17`
- **`test_game_prompts_and_plan_strategies_available`** (Function) — `tests/strategy/test_role_prompts.py:9`

## Key Symbols

| Symbol                                             | Type     | File                                               | Line |
| -------------------------------------------------- | -------- | -------------------------------------------------- | ---- |
| `get_registry`                                     | Function | `src/llm_werewolf/strategy/prompt_registry.py`     | 134  |
| `resolve_plan_text`                                | Function | `src/llm_werewolf/agent_team/factory.py`           | 32   |
| `test_resolve_plan_text_comes_from_prompt_manager` | Function | `tests/game_runtime/test_prompt_manager.py`        | 28   |
| `test_plan_strategies`                             | Function | `tests/strategy/test_game_prompts.py`              | 17   |
| `test_game_prompts_and_plan_strategies_available`  | Function | `tests/strategy/test_role_prompts.py`              | 9    |
| `compute_vote_swings`                              | Function | `src/llm_werewolf/strategy/vote_intention.py`      | 124  |
| `test_tracker_record_speech_block`                 | Function | `tests/strategy/test_vote_intention.py`            | 44   |
| `test_compute_vote_swings_detects_changes`         | Function | `tests/strategy/test_vote_intention.py`            | 20   |
| `test_compute_vote_swings_none_to_target`          | Function | `tests/strategy/test_vote_intention.py`            | 36   |
| `test_format_intentions_line`                      | Function | `tests/strategy/test_vote_intention.py`            | 69   |
| `role_name`                                        | Method   | `src/llm_werewolf/agent_team/agentscope_agent.py`  | 176  |
| `get_role_strategy_config`                         | Method   | `src/llm_werewolf/game_runtime/prompts/manager.py` | 60   |
| `get_role_strategy_configs`                        | Method   | `src/llm_werewolf/game_runtime/prompts/manager.py` | 73   |
| `build_prompt_key_strategy_prompt`                 | Method   | `src/llm_werewolf/game_runtime/prompts/manager.py` | 90   |
| `variable_path`                                    | Method   | `src/llm_werewolf/strategy/prompt_registry.py`     | 75   |
| `get_text`                                         | Method   | `src/llm_werewolf/strategy/prompt_registry.py`     | 79   |
| `get_role_card`                                    | Method   | `src/llm_werewolf/strategy/prompt_registry.py`     | 91   |
| `resolve`                                          | Method   | `src/llm_werewolf/strategy/prompt_registry.py`     | 108  |
| `role_card_by_prompt_key`                          | Method   | `src/llm_werewolf/strategy/prompt_registry.py`     | 112  |
| `agent_base_template`                              | Method   | `src/llm_werewolf/strategy/prompt_registry.py`     | 121  |

## Execution Flows

| Flow                                                  | Type            | Steps |
| ----------------------------------------------------- | --------------- | ----- |
| `Reset → _require_spec`                               | cross_community | 8     |
| `Configure_role → _require_spec`                      | cross_community | 7     |
| `Bind_role_prompt → _require_spec`                    | cross_community | 7     |
| `Bind_role_prompt → Get_registry`                     | cross_community | 7     |
| `Role_name → _require_spec`                           | intra_community | 6     |
| `Reset → Get_registry`                                | cross_community | 6     |
| `Configure_agents_for_players → Get_all_plans`        | cross_community | 5     |
| `Get_role_strategy_configs → _require_spec`           | intra_community | 5     |
| `Role_name → Get_registry`                            | intra_community | 4     |
| `_hydrate_role_prompts_from_registry → _require_spec` | intra_community | 4     |

## How to Explore

1. `gitnexus_context({name: "get_registry"})` — see callers and callees
2. `gitnexus_query({query: "strategy"})` — find related execution flows
3. Read key files listed above for implementation details
