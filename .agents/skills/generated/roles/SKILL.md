---
name: roles
description: "Skill for the Roles area of MultiAgent-Werewolf. 68 symbols across 15 files."
---

# Roles

68 symbols | 15 files | Cohesion: 88%

## When to Use

- Working with code in `src/`
- Understanding how get_role_class, list_roles, import_role_class work
- Modifying roles-related functionality

## Key Files

| File                                                   | Symbols                                                                                               |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `src/llm_werewolf/game_runtime/roles/villager.py`      | Villager, Seer, Witch, Hunter, Guard (+16)                                                            |
| `src/llm_werewolf/game_runtime/roles/werewolf.py`      | Werewolf, AlphaWolf, WhiteWolf, WolfBeauty, GuardianWolf (+7)                                         |
| `src/llm_werewolf/game_runtime/roles/neutral.py`       | Thief, Lover, WhiteLoverWolf, __init__, __init__ (+1)                                                 |
| `src/llm_werewolf/game_runtime/roles/registry.py`      | get_role_map, runtime_role_name, build_catalog_to_runtime_map, create_roles, get_role_definition (+1) |
| `src/llm_werewolf/game_runtime/roles/base.py`          | Role, __init__, get_config, get_private_notes                                                         |
| `src/llm_werewolf/game_runtime/role_night_plans.py`    | \_werewolf_context, plan_white_wolf, plan_guardian_wolf, blood_moon_other_wolves_alive                |
| `src/llm_werewolf/evaluation/post_game/run_context.py` | \_runtime_role_camp_map, role_name_to_camp, \_apply_role                                              |
| `src/llm_werewolf/game_runtime/roles/names.py`         | role_name_is, is_untransformed_blood_moon, seer_apparent_camp                                         |
| `src/llm_werewolf/game_runtime/role_registry.py`       | get_role_class, list_roles                                                                            |
| `src/llm_werewolf/game_runtime/roles/loader.py`        | import_role_class, role_class_from_definition                                                         |

## Entry Points

Start here when exploring this area:

- **`get_role_class`** (Function) — `src/llm_werewolf/game_runtime/role_registry.py:11`
- **`list_roles`** (Function) — `src/llm_werewolf/game_runtime/role_registry.py:16`
- **`import_role_class`** (Function) — `src/llm_werewolf/game_runtime/roles/loader.py:11`
- **`role_class_from_definition`** (Function) — `src/llm_werewolf/game_runtime/roles/loader.py:25`
- **`get_role_map`** (Function) — `src/llm_werewolf/game_runtime/roles/registry.py:20`

## Key Symbols

| Symbol            | Type  | File                                              | Line |
| ----------------- | ----- | ------------------------------------------------- | ---- |
| `Role`            | Class | `src/llm_werewolf/game_runtime/roles/base.py`     | 11   |
| `Thief`           | Class | `src/llm_werewolf/game_runtime/roles/neutral.py`  | 11   |
| `Lover`           | Class | `src/llm_werewolf/game_runtime/roles/neutral.py`  | 41   |
| `WhiteLoverWolf`  | Class | `src/llm_werewolf/game_runtime/roles/neutral.py`  | 75   |
| `Villager`        | Class | `src/llm_werewolf/game_runtime/roles/villager.py` | 21   |
| `Seer`            | Class | `src/llm_werewolf/game_runtime/roles/villager.py` | 44   |
| `Witch`           | Class | `src/llm_werewolf/game_runtime/roles/villager.py` | 81   |
| `Hunter`          | Class | `src/llm_werewolf/game_runtime/roles/villager.py` | 120  |
| `Guard`           | Class | `src/llm_werewolf/game_runtime/roles/villager.py` | 143  |
| `Idiot`           | Class | `src/llm_werewolf/game_runtime/roles/villager.py` | 179  |
| `Elder`           | Class | `src/llm_werewolf/game_runtime/roles/villager.py` | 206  |
| `Knight`          | Class | `src/llm_werewolf/game_runtime/roles/villager.py` | 234  |
| `Magician`        | Class | `src/llm_werewolf/game_runtime/roles/villager.py` | 263  |
| `Cupid`           | Class | `src/llm_werewolf/game_runtime/roles/villager.py` | 291  |
| `Raven`           | Class | `src/llm_werewolf/game_runtime/roles/villager.py` | 321  |
| `GraveyardKeeper` | Class | `src/llm_werewolf/game_runtime/roles/villager.py` | 345  |
| `Werewolf`        | Class | `src/llm_werewolf/game_runtime/roles/werewolf.py` | 27   |
| `AlphaWolf`       | Class | `src/llm_werewolf/game_runtime/roles/werewolf.py` | 64   |
| `WhiteWolf`       | Class | `src/llm_werewolf/game_runtime/roles/werewolf.py` | 87   |
| `WolfBeauty`      | Class | `src/llm_werewolf/game_runtime/roles/werewolf.py` | 111  |

## Execution Flows

| Flow                                   | Type            | Steps |
| -------------------------------------- | --------------- | ----- |
| `Load_game → Import_role_class`        | cross_community | 7     |
| `Run → Role_name_is`                   | cross_community | 7     |
| `Get_winner → Role_name_is`            | cross_community | 7     |
| `Main → Role_name_is`                  | cross_community | 6     |
| `Main → Role_name_is`                  | cross_community | 6     |
| `Step → Role_name_is`                  | cross_community | 6     |
| `Run → Role_name_is`                   | cross_community | 6     |
| `Load_run_context → Get_definition`    | cross_community | 5     |
| `Plan_white_wolf → Get_private_notes`  | cross_community | 5     |
| `Plan_wolf_beauty → Get_private_notes` | cross_community | 5     |

## Connected Areas

| Area         | Connections |
| ------------ | ----------- |
| Game_runtime | 4 calls     |
| Engine       | 2 calls     |
| Prompts      | 1 calls     |
| Actions      | 1 calls     |

## How to Explore

1. `gitnexus_context({name: "get_role_class"})` — see callers and callees
2. `gitnexus_query({query: "roles"})` — find related execution flows
3. Read key files listed above for implementation details
