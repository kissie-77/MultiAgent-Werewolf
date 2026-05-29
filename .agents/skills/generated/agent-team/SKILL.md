---
name: agent-team
description: "Skill for the Agent_team area of MultiAgent-Werewolf. 167 symbols across 35 files."
---

# Agent_team

167 symbols | 35 files | Cohesion: 85%

## When to Use

- Working with code in `src/`
- Understanding how agent_uses_structured_output, invoke_structured, vote_intention_schema_instruction work
- Modifying agent_team-related functionality

## Key Files

| File                                                     | Symbols                                                                                                                                                                                                                                           |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/llm_werewolf/agent_team/bridge.py`                  | get_player_seat, resolve_player_by_seat, parse_yes_no, parse_multi_target_selection, build_target_selection_prompt (+16)                                                                                                                          |
| `src/llm_werewolf/agent_team/agentscope_agent.py`        | \_call_agentscope_agent, get_structured_response, \_extract_agentscope_text, extract_target, extract_content (+13)                                                                                                                                |
| `tests/agent_team/test_message.py`                       | test_chat_history_to_msgs, test_msgs_to_chat_history, test_chat_history_roundtrip, test_get_text_content_string, test_get_text_content_blocks (+13)                                                                                               |
| `src/llm_werewolf/agent_team/information_hub.py`         | \_call, \_react_agent, \_resolve_audience, \_deliver_private, \_broadcast_moderator (+11)                                                                                                                                                         |
| `src/llm_werewolf/strategy/decisions.py`                 | vote_intention_schema_instruction, seat_choice_schema_instruction, witch_night_schema_instruction, speech_schema_instruction, validate_public_speech (+6)                                                                                         |
| `src/llm_werewolf/agent_team/message.py`                 | chat_history_to_msgs, msgs_to_chat_history, get_text_content, str_to_msg, msg_to_str (+6)                                                                                                                                                         |
| `src/llm_werewolf/agent_team/skill_loader.py`            | load_role_skills_text, agent_skills_root, \_parse_frontmatter, \_load_skill_file, list_role_skill_files (+2)                                                                                                                                      |
| `src/llm_werewolf/agent_team/human_interactive_agent.py` | HumanInteractiveAgent, \_render_prompt, \_classify, \_hint, \_normalize (+1)                                                                                                                                                                      |
| `tests/agent_team/test_bridge_parsing.py`                | test_yes_no_accepts_bracketed_binary_answers, test_target_selection_uses_player_seat_not_list_position, test_target_selection_rejects_illegal_seat, test_target_selection_can_parse_seat_from_player_name, test_target_selection_allows_zero_skip |
| `tests/agent_team/test_agentscope_agent_fallback.py`     | test_no_good_identity_in_wolf_night_chat, test_wolf_team_marker_detected, test_no_role_reveal_on_day_speech, test_yes_no, test_numeric_target                                                                                                     |

## Entry Points

Start here when exploring this area:

- **`agent_uses_structured_output`** (Function) — `src/llm_werewolf/agent_team/structured_invoke.py:22`
- **`invoke_structured`** (Function) — `src/llm_werewolf/agent_team/structured_invoke.py:47`
- **`vote_intention_schema_instruction`** (Function) — `src/llm_werewolf/strategy/decisions.py:135`
- **`seat_choice_schema_instruction`** (Function) — `src/llm_werewolf/strategy/decisions.py:148`
- **`witch_night_schema_instruction`** (Function) — `src/llm_werewolf/strategy/decisions.py:162`

## Key Symbols

| Symbol                                         | Type     | File                                                     | Line |
| ---------------------------------------------- | -------- | -------------------------------------------------------- | ---- |
| `AgentScopeWerewolfAgent`                      | Class    | `src/llm_werewolf/agent_team/agentscope_agent.py`        | 27   |
| `BaseAgent`                                    | Class    | `src/llm_werewolf/agent_team/base.py`                    | 13   |
| `DemoAgent`                                    | Class    | `src/llm_werewolf/agent_team/base.py`                    | 32   |
| `HumanAgent`                                   | Class    | `src/llm_werewolf/agent_team/base.py`                    | 85   |
| `HumanInteractiveAgent`                        | Class    | `src/llm_werewolf/agent_team/human_interactive_agent.py` | 56   |
| `PromptAgentMixin`                             | Class    | `src/llm_werewolf/agent_team/mixin.py`                   | 7    |
| `agent_uses_structured_output`                 | Function | `src/llm_werewolf/agent_team/structured_invoke.py`       | 22   |
| `invoke_structured`                            | Function | `src/llm_werewolf/agent_team/structured_invoke.py`       | 47   |
| `vote_intention_schema_instruction`            | Function | `src/llm_werewolf/strategy/decisions.py`                 | 135  |
| `seat_choice_schema_instruction`               | Function | `src/llm_werewolf/strategy/decisions.py`                 | 148  |
| `witch_night_schema_instruction`               | Function | `src/llm_werewolf/strategy/decisions.py`                 | 162  |
| `action_phase_instruction`                     | Function | `src/llm_werewolf/strategy/phase_outputs.py`             | 124  |
| `test_yes_no_accepts_bracketed_binary_answers` | Function | `tests/agent_team/test_bridge_parsing.py`                | 46   |
| `run_serial_agent_call`                        | Function | `src/llm_werewolf/agent_team/serial_calls.py`            | 28   |
| `unwrap_structured_metadata`                   | Function | `src/llm_werewolf/agent_team/structured_invoke.py`       | 27   |
| `coerce_speech`                                | Function | `src/llm_werewolf/agent_team/structured_invoke.py`       | 104  |
| `speech_schema_instruction`                    | Function | `src/llm_werewolf/strategy/decisions.py`                 | 29   |
| `metadata_looks_like_wrong_schema_for_speech`  | Function | `src/llm_werewolf/strategy/decisions.py`                 | 195  |
| `looks_like_kill_or_vote_format`               | Function | `src/llm_werewolf/strategy/decisions.py`                 | 206  |
| `looks_like_seat_only`                         | Function | `src/llm_werewolf/strategy/decisions.py`                 | 222  |

## Execution Flows

| Flow                                             | Type            | Steps |
| ------------------------------------------------ | --------------- | ----- |
| `Reset → _require_spec`                          | cross_community | 8     |
| `Reset → Agent_skills_root`                      | cross_community | 8     |
| `Reset → _parse_frontmatter`                     | cross_community | 8     |
| `Bind_role_prompt → Agent_skills_root`           | cross_community | 8     |
| `Bind_role_prompt → _parse_frontmatter`          | cross_community | 8     |
| `Request_speech → Looks_like_seat_only`          | intra_community | 7     |
| `Configure_role → _require_spec`                 | cross_community | 7     |
| `Bind_role_prompt → _require_spec`               | cross_community | 7     |
| `Bind_role_prompt → Get_registry`                | cross_community | 7     |
| `Get_structured_response → Looks_like_seat_only` | intra_community | 6     |

## Connected Areas

| Area      | Connections |
| --------- | ----------- |
| Engine    | 7 calls     |
| Post_game | 5 calls     |
| Strategy  | 4 calls     |
| Prompts   | 1 calls     |

## How to Explore

1. `gitnexus_context({name: "agent_uses_structured_output"})` — see callers and callees
2. `gitnexus_query({query: "agent_team"})` — find related execution flows
3. Read key files listed above for implementation details
