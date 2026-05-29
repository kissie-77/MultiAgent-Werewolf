# max_tokens 降配（⑤因子）对单局对局速度影响的 A/B 实验分析报告

**日期**: 2026-05-27 **模型**: deepseek-chat（非 reasoning，reasoning_tokens=0） **样本**: n=1/臂

---

## 1. 摘要（TL;DR）

在 deepseek-chat 上把 `max_tokens` 从 2048 降到 512 的 cap **从未触发**（两臂 `n_cap_or_length=0`，A 最大 completion=471、B 最大=383，均远低于各自上限）；观察到的整局墙钟差异（702.2s→467.3s）**主要来自两局轨迹方差**（166 vs 130 次调用、2 vs 4 存活的不同对局），而非 cap；又因 completion 仅占总 token **\<1%**、prompt（上下文）占 ~99%，故 **⑤（降 output token）对本模型几乎没有提速杠杆**。真正的杠杆是 ②（O(N²) 意向重轮询）与 ③（每决策第二次 round-trip）所驱动的**调用次数 / prompt 体量**。

---

## 2. 实验设计与偏离

**原计划**：在 **doubao**（reasoning 模型）6 人局上测 ⑤。理由是 reasoning 模型的输出（含思维链）体量大，`max_tokens` 上限对其生成时间的杠杆理论上最大，⑤ 的预期收益最高。

**实际偏离**（被迫两次换模型）：

1. **doubao 不可用** —— ARK key 已失效，返回 401 "key doesn't exist"。
2. **deepseek-v4-flash 不可用** —— 约 70% 调用返回 400 "thinking mode does not support tools"（thinking + tools 不兼容）。
3. **最终改用 deepseek-chat** —— 非 thinking、支持 tools、能打完整局。

**关键后果**：deepseek-chat 是**非 reasoning** 模型（`reasoning_tokens=0`），输出本就短。这意味着本实验 **不能直接验证**配套报告对 doubao 的 ⑤ 预测（reasoning 模型才是 ⑤ 收益假设的对象）。但它能补上 **deepseek 侧的数据**——这正是配套报告 §6 本就计划采集的部分，故实验仍有独立价值，只是结论的适用域被限定在 deepseek-chat。

---

## 3. 方法与计时器

- **插桩层**：在 HTTP 层（openai `AsyncCompletions.create` / `parse`）插桩，捕获每次调用的 `wall_s` / `prompt_tokens` / `completion_tokens` / `finish_reason` / `n_tool_calls` / `max_tokens_req`。
- **隔离变量**：仅隔离 ⑤。意向重轮询（`track_vote_intentions=True`）与 ③ 第二次 round-trip **均保持开启**，确保两臂唯一受控差异是 `max_tokens` 上限。
- **变量注入**：env-gated `WW_MAX_TOKENS_CAP`。Arm A 未设（用默认 **2048**），Arm B 设为 **512**，且已逐条确认 cap 如实下发到每一次调用（A 全部 `max_tokens_req=2048`，B 全部 =512）。
- **产物**：每臂一份 `*.json`（含 `summary` + 逐条 `calls[]`）与 `*.log`。

---

## 4. 结果数据表

| 指标                                  | Arm A (cap=2048, baseline)   | Arm B (cap=512)                                                            |
| ------------------------------------- | ---------------------------- | -------------------------------------------------------------------------- |
| HTTP 调用数                           | 166                          | 130                                                                        |
| 逻辑决策数（=调用/2）                 | 83                           | 65                                                                         |
| 整局 wall                             | 702.2s                       | 467.3s                                                                     |
| finish_reason                         | tool_calls 83 + stop 83      | tool_calls 65 + stop 65                                                    |
| n_cap_or_length（命中512截断）        | 0                            | 0                                                                          |
| n_truncated_no_tool（截断致决策丢失） | 0                            | 0                                                                          |
| prompt tokens                         | 3,290,728                    | 1,720,976                                                                  |
| completion tokens                     | 24,291                       | 15,340                                                                     |
| completion 占总 token                 | 0.73%                        | 0.88%                                                                      |
| per-call wall mean/p50/p95/max        | 4.18 / 3.95 / 7.58 / 10.48   | 3.53 / 3.27 / 5.94 / 8.29                                                  |
| wall/call（整局/调用）                | 4.23s                        | 3.59s                                                                      |
| completion tok/call                   | 146.3                        | 118.0                                                                      |
| 结局                                  | werewolf 胜，存活 2（P1,P5） | werewolf 胜，存活 4（P1,P3,P5,P6）                                         |
| 备注                                  | —                            | 另有 6 次 memory-compressor 400（独立 httpx 路径，已优雅回退，非决策调用） |

补充分布事实（经逐条 `calls[]` 复算）：

- **A 接近上限计数**：completion ≥2048→0；≥1024→0；≥512→0；仅 ≥400→3 条（418/451/471）。最慢的两次调用（10.48/10.4s）伴随高 completion（418/451）与大 prompt（35k/51k）。
- **B cap 咬合核对**：completion ≥512→0；≥461（90% cap）→0；≥410（80% cap）→0；峰值 383（约 75% cap）。top5 completion = [383, 318, 316, 308, 300]。
- **两臂 prompt/call 随对局推进单调增长**（上下文累积）：A 最高 67,230、B 最高 ~35,128。

---

## 5. 分析与对抗结论（逐条裁决）

> 下列断言经对抗审稿；裁决基于 `summary` 与逐条 `calls[]` 复算后的事实。

### 断言 1：「把 `max_tokens` 从 2048 降到 512，导致了对局提速（B 的 wall/call 3.59s 低于 A 的 4.23s，整局 702s→467s）。」

**裁决：✗ 证伪（信心 0.9）**
cap 在两臂**均未触发**（`n_cap_or_length=0`），且 A 的最大 completion=471\<512——**512 上限对 B 在机械上完全 inert**，不可能截断 B 的任何输出。所谓提速实为混杂：(1) B 本就是更短的另一局（130 vs 166 调用、4 vs 2 存活）；(2) 单调用变快源于 completion 更少（每类别 108–128 vs 142–151 tok），而**每 token 解码速率两臂几乎相同**（A≈72ms / B≈76ms，B 反而略慢）——说明速度由**生成量**决定，而非 cap 截断。n=1 无法区分 cap 效应与轨迹方差。

### 断言 2：「512 的 `max_tokens` cap 在 deepseek-chat 上是安全的，没有造成任何决策截断或破坏。」

**裁决：✓ 成立（信心 0.78）**
原始 `calls[]` 直接证实核心事实：B 臂 130 次调用**无一例** `length` / `content_filter` 截断；决策（tool_calls）最大 383 tok（=75% cap），无调用达 90% cap；无残缺工具调用（65 次 tool_calls 全部恰好携带 1 个 tool call，65 次 stop 全部 `n_tool_calls==0`）；`summary` 各项与原始数据逐项对齐。**"未发生截断/破坏"在本局成立**。
但需保留一处措辞偏差：**"安全"是一种泛化**——基线 A 已出现 471/451 tok（约 90% of 512）的输出，余量很薄；n=1 无方差，不能把"单局无截断"升级为"类别级安全保证"。故核心断言成立，仅"安全"二字偏强。

### 断言 3：「降低 `max_tokens` 是降低这局总 token 成本 / 提速的有效杠杆。」

**裁决：✗ 证伪（信心 0.93）**
cap 两臂均未触发（B 最大 completion=383\<512，`n_cap_or_length=0`），**无机械省 token / 提速通路**。234s 总 wall 差中：约 **127s** 来自 B 仅是更短的一局（130 vs 166 调用），约 **84s** 来自更低的 per-call wall——但按 completion 分桶匹配后两臂 per-call wall **几乎相同**（100–149 桶：3.82 vs 3.75），OLS 斜率亦近乎一致（~18.3 vs ~18.0 s/1k completion）。**completion 仅占 \<1% token，降其上限无法撼动总量**；真正省下的是 prompt（占 99%，因 B 是更短轨迹）。n=1 且两局轨迹不同，cap 效应与方差不可分。提速纯属轨迹混杂，非 cap 杠杆。

### 断言 4：「本实验（n=1/臂）足以把观察到的差异归因于 cap，而非对局轨迹方差。」

**裁决：✗ 证伪（信心 0.93）**
分解 234s 总 wall 差：**54%（127s）纯来自调用数**（166 vs 130，源于 2 vs 4 存活的不同对局轨迹）——这恰是断言想要排除的方差通道。cap 从未触发（`n_cap_or_length=0`；最大 completion A=471 / B=383 均\<512），无机械提速通路。剩余 **46% per-call 差**与 prompt 上下文分布混杂（A 达 65–70k，B 仅 ~38k）；同 prompt 桶内差缩到 ~0.39s 且**非单调**。n=1 无法分离残差与单端点延迟噪声（臂内 p95/p50≈1.8x）。

---

## 6. 经验证的真实发现

1. **③第二次 round-trip 被实锤**：两臂 `finish_reason` 恰好 **1:1**（A=83:83、B=65:65），且结构严格配对——每个 tool_calls 条目 `n_tool_calls==1`、每个 stop 条目 `n_tool_calls==0`。这直接验证配套报告 ③："每个结构化决策 = 1 次工具调用响应 + 1 次纯文本（stop）响应 = ×2 次 HTTP 调用"。

2. **token 成本由 prompt（上下文）主导**：两臂 completion 均 \<1%，prompt 占 ~99%。而 prompt 体量被**调用次数**驱动——②O(N²) 的意向重轮询每多一次决策就拉长一次上下文，③×2 又把每个决策翻倍成两次带满上下文的调用。

3. **结论的方向性**：在 deepseek-chat 上，**⑤ 不是杠杆**（output 本就 \<1%、cap 咬不到）；**② 和 ③ 才是**——它们决定调用次数，进而决定占 99% 成本的 prompt 总量。优化资源应投向减少调用次数，而非压低 output 上限。

---

## 7. 局限与下一步

**局限**：

- **n=1/臂**：无臂内方差估计，无法把整局或 per-call 差异统计性地归因于 cap；臂内 p95/p50≈1.8x 的延迟噪声已能淹没所观察的 per-call 差。
- **模型错配**：deepseek-chat 非 reasoning（`reasoning_tokens=0`），输出天然短，**与 ⑤ 收益假设的对象（doubao 等 reasoning 模型）不匹配**；本实验无法验证报告对 doubao 的 ⑤ 预测。
- **cap 未咬合**：512 在两臂均未被触及（峰值 383），实验实际上**没有真正测试 cap 的截断行为**——它只证明了"在不咬合时 cap 无效"。

**下一步**：

- **(a)** 拿到有效 doubao（或其他 reasoning 模型）key，在 reasoning 模型上重测 ⑤——那里 output 体量大，cap 才可能真正咬合并产生杠杆。
- **(b)** 使用**会真正咬合**的低 cap（如 64 / 128），制造可观测的 `length` 截断，才能测出 cap 的真实机械效应（以及它对决策完整性的破坏阈值）。
- **(c)** 每臂跑**多局**以消轨迹方差，使 cap 效应可与对局长度方差分离。
- **(d)** 直接测 **②③** 的提速（关闭 / 优化 O(N²) 意向重轮询、合并第二次 round-trip）——这才是占 99% 成本的大头杠杆。

---

## 8. 附：产物文件路径

- Arm A 数据：`D:/AI_werewolf/NEW/MultiAgent-Werewolf/.claude/worktrees/wt-token-speed/runs/token-cap-exp/A.json`
- Arm B 数据：`D:/AI_werewolf/NEW/MultiAgent-Werewolf/.claude/worktrees/wt-token-speed/runs/token-cap-exp/B.json`
- Arm A 日志：`D:/AI_werewolf/NEW/MultiAgent-Werewolf/.claude/worktrees/wt-token-speed/runs/token-cap-exp/A.log`
- Arm B 日志：`D:/AI_werewolf/NEW/MultiAgent-Werewolf/.claude/worktrees/wt-token-speed/runs/token-cap-exp/B.log`
- 计时器插桩：`D:/AI_werewolf/NEW/MultiAgent-Werewolf/.claude/worktrees/wt-token-speed/src/llm_werewolf/evaluation/game_timer.py`
- 计时运行入口：`D:/AI_werewolf/NEW/MultiAgent-Werewolf/.claude/worktrees/wt-token-speed/_play/timed_game.py`
