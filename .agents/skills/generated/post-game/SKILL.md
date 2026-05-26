---
name: post-game
description: "Skill for the Post_game area of MultiAgent-Werewolf. 44 symbols across 10 files."
---

# Post_game

44 symbols | 10 files | Cohesion: 76%

## When to Use

- Working with code in `src/`
- Understanding how build_role_skills, evaluate_persuasion_speech, evaluate_night_action_event work
- Modifying post_game-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/llm_werewolf/evaluation/post_game/run_context.py` | _read_jsonl, merge_rosters, winner_from_events, roster_from_engine, load_run_context (+6) |
| `src/llm_werewolf/evaluation/post_game/skill_generation_rules.py` | _role_key_for_player, evaluate_persuasion_speech, evaluate_night_action_event, _speech_rank_score, _night_rank_score (+2) |
| `src/llm_werewolf/evaluation/post_game/skill_extractor.py` | build_role_skills, _build_skipped_summary, _slug, _skill_from_candidate, _skill_from_persuasion (+1) |
| `src/llm_werewolf/evaluation/post_game/prompt_proposal.py` | _events_from_dicts, _role_key_for_speaker, _proposal_from_speech, _proposal_from_bad_case, build_prompt_proposals (+1) |
| `src/llm_werewolf/evaluation/post_game/eval_agent.py` | _load_analyst_config, _extract_text, _parse_json_response, build_replay_prompt, run_eval_replay |
| `src/llm_werewolf/evaluation/post_game/pipeline.py` | to_dict, run_post_game_pipeline, run_post_game_pipeline_sync |
| `tests/evaluation/test_run_context.py` | test_roster_from_role_acting_events, test_load_run_context_doubao_run_roster |
| `src/llm_werewolf/evaluation/post_game/replay_agent.py` | run_llm_replay, write_post_game_analysis |
| `src/llm_werewolf/game_runtime/prompts/manager.py` | get_prompt_role_key |
| `src/llm_werewolf/agent_team/factory.py` | create_react_agent |

## Entry Points

Start here when exploring this area:

- **`build_role_skills`** (Function) — `src/llm_werewolf/evaluation/post_game/skill_extractor.py:154`
- **`evaluate_persuasion_speech`** (Function) — `src/llm_werewolf/evaluation/post_game/skill_generation_rules.py:57`
- **`evaluate_night_action_event`** (Function) — `src/llm_werewolf/evaluation/post_game/skill_generation_rules.py:89`
- **`collect_skill_generation_candidates`** (Function) — `src/llm_werewolf/evaluation/post_game/skill_generation_rules.py:135`
- **`generation_rules_summary`** (Function) — `src/llm_werewolf/evaluation/post_game/skill_generation_rules.py:202`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `build_role_skills` | Function | `src/llm_werewolf/evaluation/post_game/skill_extractor.py` | 154 |
| `evaluate_persuasion_speech` | Function | `src/llm_werewolf/evaluation/post_game/skill_generation_rules.py` | 57 |
| `evaluate_night_action_event` | Function | `src/llm_werewolf/evaluation/post_game/skill_generation_rules.py` | 89 |
| `collect_skill_generation_candidates` | Function | `src/llm_werewolf/evaluation/post_game/skill_generation_rules.py` | 135 |
| `generation_rules_summary` | Function | `src/llm_werewolf/evaluation/post_game/skill_generation_rules.py` | 202 |
| `test_roster_from_role_acting_events` | Function | `tests/evaluation/test_run_context.py` | 8 |
| `test_load_run_context_doubao_run_roster` | Function | `tests/evaluation/test_run_context.py` | 36 |
| `create_react_agent` | Function | `src/llm_werewolf/agent_team/factory.py` | 63 |
| `build_replay_prompt` | Function | `src/llm_werewolf/evaluation/post_game/eval_agent.py` | 67 |
| `run_eval_replay` | Function | `src/llm_werewolf/evaluation/post_game/eval_agent.py` | 110 |
| `run_llm_replay` | Function | `src/llm_werewolf/evaluation/post_game/replay_agent.py` | 16 |
| `build_prompt_proposals` | Function | `src/llm_werewolf/evaluation/post_game/prompt_proposal.py` | 110 |
| `write_prompt_proposals` | Function | `src/llm_werewolf/evaluation/post_game/prompt_proposal.py` | 151 |
| `merge_rosters` | Function | `src/llm_werewolf/evaluation/post_game/run_context.py` | 208 |
| `winner_from_events` | Function | `src/llm_werewolf/evaluation/post_game/run_context.py` | 232 |
| `roster_from_engine` | Function | `src/llm_werewolf/evaluation/post_game/run_context.py` | 243 |
| `load_run_context` | Function | `src/llm_werewolf/evaluation/post_game/run_context.py` | 259 |
| `run_post_game_pipeline` | Function | `src/llm_werewolf/evaluation/post_game/pipeline.py` | 38 |
| `run_post_game_pipeline_sync` | Function | `src/llm_werewolf/evaluation/post_game/pipeline.py` | 129 |
| `write_post_game_analysis` | Function | `src/llm_werewolf/evaluation/post_game/replay_agent.py` | 34 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Bind_role_prompt → Get_prompt_role_key` | cross_community | 6 |
| `Run_post_game_pipeline_sync → _influence_score` | cross_community | 6 |
| `Run_post_game_pipeline_sync → _intentions_summary` | cross_community | 6 |
| `Run_post_game_pipeline → _read_jsonl` | cross_community | 5 |
| `Run_post_game_pipeline → _records_from_events` | cross_community | 5 |
| `Load_run_context → Get_definition` | cross_community | 5 |
| `Write_role_skills_artifacts → Get_prompt_role_key` | cross_community | 5 |
| `Write_role_skills_artifacts → _slug` | cross_community | 5 |
| `Reset → Get_prompt_role_key` | cross_community | 5 |
| `Run_post_game_pipeline_sync → _role_hint_from_event` | cross_community | 5 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Scoring | 3 calls |
| Evaluation | 2 calls |
| Agent_team | 2 calls |
| Roles | 1 calls |
| Interface | 1 calls |

## How to Explore

1. `gitnexus_context({name: "build_role_skills"})` — see callers and callees
2. `gitnexus_query({query: "post_game"})` — find related execution flows
3. Read key files listed above for implementation details
