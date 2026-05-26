---
name: scoring
description: "Skill for the Scoring area of MultiAgent-Werewolf. 13 symbols across 5 files."
---

# Scoring

13 symbols | 5 files | Cohesion: 85%

## When to Use

- Working with code in `src/`
- Understanding how target_id_to_camp, is_camp_aligned_vote_target, build_benefit_scores work
- Modifying scoring-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/llm_werewolf/evaluation/scoring/intention.py` | _final_votes_by_round, _swing_to_final_vote_count, _persuasion_net, build_intention_scores, write_intention_scores |
| `src/llm_werewolf/evaluation/scoring/benefit.py` | _eliminations, _elimination_aligned_for_player, build_benefit_scores, write_benefit_scores |
| `src/llm_werewolf/evaluation/post_game/run_context.py` | target_id_to_camp, is_camp_aligned_vote_target |
| `src/llm_werewolf/evaluation/post_game/camp_persuasion.py` | _annotate_swings |
| `src/llm_werewolf/evaluation/scoring/models.py` | to_dict |

## Entry Points

Start here when exploring this area:

- **`target_id_to_camp`** (Function) — `src/llm_werewolf/evaluation/post_game/run_context.py:308`
- **`is_camp_aligned_vote_target`** (Function) — `src/llm_werewolf/evaluation/post_game/run_context.py:315`
- **`build_benefit_scores`** (Function) — `src/llm_werewolf/evaluation/scoring/benefit.py:48`
- **`write_benefit_scores`** (Function) — `src/llm_werewolf/evaluation/scoring/benefit.py:100`
- **`build_intention_scores`** (Function) — `src/llm_werewolf/evaluation/scoring/intention.py:64`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `target_id_to_camp` | Function | `src/llm_werewolf/evaluation/post_game/run_context.py` | 308 |
| `is_camp_aligned_vote_target` | Function | `src/llm_werewolf/evaluation/post_game/run_context.py` | 315 |
| `build_benefit_scores` | Function | `src/llm_werewolf/evaluation/scoring/benefit.py` | 48 |
| `write_benefit_scores` | Function | `src/llm_werewolf/evaluation/scoring/benefit.py` | 100 |
| `build_intention_scores` | Function | `src/llm_werewolf/evaluation/scoring/intention.py` | 64 |
| `write_intention_scores` | Function | `src/llm_werewolf/evaluation/scoring/intention.py` | 105 |
| `to_dict` | Method | `src/llm_werewolf/evaluation/scoring/models.py` | 20 |
| `_annotate_swings` | Function | `src/llm_werewolf/evaluation/post_game/camp_persuasion.py` | 109 |
| `_eliminations` | Function | `src/llm_werewolf/evaluation/scoring/benefit.py` | 15 |
| `_elimination_aligned_for_player` | Function | `src/llm_werewolf/evaluation/scoring/benefit.py` | 30 |
| `_final_votes_by_round` | Function | `src/llm_werewolf/evaluation/scoring/intention.py` | 14 |
| `_swing_to_final_vote_count` | Function | `src/llm_werewolf/evaluation/scoring/intention.py` | 29 |
| `_persuasion_net` | Function | `src/llm_werewolf/evaluation/scoring/intention.py` | 49 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Write_camp_persuasion_artifacts → Target_id_to_camp` | cross_community | 4 |
| `Write_camp_persuasion_artifacts → Is_camp_aligned_vote_target` | cross_community | 4 |
| `Write_benefit_scores → Target_id_to_camp` | intra_community | 4 |
| `Write_benefit_scores → _elimination_aligned_for_player` | intra_community | 3 |
| `Write_intention_scores → To_dict` | intra_community | 3 |
| `Write_intention_scores → _final_votes_by_round` | intra_community | 3 |
| `Write_intention_scores → _swing_to_final_vote_count` | intra_community | 3 |
| `Write_intention_scores → _persuasion_net` | intra_community | 3 |

## How to Explore

1. `gitnexus_context({name: "target_id_to_camp"})` — see callers and callees
2. `gitnexus_query({query: "scoring"})` — find related execution flows
3. Read key files listed above for implementation details
