---
name: ui
description: "Skill for the Ui area of MultiAgent-Werewolf. 31 symbols across 3 files."
---

# Ui

31 symbols | 3 files | Cohesion: 85%

## When to Use

- Working with code in `src/`
- Understanding how is_visible_to, present_event, on_mount work
- Modifying ui-related functionality

## Key Files

| File                                            | Symbols                                                                                                                   |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `src/llm_werewolf/ui/console_presenter.py`      | \_is_night_action_event, \_handle_game_lifecycle_events, present_event, \_buffer_night_action, \_present_game_start (+20) |
| `src/llm_werewolf/ui/tui_app.py`                | on_mount, update_game_state, on_game_event, add_system_message, add_error                                                 |
| `src/llm_werewolf/game_runtime/types/models.py` | is_visible_to                                                                                                             |

## Entry Points

Start here when exploring this area:

- **`is_visible_to`** (Method) — `src/llm_werewolf/game_runtime/types/models.py:57`
- **`present_event`** (Method) — `src/llm_werewolf/ui/console_presenter.py:152`
- **`on_mount`** (Method) — `src/llm_werewolf/ui/tui_app.py:106`
- **`update_game_state`** (Method) — `src/llm_werewolf/ui/tui_app.py:135`
- **`on_game_event`** (Method) — `src/llm_werewolf/ui/tui_app.py:146`

## Key Symbols

| Symbol                          | Type   | File                                            | Line |
| ------------------------------- | ------ | ----------------------------------------------- | ---- |
| `is_visible_to`                 | Method | `src/llm_werewolf/game_runtime/types/models.py` | 57   |
| `present_event`                 | Method | `src/llm_werewolf/ui/console_presenter.py`      | 152  |
| `on_mount`                      | Method | `src/llm_werewolf/ui/tui_app.py`                | 106  |
| `update_game_state`             | Method | `src/llm_werewolf/ui/tui_app.py`                | 135  |
| `on_game_event`                 | Method | `src/llm_werewolf/ui/tui_app.py`                | 146  |
| `add_system_message`            | Method | `src/llm_werewolf/ui/tui_app.py`                | 157  |
| `add_error`                     | Method | `src/llm_werewolf/ui/tui_app.py`                | 166  |
| `_is_night_action_event`        | Method | `src/llm_werewolf/ui/console_presenter.py`      | 36   |
| `_handle_game_lifecycle_events` | Method | `src/llm_werewolf/ui/console_presenter.py`      | 94   |
| `_buffer_night_action`          | Method | `src/llm_werewolf/ui/console_presenter.py`      | 242  |
| `_present_game_start`           | Method | `src/llm_werewolf/ui/console_presenter.py`      | 363  |
| `_present_game_end`             | Method | `src/llm_werewolf/ui/console_presenter.py`      | 373  |
| `_get_event_style`              | Method | `src/llm_werewolf/ui/console_presenter.py`      | 405  |
| `_handle_voting_events`         | Method | `src/llm_werewolf/ui/console_presenter.py`      | 134  |
| `_handle_phase_change`          | Method | `src/llm_werewolf/ui/console_presenter.py`      | 187  |
| `_handle_narrator_message`      | Method | `src/llm_werewolf/ui/console_presenter.py`      | 213  |
| `_flush_night_actions`          | Method | `src/llm_werewolf/ui/console_presenter.py`      | 267  |
| `_flush_werewolf_discussion`    | Method | `src/llm_werewolf/ui/console_presenter.py`      | 294  |
| `_flush_discussion`             | Method | `src/llm_werewolf/ui/console_presenter.py`      | 307  |
| `_buffer_vote`                  | Method | `src/llm_werewolf/ui/console_presenter.py`      | 318  |

## Execution Flows

| Flow                                   | Type            | Steps |
| -------------------------------------- | --------------- | ----- |
| `Present_event → _flush_discussion`    | cross_community | 4     |
| `Present_event → _flush_night_actions` | cross_community | 3     |
| `Present_event → _present_game_start`  | intra_community | 3     |
| `Present_event → _present_game_end`    | intra_community | 3     |
| `Add_event → Is_visible_to`            | cross_community | 3     |

## How to Explore

1. `gitnexus_context({name: "is_visible_to"})` — see callers and callees
2. `gitnexus_query({query: "ui"})` — find related execution flows
3. Read key files listed above for implementation details
