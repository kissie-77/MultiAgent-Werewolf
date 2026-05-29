---
name: game-runtime
description: "Skill for the Game_runtime area of MultiAgent-Werewolf. 166 symbols across 28 files."
---

# Game_runtime

166 symbols | 28 files | Cohesion: 80%

## When to Use

- Working with code in `src/`
- Understanding how test_graveyard_checked_persisted_on_execute, test_player_creation, test_player_death work
- Modifying game_runtime-related functionality

## Key Files

| File                                                | Symbols                                                                                                                                                                                                            |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `tests/game_runtime/test_victory.py`                | create_mock_player, test_villager_victory_all_werewolves_dead, test_villager_not_won_yet, test_white_lover_wolf_victory, test_check_victory_priority_lover_first (+19)                                             |
| `tests/game_runtime/test_events.py`                 | test_initialization, test_log_event, test_create_event, test_create_event_with_data, test_create_event_with_visibility (+11)                                                                                       |
| `src/llm_werewolf/game_runtime/role_night_plans.py` | \_resolve_night_planner, dispatch_night_plan, \_seat_label, plan_witch_actions, plan_guard_protect (+11)                                                                                                           |
| `src/llm_werewolf/game_runtime/player.py`           | is_alive, kill, revive, add_status, remove_status (+10)                                                                                                                                                            |
| `src/llm_werewolf/game_runtime/victory.py`          | check_victory, check_villager_victory, check_thief_victory, check_special_victory, get_winner (+7)                                                                                                                 |
| `src/llm_werewolf/game_runtime/night_scheduler.py`  | run_post_wolf_resolution, \_players_witch, \_players_post_witch_ordered, \_collect_for_players, \_plan_for_player (+5)                                                                                             |
| `src/llm_werewolf/game_runtime/serialization.py`    | \_extract_witch_data, \_extract_role_data, serialize_player, serialize_game_state, save_game_state (+5)                                                                                                            |
| `src/llm_werewolf/game_runtime/events.py`           | log_event, create_event, get_events_for_players, get_recent_events, get_events_by_type (+3)                                                                                                                        |
| `tests/game_runtime/test_game_state.py`             | \_players, test_next_phase_setup_to_night, test_next_phase_first_night_to_sheriff_election, test_next_phase_first_night_skips_sheriff_when_disabled, test_next_phase_voting_increments_round_and_clears_state (+3) |
| `tests/game_runtime/test_player.py`                 | test_player_creation, test_player_death, test_player_revive, test_player_status, test_player_voting_rights (+2)                                                                                                    |

## Entry Points

Start here when exploring this area:

- **`test_graveyard_checked_persisted_on_execute`** (Function) — `tests/game_runtime/test_graveyard_and_wolf_team.py:24`
- **`test_player_creation`** (Function) — `tests/game_runtime/test_player.py:4`
- **`test_player_death`** (Function) — `tests/game_runtime/test_player.py:14`
- **`test_player_revive`** (Function) — `tests/game_runtime/test_player.py:23`
- **`test_player_status`** (Function) — `tests/game_runtime/test_player.py:35`

## Key Symbols

| Symbol                                                     | Type     | File                                                 | Line |
| ---------------------------------------------------------- | -------- | ---------------------------------------------------- | ---- |
| `test_graveyard_checked_persisted_on_execute`              | Function | `tests/game_runtime/test_graveyard_and_wolf_team.py` | 24   |
| `test_player_creation`                                     | Function | `tests/game_runtime/test_player.py`                  | 4    |
| `test_player_death`                                        | Function | `tests/game_runtime/test_player.py`                  | 14   |
| `test_player_revive`                                       | Function | `tests/game_runtime/test_player.py`                  | 23   |
| `test_player_status`                                       | Function | `tests/game_runtime/test_player.py`                  | 35   |
| `test_player_voting_rights`                                | Function | `tests/game_runtime/test_player.py`                  | 46   |
| `test_player_lover_status`                                 | Function | `tests/game_runtime/test_player.py`                  | 57   |
| `test_next_phase_setup_to_night`                           | Function | `tests/game_runtime/test_game_state.py`              | 16   |
| `test_next_phase_first_night_to_sheriff_election`          | Function | `tests/game_runtime/test_game_state.py`              | 24   |
| `test_next_phase_first_night_skips_sheriff_when_disabled`  | Function | `tests/game_runtime/test_game_state.py`              | 33   |
| `test_next_phase_voting_increments_round_and_clears_state` | Function | `tests/game_runtime/test_game_state.py`              | 43   |
| `test_get_vote_counts_with_raven_mark`                     | Function | `tests/game_runtime/test_game_state.py`              | 60   |
| `test_reset_deaths`                                        | Function | `tests/game_runtime/test_game_state.py`              | 83   |
| `dispatch_night_plan`                                      | Function | `src/llm_werewolf/game_runtime/role_night_plans.py`  | 536  |
| `plan_witch_actions`                                       | Function | `src/llm_werewolf/game_runtime/role_night_plans.py`  | 277  |
| `plan_guard_protect`                                       | Function | `src/llm_werewolf/game_runtime/role_night_plans.py`  | 355  |
| `plan_seer_check`                                          | Function | `src/llm_werewolf/game_runtime/role_night_plans.py`  | 389  |
| `plan_graveyard_check`                                     | Function | `src/llm_werewolf/game_runtime/role_night_plans.py`  | 478  |
| `serialize_player`                                         | Function | `src/llm_werewolf/game_runtime/serialization.py`     | 113  |
| `serialize_game_state`                                     | Function | `src/llm_werewolf/game_runtime/serialization.py`     | 135  |

## Execution Flows

| Flow                            | Type            | Steps |
| ------------------------------- | --------------- | ----- |
| `Load_game → Import_role_class` | cross_community | 7     |
| `Load_game → Get_player`        | cross_community | 7     |
| `Main → Get_role_name`          | cross_community | 7     |
| `Main → Is_alive`               | cross_community | 7     |
| `Run → Get_camp`                | cross_community | 7     |
| `Run → _extract_witch_data`     | cross_community | 7     |
| `Get_winner → Get_camp`         | cross_community | 7     |
| `Get_winner → Role_name_is`     | cross_community | 7     |
| `Main → Get_camp`               | cross_community | 6     |
| `Main → Get_camp`               | cross_community | 6     |

## Connected Areas

| Area       | Connections |
| ---------- | ----------- |
| Engine     | 18 calls    |
| Roles      | 5 calls     |
| Agent_team | 2 calls     |
| Actions    | 2 calls     |
| Prompts    | 1 calls     |

## How to Explore

1. `gitnexus_context({name: "test_graveyard_checked_persisted_on_execute"})` — see callers and callees
2. `gitnexus_query({query: "game_runtime"})` — find related execution flows
3. Read key files listed above for implementation details
