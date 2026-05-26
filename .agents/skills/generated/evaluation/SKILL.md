---
name: evaluation
description: "Skill for the Evaluation area of MultiAgent-Werewolf. 59 symbols across 15 files."
---

# Evaluation

59 symbols | 15 files | Cohesion: 87%

## When to Use

- Working with code in `src/`
- Understanding how build_camp_persuasion_report, format_camp_markdown, write_camp_persuasion_artifacts work
- Modifying evaluation-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/llm_werewolf/evaluation/vote_swing_analysis.py` | to_dict, _intentions_summary, _influence_score, analyze_speech_records, _read_jsonl (+5) |
| `src/llm_werewolf/evaluation/checkers.py` | check, _bad_case, _extract_speech_text, _check_response_format, _check_low_information_speech (+4) |
| `src/llm_werewolf/evaluation/runner.py` | on_event, run_scenario, _build_engine, _run_checkers, _error_event_checks (+2) |
| `src/llm_werewolf/evaluation/recorder.py` | record_event, record_snapshot, record_error, _append_jsonl, record_vote_intentions (+1) |
| `src/llm_werewolf/evaluation/post_game/camp_persuasion.py` | to_dict, _eliminations_by_round, build_camp_persuasion_report, format_camp_markdown, write_camp_persuasion_artifacts |
| `src/llm_werewolf/evaluation/reporter.py` | write, _write_summary, _write_metrics_csv, _write_report |
| `src/llm_werewolf/evaluation/scenarios.py` | smoke_6p_basic, regression_default_demo, get_scenario |
| `tests/evaluation/test_scoring.py` | _fixture_events, test_intention_scores_swing_to_final_vote, test_benefit_scores_partial_metrics |
| `tests/evaluation/test_skill_extractor.py` | _fixture_events, test_write_role_skills_only_generates_passed_candidates, test_build_role_skills_no_placeholder_for_all_roles |
| `tests/evaluation/test_vote_swing_analysis.py` | _sample_record, test_analyze_speech_records, test_write_persuasion_artifacts |

## Entry Points

Start here when exploring this area:

- **`build_camp_persuasion_report`** (Function) — `src/llm_werewolf/evaluation/post_game/camp_persuasion.py:138`
- **`format_camp_markdown`** (Function) — `src/llm_werewolf/evaluation/post_game/camp_persuasion.py:183`
- **`write_camp_persuasion_artifacts`** (Function) — `src/llm_werewolf/evaluation/post_game/camp_persuasion.py:216`
- **`analyze_speech_records`** (Function) — `src/llm_werewolf/evaluation/vote_swing_analysis.py:112`
- **`load_speech_records`** (Function) — `src/llm_werewolf/evaluation/vote_swing_analysis.py:166`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `build_camp_persuasion_report` | Function | `src/llm_werewolf/evaluation/post_game/camp_persuasion.py` | 138 |
| `format_camp_markdown` | Function | `src/llm_werewolf/evaluation/post_game/camp_persuasion.py` | 183 |
| `write_camp_persuasion_artifacts` | Function | `src/llm_werewolf/evaluation/post_game/camp_persuasion.py` | 216 |
| `analyze_speech_records` | Function | `src/llm_werewolf/evaluation/vote_swing_analysis.py` | 112 |
| `load_speech_records` | Function | `src/llm_werewolf/evaluation/vote_swing_analysis.py` | 166 |
| `analyze_path` | Function | `src/llm_werewolf/evaluation/vote_swing_analysis.py` | 202 |
| `format_markdown_report` | Function | `src/llm_werewolf/evaluation/vote_swing_analysis.py` | 207 |
| `write_persuasion_artifacts` | Function | `src/llm_werewolf/evaluation/vote_swing_analysis.py` | 261 |
| `main` | Function | `src/llm_werewolf/interface/vote_swing_cli.py` | 13 |
| `on_event` | Function | `src/llm_werewolf/evaluation/runner.py` | 84 |
| `test_recorder_writes_events_snapshots_errors_and_checks` | Function | `tests/evaluation/test_recorder.py` | 25 |
| `build_summary` | Function | `src/llm_werewolf/evaluation/metrics.py` | 5 |
| `test_runner_writes_artifacts_for_smoke_scenario` | Function | `tests/evaluation/test_runner.py` | 7 |
| `smoke_6p_basic` | Function | `src/llm_werewolf/evaluation/scenarios.py` | 26 |
| `regression_default_demo` | Function | `src/llm_werewolf/evaluation/scenarios.py` | 45 |
| `get_scenario` | Function | `src/llm_werewolf/evaluation/scenarios.py` | 66 |
| `main` | Function | `src/llm_werewolf/interface/eval_cli.py` | 9 |
| `test_intention_scores_swing_to_final_vote` | Function | `tests/evaluation/test_scoring.py` | 64 |
| `test_benefit_scores_partial_metrics` | Function | `tests/evaluation/test_scoring.py` | 87 |
| `test_write_role_skills_only_generates_passed_candidates` | Function | `tests/evaluation/test_skill_extractor.py` | 139 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → Resolve_visible_to` | cross_community | 7 |
| `Main → Get_role_name` | cross_community | 7 |
| `Main → Is_alive` | cross_community | 7 |
| `Run → Get_private_notes` | cross_community | 7 |
| `Run → _extract_witch_data` | cross_community | 7 |
| `Main → _attach_agent_to_player` | cross_community | 6 |
| `Run_post_game_pipeline_sync → _influence_score` | cross_community | 6 |
| `Run_post_game_pipeline_sync → _intentions_summary` | cross_community | 6 |
| `Run_post_game_pipeline → _read_jsonl` | cross_community | 5 |
| `Run_post_game_pipeline → _records_from_events` | cross_community | 5 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Integration | 2 calls |
| Scripts | 1 calls |
| Post_game | 1 calls |
| Game_runtime | 1 calls |
| Agent_team | 1 calls |
| Scoring | 1 calls |

## How to Explore

1. `gitnexus_context({name: "build_camp_persuasion_report"})` — see callers and callees
2. `gitnexus_query({query: "evaluation"})` — find related execution flows
3. Read key files listed above for implementation details
