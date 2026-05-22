# 讨论子阶段输出规范

讨论类回合**只**允许 `SpeechDecision`；选刀/投票/技能目标在**独立步骤**用 `SeatChoiceDecision` 或 `YesNoDecision`。

## 圆桌讨论（`run_roundtable` / `collect_speech`）

| 子阶段 | `RoundtablePhase` | 输出 Schema | 必填字段 | 禁止 |
|--------|-------------------|-------------|----------|------|
| 白天讨论 | `day_discussion` | `SpeechDecision` | `public_speech` ≥15 字 | `[[数字]]`、仅座位号、刀/投/验/守/毒、`seat`/`choice`/`seats` |
| 狼队夜聊 | `wolf_team_discussion` | `SpeechDecision` | 同上 | 同上；选刀在讨论后的 `night_kill_vote` |
| 警长竞选发言 | `sheriff_campaign` | `SpeechDecision` | 同上 | 投票座位号、`seat` 字段 |

提示词标记：`【子阶段·仅发言】`（见 `core/phase_outputs.py`）。

## 行动阶段（非讨论）

| 子阶段 | `ActionPhase` | 输出 Schema | 说明 |
|--------|---------------|-------------|------|
| 狼队选刀 | `night_kill_vote` | `SeatChoiceDecision` | `seat` 全局座位号，弃票 0 |
| 夜晚技能目标 | `night_skill_target` | `SeatChoiceDecision` | 女巫/守卫/预言家等 |
| 白天放逐投票 | `day_vote` | `SeatChoiceDecision` | 弃票 `[[0]]` |
| 女巫夜间（狼刀后） | `witch_night` | `WitchNightDecision` | `action`=save/poison/none；有解药时可见刀口，解药用完后不可见 |
| 是否上警 | `sheriff_run` | `SeatChoiceDecision` | 1=参加，0=不参加 |
| 警长投票 | `sheriff_vote` | `SeatChoiceDecision` | 候选人座位号 |
| 猎人开枪 | `death_shoot` | `SeatChoiceDecision` | 目标座位号 |
| 警徽流转 | `badge_transfer` | `SeatChoiceDecision` | 继承座位号，0=撕毁 |

## Event 与 MsgHub 分工

| 用途 | Event 日志 | MsgHub / ReAct 记忆 |
|------|------------|---------------------|
| 回放、UI、评测 | 写入 `PLAYER_SPEECH` / `PLAYER_DISCUSSION` / `SHERIFF_CANDIDATE_SPEECH` | — |
| 白天讨论 / 狼聊 / 警上发言 | 仅记录，**不**注入决策 prompt | 圆桌 `run_roundtable` 广播 |
| 投票 / 夜间技能 | 局面变化（死亡、阶段等） | 上文对话记忆 + `hub_decision_memory_notice` |

`build_player_observation(..., for_agent_decision=True)` 自动排除 `HUB_DIALOGUE_EVENT_TYPES`；`InformationHub.set_context_provider` 始终使用该模式。

## 引擎校验

- `is_valid_public_speech` 拒绝 `looks_like_kill_or_vote_format`（`[[7]]`、纯「刀7」等）。
- AgentScope 若 `metadata` 含 `seat` 且无 `public_speech`，视为错误 Schema，回退文本解析。
- `_message_expects_seat_only` 见到 `【子阶段·仅发言】` 时**不**把 `[[7]]` 当座位投票解析。
