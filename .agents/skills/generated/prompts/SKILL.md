---
name: prompts
description: "Skill for the Prompts area of MultiAgent-Werewolf. 41 symbols across 12 files."
---

# Prompts

41 symbols | 12 files | Cohesion: 82%

## When to Use

- Working with code in `src/`
- Understanding how get_identity_template, format_identity_prompt, get_definition_by_role_class work
- Modifying prompts-related functionality

## Key Files

| File                                                | Symbols                                                                                                                                                  |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/llm_werewolf/game_runtime/prompts/selector.py` | parse_yes_no, parse_target_selection, \_role_display_name, build_yes_no_prompt, ask_yes_no (+5)                                                          |
| `src/llm_werewolf/game_runtime/prompts/manager.py`  | build_system_prompt, build_identity_prompt, build_initial_chat_history, get_role_description, parse_bracket_number (+4)                                  |
| `tests/game_runtime/test_action_selector.py`        | test_parse_target_selection, test_parse_yes_no, test_ask_yes_no, test_build_target_selection_prompt, test_get_target_from_agent_uses_agent_response (+3) |
| `tests/game_runtime/test_prompt_manager_basic.py`   | test_system_and_identity_messages, test_parse_bracket_number, test_target_prompt_chinese_brackets                                                        |
| `src/llm_werewolf/game_runtime/prompts/identity.py` | get_identity_template, format_identity_prompt                                                                                                            |
| `src/llm_werewolf/game_runtime/roles/base.py`       | \_apply_catalog_description, get_action_prompt                                                                                                           |
| `src/llm_werewolf/game_runtime/prompts/actions.py`  | werewolf_coordination_note, werewolf_discussion                                                                                                          |
| `src/llm_werewolf/agent_team/mixin.py`              | bind_role                                                                                                                                                |
| `src/llm_werewolf/game_runtime/roles/catalog.py`    | get_definition_by_role_class                                                                                                                             |
| `src/llm_werewolf/agent_team/message_router.py`     | wolf_player_ids                                                                                                                                          |

## Entry Points

Start here when exploring this area:

- **`get_identity_template`** (Function) — `src/llm_werewolf/game_runtime/prompts/identity.py:106`
- **`format_identity_prompt`** (Function) — `src/llm_werewolf/game_runtime/prompts/identity.py:117`
- **`get_definition_by_role_class`** (Function) — `src/llm_werewolf/game_runtime/roles/catalog.py:190`
- **`test_system_and_identity_messages`** (Function) — `tests/game_runtime/test_prompt_manager_basic.py:6`
- **`test_parse_target_selection`** (Function) — `tests/game_runtime/test_action_selector.py:35`

## Key Symbols

| Symbol                                           | Type     | File                                                | Line |
| ------------------------------------------------ | -------- | --------------------------------------------------- | ---- |
| `get_identity_template`                          | Function | `src/llm_werewolf/game_runtime/prompts/identity.py` | 106  |
| `format_identity_prompt`                         | Function | `src/llm_werewolf/game_runtime/prompts/identity.py` | 117  |
| `get_definition_by_role_class`                   | Function | `src/llm_werewolf/game_runtime/roles/catalog.py`    | 190  |
| `test_system_and_identity_messages`              | Function | `tests/game_runtime/test_prompt_manager_basic.py`   | 6    |
| `test_parse_target_selection`                    | Function | `tests/game_runtime/test_action_selector.py`        | 35   |
| `test_parse_yes_no`                              | Function | `tests/game_runtime/test_action_selector.py`        | 43   |
| `test_parse_bracket_number`                      | Function | `tests/game_runtime/test_prompt_manager_basic.py`   | 32   |
| `participates_in_wolf_team`                      | Function | `src/llm_werewolf/game_runtime/roles/names.py`      | 61   |
| `test_ask_yes_no`                                | Function | `tests/game_runtime/test_action_selector.py`        | 102  |
| `test_build_target_selection_prompt`             | Function | `tests/game_runtime/test_action_selector.py`        | 20   |
| `test_target_prompt_chinese_brackets`            | Function | `tests/game_runtime/test_prompt_manager_basic.py`   | 20   |
| `test_get_target_from_agent_uses_agent_response` | Function | `tests/game_runtime/test_action_selector.py`        | 66   |
| `test_get_target_from_agent_random_fallback`     | Function | `tests/game_runtime/test_action_selector.py`        | 84   |
| `test_build_multi_target_prompt`                 | Function | `tests/game_runtime/test_action_selector.py`        | 49   |
| `test_parse_multi_target_selection`              | Function | `tests/game_runtime/test_action_selector.py`        | 59   |
| `bind_role`                                      | Method   | `src/llm_werewolf/agent_team/mixin.py`              | 15   |
| `build_system_prompt`                            | Method   | `src/llm_werewolf/game_runtime/prompts/manager.py`  | 46   |
| `build_identity_prompt`                          | Method   | `src/llm_werewolf/game_runtime/prompts/manager.py`  | 127  |
| `build_initial_chat_history`                     | Method   | `src/llm_werewolf/game_runtime/prompts/manager.py`  | 138  |
| `get_role_description`                           | Method   | `src/llm_werewolf/game_runtime/prompts/manager.py`  | 157  |

## Execution Flows

| Flow                  | Type            | Steps |
| --------------------- | --------------- | ----- |
| `Run → Get_camp`      | cross_community | 7     |
| `Run → Role_name_is`  | cross_community | 7     |
| `Main → Get_camp`     | cross_community | 6     |
| `Main → Role_name_is` | cross_community | 6     |
| `Main → Get_camp`     | cross_community | 6     |
| `Main → Role_name_is` | cross_community | 6     |
| `Step → Get_camp`     | cross_community | 6     |
| `Step → Role_name_is` | cross_community | 6     |
| `Run → Get_camp`      | cross_community | 6     |
| `Run → Role_name_is`  | cross_community | 6     |

## Connected Areas

| Area       | Connections |
| ---------- | ----------- |
| Agent_team | 2 calls     |
| Engine     | 2 calls     |
| Actions    | 1 calls     |
| Roles      | 1 calls     |

## How to Explore

1. `gitnexus_context({name: "get_identity_template"})` — see callers and callees
2. `gitnexus_query({query: "prompts"})` — find related execution flows
3. Read key files listed above for implementation details
