---
name: log-views
description: "Skill for the Log_views area of MultiAgent-Werewolf. 16 symbols across 2 files."
---

# Log_views

16 symbols | 2 files | Cohesion: 98%

## When to Use

- Working with code in `src/`
- Understanding how build_god_timeline, build_player_timeline, build_public_digest work
- Modifying log_views-related functionality

## Key Files

| File                                               | Symbols                                                                                                   |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `src/llm_werewolf/evaluation/log_views/builder.py` | to_dict, \_write_text, \_write_json, build_god_timeline, build_player_timeline (+4)                       |
| `src/llm_werewolf/evaluation/log_views/filters.py` | event_is_visible_to, filter_events_for_player, strip_thinking, truncate_text, sanitize_event_message (+2) |

## Entry Points

Start here when exploring this area:

- **`build_god_timeline`** (Function) — `src/llm_werewolf/evaluation/log_views/builder.py:69`
- **`build_player_timeline`** (Function) — `src/llm_werewolf/evaluation/log_views/builder.py:76`
- **`build_public_digest`** (Function) — `src/llm_werewolf/evaluation/log_views/builder.py:89`
- **`build_swing_digest`** (Function) — `src/llm_werewolf/evaluation/log_views/builder.py:101`
- **`build_role_timeline`** (Function) — `src/llm_werewolf/evaluation/log_views/builder.py:125`

## Key Symbols

| Symbol                     | Type     | File                                               | Line |
| -------------------------- | -------- | -------------------------------------------------- | ---- |
| `build_god_timeline`       | Function | `src/llm_werewolf/evaluation/log_views/builder.py` | 69   |
| `build_player_timeline`    | Function | `src/llm_werewolf/evaluation/log_views/builder.py` | 76   |
| `build_public_digest`      | Function | `src/llm_werewolf/evaluation/log_views/builder.py` | 89   |
| `build_swing_digest`       | Function | `src/llm_werewolf/evaluation/log_views/builder.py` | 101  |
| `build_role_timeline`      | Function | `src/llm_werewolf/evaluation/log_views/builder.py` | 125  |
| `write_log_views`          | Function | `src/llm_werewolf/evaluation/log_views/builder.py` | 160  |
| `event_is_visible_to`      | Function | `src/llm_werewolf/evaluation/log_views/filters.py` | 14   |
| `filter_events_for_player` | Function | `src/llm_werewolf/evaluation/log_views/filters.py` | 24   |
| `strip_thinking`           | Function | `src/llm_werewolf/evaluation/log_views/filters.py` | 36   |
| `truncate_text`            | Function | `src/llm_werewolf/evaluation/log_views/filters.py` | 44   |
| `sanitize_event_message`   | Function | `src/llm_werewolf/evaluation/log_views/filters.py` | 51   |
| `event_line`               | Function | `src/llm_werewolf/evaluation/log_views/filters.py` | 55   |
| `estimate_tokens`          | Function | `src/llm_werewolf/evaluation/log_views/filters.py` | 63   |
| `to_dict`                  | Method   | `src/llm_werewolf/evaluation/log_views/builder.py` | 52   |
| `_write_text`              | Function | `src/llm_werewolf/evaluation/log_views/builder.py` | 56   |
| `_write_json`              | Function | `src/llm_werewolf/evaluation/log_views/builder.py` | 62   |

## Execution Flows

| Flow                                          | Type            | Steps |
| --------------------------------------------- | --------------- | ----- |
| `Write_log_views → Strip_thinking`            | intra_community | 6     |
| `Build_role_timeline → Strip_thinking`        | intra_community | 5     |
| `Build_player_timeline → Strip_thinking`      | intra_community | 5     |
| `Write_log_views → Estimate_tokens`           | intra_community | 3     |
| `Build_role_timeline → Event_is_visible_to`   | intra_community | 3     |
| `Build_player_timeline → Event_is_visible_to` | intra_community | 3     |

## Connected Areas

| Area      | Connections |
| --------- | ----------- |
| Post_game | 1 calls     |

## How to Explore

1. `gitnexus_context({name: "build_god_timeline"})` — see callers and callees
2. `gitnexus_query({query: "log_views"})` — find related execution flows
3. Read key files listed above for implementation details
