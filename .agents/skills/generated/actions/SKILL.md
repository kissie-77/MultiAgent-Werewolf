---
name: actions
description: "Skill for the Actions area of MultiAgent-Werewolf. 51 symbols across 6 files."
---

# Actions

51 symbols | 6 files | Cohesion: 94%

## When to Use

- Working with code in `src/`
- Understanding how player_camp_is, test_werewolf_vote_action, test_werewolf_vote_rejects_wolf_target work
- Modifying actions-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/llm_werewolf/game_runtime/actions/villager.py` | WitchSaveAction, WitchPoisonAction, SeerCheckAction, GuardProtectAction, CupidLinkAction (+18) |
| `src/llm_werewolf/game_runtime/actions/werewolf.py` | WerewolfVoteAction, WerewolfKillAction, WhiteWolfKillAction, WolfBeautyCharmAction, GuardianWolfProtectAction (+10) |
| `tests/game_runtime/test_actions.py` | test_werewolf_vote_action, test_werewolf_vote_rejects_wolf_target, test_seer_check_execute_records_round, test_seer_hidden_wolf_appears_villager, test_witch_save_validate_and_execute (+1) |
| `src/llm_werewolf/game_runtime/actions/common.py` | VoteAction, HunterShootAction, __init__, __init__ |
| `src/llm_werewolf/game_runtime/actions/base.py` | Action, __init__ |
| `src/llm_werewolf/game_runtime/roles/names.py` | player_camp_is |

## Entry Points

Start here when exploring this area:

- **`player_camp_is`** (Function) — `src/llm_werewolf/game_runtime/roles/names.py:47`
- **`test_werewolf_vote_action`** (Function) — `tests/game_runtime/test_actions.py:50`
- **`test_werewolf_vote_rejects_wolf_target`** (Function) — `tests/game_runtime/test_actions.py:61`
- **`test_seer_check_execute_records_round`** (Function) — `tests/game_runtime/test_actions.py:38`
- **`test_seer_hidden_wolf_appears_villager`** (Function) — `tests/game_runtime/test_actions.py:70`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Action` | Class | `src/llm_werewolf/game_runtime/actions/base.py` | 5 |
| `VoteAction` | Class | `src/llm_werewolf/game_runtime/actions/common.py` | 4 |
| `HunterShootAction` | Class | `src/llm_werewolf/game_runtime/actions/common.py` | 38 |
| `WitchSaveAction` | Class | `src/llm_werewolf/game_runtime/actions/villager.py` | 5 |
| `WitchPoisonAction` | Class | `src/llm_werewolf/game_runtime/actions/villager.py` | 46 |
| `SeerCheckAction` | Class | `src/llm_werewolf/game_runtime/actions/villager.py` | 85 |
| `GuardProtectAction` | Class | `src/llm_werewolf/game_runtime/actions/villager.py` | 116 |
| `CupidLinkAction` | Class | `src/llm_werewolf/game_runtime/actions/villager.py` | 157 |
| `RavenMarkAction` | Class | `src/llm_werewolf/game_runtime/actions/villager.py` | 211 |
| `GraveyardKeeperCheckAction` | Class | `src/llm_werewolf/game_runtime/actions/villager.py` | 241 |
| `KnightDuelAction` | Class | `src/llm_werewolf/game_runtime/actions/villager.py` | 275 |
| `WerewolfVoteAction` | Class | `src/llm_werewolf/game_runtime/actions/werewolf.py` | 5 |
| `WerewolfKillAction` | Class | `src/llm_werewolf/game_runtime/actions/werewolf.py` | 41 |
| `WhiteWolfKillAction` | Class | `src/llm_werewolf/game_runtime/actions/werewolf.py` | 71 |
| `WolfBeautyCharmAction` | Class | `src/llm_werewolf/game_runtime/actions/werewolf.py` | 129 |
| `GuardianWolfProtectAction` | Class | `src/llm_werewolf/game_runtime/actions/werewolf.py` | 172 |
| `NightmareWolfBlockAction` | Class | `src/llm_werewolf/game_runtime/actions/werewolf.py` | 207 |
| `player_camp_is` | Function | `src/llm_werewolf/game_runtime/roles/names.py` | 47 |
| `test_werewolf_vote_action` | Function | `tests/game_runtime/test_actions.py` | 50 |
| `test_werewolf_vote_rejects_wolf_target` | Function | `tests/game_runtime/test_actions.py` | 61 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Run → Get_camp` | cross_community | 7 |
| `Get_winner → Get_camp` | cross_community | 7 |
| `Main → Get_camp` | cross_community | 6 |
| `Main → Get_camp` | cross_community | 6 |
| `Step → Get_camp` | cross_community | 6 |
| `Run → Get_camp` | cross_community | 6 |
| `Wolf_player_ids → Get_camp` | cross_community | 4 |
| `Execute → Get_camp` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Game_runtime | 1 calls |
| Roles | 1 calls |

## How to Explore

1. `gitnexus_context({name: "player_camp_is"})` — see callers and callees
2. `gitnexus_query({query: "actions"})` — find related execution flows
3. Read key files listed above for implementation details
