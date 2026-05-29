---
name: engine
description: "Skill for the Engine area of MultiAgent-Werewolf. 128 symbols across 25 files."
---

# Engine

128 symbols | 25 files | Cohesion: 71%

## When to Use

- Working with code in `src/`
- Understanding how on_speech, on_speech, context_builder work
- Modifying engine-related functionality

## Key Files

| File                                                       | Symbols                                                                                                                                                                         |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/llm_werewolf/game_runtime/engine/action_processor.py` | \_decision_data, \_is_actor_blocked, \_log_guard_action, \_log_witch_save_action, \_log_witch_poison_action (+11)                                                               |
| `src/llm_werewolf/game_runtime/engine/sheriff_election.py` | on_speech, execute_sheriff_election, \_collect_sheriff_candidates, \_build_campaign_context, \_conduct_campaign_speeches (+10)                                                  |
| `src/llm_werewolf/game_runtime/engine/voting_phase.py`     | \_build_exile_pk_speech_context, context_builder, on_speech, \_get_vote, \_conduct_voting_pk_speeches (+8)                                                                      |
| `src/llm_werewolf/game_runtime/engine/death_handler.py`    | \_handle_elder_penalty, \_handle_sheriff_badge_transfer, \_process_hunter_or_alpha_death, \_handle_lover_death, \_handle_wolf_beauty_charm_death (+7)                           |
| `tests/game_runtime/test_locale.py`                        | test_unsupported_language_fallback, test_get_message_without_formatting, test_get_message_with_formatting, test_get_message_with_multiple_params, test_get_nonexistent_key (+6) |
| `src/llm_werewolf/game_runtime/game_state.py`              | get_alive_witch_player_ids, require_phase_interaction, set_phase, get_alive_players, get_players_with_night_actions (+5)                                                        |
| `src/llm_werewolf/game_runtime/engine/base.py`             | GameEngineBase, check_victory, \_log_vote_intention_record, \_log_event, step (+4)                                                                                              |
| `src/llm_werewolf/game_runtime/engine/night_phase.py`      | \_log_role_acting, \_resolve_blood_moon_transforms, \_run_werewolf_discussion, run_night_phase, \_resolve_werewolf_votes (+1)                                                   |
| `src/llm_werewolf/game_runtime/types/protocols.py`         | get_role_name, is_alive, kill, is_lover, can_vote (+1)                                                                                                                          |
| `src/llm_werewolf/game_runtime/prompts/actions.py`         | exile_pk_speech, sheriff_run, sheriff_vote_intro, sheriff_died, sheriff_speech                                                                                                  |

## Entry Points

Start here when exploring this area:

- **`on_speech`** (Function) — `src/llm_werewolf/game_runtime/engine/day_phase.py:101`
- **`on_speech`** (Function) — `src/llm_werewolf/game_runtime/engine/sheriff_election.py:116`
- **`context_builder`** (Function) — `src/llm_werewolf/game_runtime/engine/voting_phase.py:339`
- **`on_speech`** (Function) — `src/llm_werewolf/game_runtime/engine/voting_phase.py:342`
- **`test_is_actor_blocked_excludes_nightmare_block_action`** (Function) — `tests/game_runtime/test_action_processor.py:45`

## Key Symbols

| Symbol                                                  | Type     | File                                                       | Line |
| ------------------------------------------------------- | -------- | ---------------------------------------------------------- | ---- |
| `ActionProcessorMixin`                                  | Class    | `src/llm_werewolf/game_runtime/engine/action_processor.py` | 25   |
| `GameEngineBase`                                        | Class    | `src/llm_werewolf/game_runtime/engine/base.py`             | 28   |
| `DayPhaseMixin`                                         | Class    | `src/llm_werewolf/game_runtime/engine/day_phase.py`        | 12   |
| `DeathHandlerMixin`                                     | Class    | `src/llm_werewolf/game_runtime/engine/death_handler.py`    | 12   |
| `GameEngine`                                            | Class    | `src/llm_werewolf/game_runtime/engine/game_engine.py`      | 11   |
| `NightPhaseMixin`                                       | Class    | `src/llm_werewolf/game_runtime/engine/night_phase.py`      | 22   |
| `SheriffElectionMixin`                                  | Class    | `src/llm_werewolf/game_runtime/engine/sheriff_election.py` | 11   |
| `VotingPhaseMixin`                                      | Class    | `src/llm_werewolf/game_runtime/engine/voting_phase.py`     | 19   |
| `on_speech`                                             | Function | `src/llm_werewolf/game_runtime/engine/day_phase.py`        | 101  |
| `on_speech`                                             | Function | `src/llm_werewolf/game_runtime/engine/sheriff_election.py` | 116  |
| `context_builder`                                       | Function | `src/llm_werewolf/game_runtime/engine/voting_phase.py`     | 339  |
| `on_speech`                                             | Function | `src/llm_werewolf/game_runtime/engine/voting_phase.py`     | 342  |
| `test_is_actor_blocked_excludes_nightmare_block_action` | Function | `tests/game_runtime/test_action_processor.py`              | 45   |
| `test_log_witch_save_action`                            | Function | `tests/game_runtime/test_action_processor.py`              | 60   |
| `offer_blood_moon_transform`                            | Function | `src/llm_werewolf/game_runtime/role_night_plans.py`        | 252  |
| `resolve_visible_to`                                    | Function | `src/llm_werewolf/game_runtime/event_visibility.py`        | 52   |
| `format_intentions_line`                                | Function | `src/llm_werewolf/strategy/vote_intention.py`              | 151  |
| `test_victory_checker`                                  | Function | `tests/integration/test_game_flow.py`                      | 62   |
| `test_player_private_notes`                             | Function | `tests/game_runtime/test_player.py`                        | 68   |
| `load_game_state_snapshot`                              | Function | `src/llm_werewolf/game_runtime/serialization.py`           | 191  |

## Execution Flows

| Flow                            | Type            | Steps |
| ------------------------------- | --------------- | ----- |
| `Load_game → Import_role_class` | cross_community | 7     |
| `Load_game → Get_player`        | cross_community | 7     |
| `Main → Resolve_visible_to`     | cross_community | 7     |
| `Main → Get_role_name`          | cross_community | 7     |
| `Main → Is_alive`               | cross_community | 7     |
| `Run → Get_camp`                | cross_community | 7     |
| `Run → Role_name_is`            | cross_community | 7     |
| `Run → Get_private_notes`       | cross_community | 7     |
| `Main → Get_camp`               | cross_community | 6     |
| `Main → Role_name_is`           | cross_community | 6     |

## Connected Areas

| Area         | Connections |
| ------------ | ----------- |
| Game_runtime | 8 calls     |
| Agent_team   | 3 calls     |
| Roles        | 2 calls     |
| Prompts      | 2 calls     |
| Integration  | 1 calls     |
| Actions      | 1 calls     |

## How to Explore

1. `gitnexus_context({name: "on_speech"})` — see callers and callees
2. `gitnexus_query({query: "engine"})` — find related execution flows
3. Read key files listed above for implementation details
