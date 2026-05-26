---
name: components
description: "Skill for the Components area of MultiAgent-Werewolf. 28 symbols across 3 files."
---

# Components

28 symbols | 3 files | Cohesion: 85%

## When to Use

- Working with code in `src/`
- Understanding how add_event, display_event, set_game_state work
- Modifying components-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/llm_werewolf/ui/components/chat_panel.py` | add_event, _is_night_action_event, _is_sheriff_event, _handle_special_events, _handle_game_lifecycle_events (+17) |
| `src/llm_werewolf/ui/components/game_panel.py` | set_game_state, refresh_display, on_mount |
| `src/llm_werewolf/ui/components/player_panel.py` | set_game_state, refresh_display, on_mount |

## Entry Points

Start here when exploring this area:

- **`add_event`** (Method) — `src/llm_werewolf/ui/components/chat_panel.py:27`
- **`display_event`** (Method) — `src/llm_werewolf/ui/components/chat_panel.py:155`
- **`set_game_state`** (Method) — `src/llm_werewolf/ui/components/game_panel.py:21`
- **`refresh_display`** (Method) — `src/llm_werewolf/ui/components/game_panel.py:30`
- **`on_mount`** (Method) — `src/llm_werewolf/ui/components/game_panel.py:109`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `add_event` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 27 |
| `display_event` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 155 |
| `set_game_state` | Method | `src/llm_werewolf/ui/components/game_panel.py` | 21 |
| `refresh_display` | Method | `src/llm_werewolf/ui/components/game_panel.py` | 30 |
| `on_mount` | Method | `src/llm_werewolf/ui/components/game_panel.py` | 109 |
| `set_game_state` | Method | `src/llm_werewolf/ui/components/player_panel.py` | 16 |
| `refresh_display` | Method | `src/llm_werewolf/ui/components/player_panel.py` | 25 |
| `on_mount` | Method | `src/llm_werewolf/ui/components/player_panel.py` | 87 |
| `_is_night_action_event` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 36 |
| `_is_sheriff_event` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 54 |
| `_handle_special_events` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 71 |
| `_handle_game_lifecycle_events` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 97 |
| `_buffer_night_action` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 249 |
| `_present_game_start` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 369 |
| `_present_game_end` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 380 |
| `_handle_voting_events` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 137 |
| `_handle_phase_change` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 190 |
| `_handle_narrator_message` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 218 |
| `_flush_night_actions` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 253 |
| `_flush_werewolf_discussion` | Method | `src/llm_werewolf/ui/components/chat_panel.py` | 302 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Add_event → _flush_discussion` | cross_community | 5 |
| `Add_event → _flush_night_actions` | cross_community | 4 |
| `Add_event → _present_game_start` | intra_community | 4 |
| `Add_event → _present_game_end` | intra_community | 4 |
| `Add_event → Is_visible_to` | cross_community | 3 |
| `Add_event → _is_night_action_event` | intra_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Ui | 1 calls |
| Game_runtime | 1 calls |

## How to Explore

1. `gitnexus_context({name: "add_event"})` — see callers and callees
2. `gitnexus_query({query: "components"})` — find related execution flows
3. Read key files listed above for implementation details
