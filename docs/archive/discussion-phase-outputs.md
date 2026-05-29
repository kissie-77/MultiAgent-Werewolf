# 讨论子阶段输出规范

讨论类回合**只**允许 `SpeechDecision`；选刀/投票/技能目标在**独立步骤**用 `SeatChoiceDecision` 或 `YesNoDecision`。

## 圆桌讨论（`run_roundtable` / `collect_speech`）

| 子阶段       | `RoundtablePhase`      | 输出 Schema      | 必填字段               | 禁止                                                          |
| ------------ | ---------------------- | ---------------- | ---------------------- | ------------------------------------------------------------- |
| 白天讨论     | `day_discussion`       | `SpeechDecision` | `public_speech` ≥15 字 | `[[数字]]`、仅座位号、刀/投/验/守/毒、`seat`/`choice`/`seats` |
| 狼队夜聊     | `wolf_team_discussion` | `SpeechDecision` | 同上                   | 同上；选刀在讨论后的 `night_kill_vote`                        |
| 警长竞选发言 | `sheriff_campaign`     | `SpeechDecision` | 同上                   | 投票座位号、`seat` 字段                                       |

提示词标记：`【子阶段·仅发言】`（见 `core/phase_outputs.py`）。

## 行动阶段（非讨论）

| 子阶段             | `ActionPhase`        | 输出 Schema          | 说明                                                          |
| ------------------ | -------------------- | -------------------- | ------------------------------------------------------------- |
| 狼队选刀           | `night_kill_vote`    | `SeatChoiceDecision` | `seat` 全局座位号，弃票 0                                     |
| 夜晚技能目标       | `night_skill_target` | `SeatChoiceDecision` | 女巫/守卫/预言家等                                            |
| 白天放逐投票       | `day_vote`           | `SeatChoiceDecision` | 弃票 `[[0]]`                                                  |
| 女巫夜间（狼刀后） | `witch_night`        | `WitchNightDecision` | `action`=save/poison/none；有解药时可见刀口，解药用完后不可见 |
| 是否上警           | `sheriff_run`        | `SeatChoiceDecision` | 1=参加，0=不参加                                              |
| 警长投票           | `sheriff_vote`       | `SeatChoiceDecision` | 候选人座位号                                                  |
| 猎人开枪           | `death_shoot`        | `SeatChoiceDecision` | 目标座位号                                                    |
| 警徽流转           | `badge_transfer`     | `SeatChoiceDecision` | 继承座位号，0=撕毁                                            |

## Event 与 MsgHub 分工

| 用途                       | Event 日志                                                              | MsgHub / ReAct 记忆                         |
| -------------------------- | ----------------------------------------------------------------------- | ------------------------------------------- |
| 回放、UI、评测             | 写入 `PLAYER_SPEECH` / `PLAYER_DISCUSSION` / `SHERIFF_CANDIDATE_SPEECH` | —                                           |
| 白天讨论 / 狼聊 / 警上发言 | 仅记录，**不**注入决策 prompt                                           | 圆桌 `run_roundtable` 广播                  |
| 投票 / 夜间技能            | 局面变化（死亡、阶段等）                                                | 上文对话记忆 + `hub_decision_memory_notice` |

`build_player_observation(..., for_agent_decision=True)` 自动排除 `HUB_DIALOGUE_EVENT_TYPES`；`InformationHub.set_context_provider` 始终使用该模式。

## 投票意向追踪（复盘）

圆桌讨论（白天 / 狼队夜聊 / 警上）按顺序采集投票意向（`VoteIntentionDecision`，`seat=0` 须由模型明示）：

| 顺序 | 步骤                                                  |
| ---- | ----------------------------------------------------- |
| 1    | **初始意向**：讨论开始前，频道内全体 Agent 各输出一次 |
| 2    | **发言人 1** 公开发言（写入 MsgHub）                  |
| 3    | **意向 1**：全体 Agent 根据发言 1 更新意向            |
| 4    | **发言人 2** 发言 → **意向 2** → …                    |

复盘对比：发言人 K 的 `before` = 意向 K-1（K=1 时为初始意向），`after` = 意向 K。

- 事件类型：`VOTE_INTENTION_SNAPSHOT`（`data` 含 before/after/swings）
- 配置：`GameConfig.track_vote_intentions`（默认 `true`）
- 评测产物：`vote_intentions.jsonl`（由 `EvaluationRecorder` 写入）
- 说服力分析：`vote_swing_report.md` / `vote_swing_summary.json`（评测结束或 CLI 对局后自动生成）
- 离线分析：`werewolf-vote-swing <游戏目录或 jsonl 路径>`

## 引擎校验

- `is_valid_public_speech` 拒绝 `looks_like_kill_or_vote_format`（`[[7]]`、纯「刀7」等）。
- AgentScope 若 `metadata` 含 `seat` 且无 `public_speech`，视为错误 Schema，回退文本解析。
- `_message_expects_seat_only` 见到 `【子阶段·仅发言】` 时**不**把 `[[7]]` 当座位投票解析。
