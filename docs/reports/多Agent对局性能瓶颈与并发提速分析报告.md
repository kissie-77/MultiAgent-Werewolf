# 多 Agent 对局性能瓶颈与并发提速分析报告

> 日期：2026-05-26
> 范围：回答两个问题 ——（Q1）为什么单局多 Agent 对局要跑几十分钟；（Q2）能否并行跑多对局、LLM API 是否允许。
> 并对由此提出的提速方案做对抗式拷打（red-team）+ GitNexus 影响范围评估，给出加固后的路线图。

## 方法与可信度说明

本报告结论由三条相互独立的证据线交叉得出，以提高可信度：

1. **直接读码核实**：人工通读核心调用链（serial_calls / information_hub / agentscope_agent / engine / runner / presets / config）。
2. **多 Agent 对抗工作流**：两轮 fan-out 工作流（各 12 个子 Agent，~60–77 万 tokens），分维度调查 + 综合 + **对抗式验证**关键论断（confirmed / partial / refuted）。
3. **GitNexus 影响分析**：对计划要改的符号跑上游爆炸半径（blast radius）。

下文凡标注 file:line 的均为已核实证据；凡标注 ✅/⚠️/❌ 的均为对抗验证后的最终判定。

---

## 摘要（TL;DR）

| 问题                               | 结论                                                                                                                                                                                                                             |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Q1 为什么慢**                    | 三件事叠乘：① 一把**进程级全局锁**把所有 LLM 调用串成单线（有效并发 = 1）；② **默认开启**的投票意向轮询是 **O(N²)**，占一局 ~70–85% 调用；③ 每次逻辑调用还有**最多 ~9–12 次物理请求**的重试叠乘。数百次请求全部排队 → 几十分钟。 |
| **Q2a 进程内并行多局**             | ❌ 不行。全局锁所有对局共享（并发仍 = 1）；且进程内并行会触发其它全局态问题。                                                                                                                                                    |
| **Q2b 进程级并行（每局一个进程）** | ✅ 可行且近线性加速，是推荐路径。但需修复"共享技能卡目录"等隐患，并加跨进程限流。                                                                                                                                                |
| **Q2 API 是否允许并发**            | ✅ 允许。DeepSeek 基本不设硬性速率上限；火山方舟/Doubao 有按档位 RPM/TPM 限制。单机全局并发 16–32 安全，保留 429 退避。                                                                                                          |
| **对原提速方案的总评**             | 诊断正确，但**排序错了**（最高 ROI 是关投票意向，不是换锁），且**漏了两个"现在就存在"的 critical bug**。需先修 bug + 先测量，再谈并发重构。                                                                                      |

---

## 第一部分 · Q1：为什么单局要几十分钟

### 瓶颈 ①（决定性）全局串行锁 —— 有效并发 = 1

`serial_calls.py:18` 定义了**模块级** `_AGENT_CALL_LOCK = asyncio.Lock()`，所有模型调用都经 `run_serial_agent_call` 持锁串行（`serial_calls.py:31-34`）。所有调用路径都汇到这里：

- `agentscope_agent.py:220`（文本路径 `_call_agentscope_agent`）
- `agentscope_agent.py:278`（结构化路径 `get_structured_response`）
- `eval_agent.py:150`（赛后复盘 `run_eval_replay`）

全代码**没有任何绕过它的 AsyncOpenAI/httpx 旁路**（已 grep 核实，`archive/LOCAL_ONLY-serial-agent-calls.md` 也说明这是有意为之的本地节流）。

后果：引擎里 `voting_phase.py:112` 用 `asyncio.gather` 并发投票，**看着是并行，实际全在锁后排队**。单局墙钟时间 = 每次调用延迟之和，零重叠。

> 注意：该锁是**单进程单事件循环**内的串行，只约束实时 LLM 对局；离线 `EvaluationRunner` 用的是 `DemoAgent`（不调真实模型），不走这把锁。

### 瓶颈 ②（最大调用量）投票意向 O(N²)，默认开启

`game_config.py:46-47` 中 `track_vote_intentions` **默认 `True`**，6 人配置未覆盖。代价在 `information_hub.py` 的 `_collect_vote_intentions`：每次白天讨论里，**每个发言者说完，所有存活玩家各发一次私有 LLM 调用更新"投票意向"**，讨论开始前还要再来一轮全员。

- 初始全员意向：`information_hub.py:315`
- 每次发言后全员意向：`information_hub.py:403`（在 `for speaker in speakers` 循环内）
- per-listener 循环：`information_hub.py:219`

**6 人首日白天真实账（已验证）：**

| 项目                                   | 调用数 (N=6) | 占比     |
| -------------------------------------- | ------------ | -------- |
| 玩家发言                               | 6            |          |
| 投票意向（初始 6 + 每次发言后 6×6=36） | **42**       | **~85%** |
| **白天讨论小计**                       | **48**       |          |

公式：每个白天圆桌 = N + N×N = **N² + N** 次意向调用 + N 次发言。这 42 次**纯属分析/复盘用，无任何游戏逻辑读取**。

### 瓶颈 ③ 重试扇出 —— 物理请求 ≫ 逻辑调用

每次逻辑调用套多层重试：

- 传输层 `for attempt in range(3)`（`agentscope_agent.py:218` / `:276`）
- 结构化校验 `invoke_structured(retries=...)`
- 发言层 `bridge.py` 的 `schema_retries=3` + 文本兜底
- 每次模型调用本身是一次 ReActAgent 运行，`max_iters` 默认 **10**（已验证）

**一次发言最坏要打 ~9–12 次真实 API 请求**，且每次重试仍排全局锁队。退避（`2**attempt`，即 1s/2s）只在 429 时触发（`agentscope_agent.py:233-241`），非 429 错误立即 break。

### 综合账与模型因素

- 一局 3–4 个昼夜：确定性逻辑调用 ~40–45 次；投票意向把它抬到**数百次逻辑调用**；再 ×重试 → **数百到上千次物理请求，全部串行**。
- 模型 `deepseek-v4-flash`（`configs/llm-6p-deepseek.yaml:6`），`max_tokens=2048` 对**所有调用硬编码**（`factory.py:85`），reasoning 类延迟本就不低。
- **隐患**：模型客户端**没设单次超时**（`factory.py:85-95`），一次卡死的请求会**攥着全局锁拖死整局**（仅 eval 路径 `runner.py:96` 有 30s 整局兜底）。

### 瓶颈排序

1. 全局串行锁（并发=1）—— 结构性天花板
2. 投票意向 O(N²)（默认开）—— 最大调用量来源
3. 重试扇出（~9–12×）—— 放大每次调用
4. 每轮确定性发言+投票（~N 各）
5. 无单次超时 —— 尾延迟/可靠性

---

## 第二部分 · Q2：并发多对局可行性 + API 政策

### (a) 进程内并行（`asyncio.gather` 多局）—— 不行

引擎本身按实例可重入（状态在 `self` 上），但有进程级全局态拦路：

1. **全局锁**（`serial_calls.py:18`）所有对局共享 → K 局调用仍串成一队，**加速 ≈ 1×**。
2. **嵌套 `asyncio.run`**：赛后管线 `run_post_game_pipeline_sync`（`pipeline.py:136`）在已运行的事件循环里再调 `asyncio.run` → `RuntimeError`（详见"现存 Bug"）。
3. **全局 RNG**：进程内并行时 `random.seed` 不线程安全（顺序跑时无此问题，见验证 ❌ 一条）。

### (b) 进程级并行（每局一个进程）—— 推荐，近线性加速

开 N 个 OS 进程各跑一次对局，每进程重新 import 一套全新全局，绕开上述全局态。但**必须**配套：

- **唯一输出目录**：`interface/cli.py:93` 用秒级时间戳 `runs/%Y%m%d-%H%M%S`，同秒启动会撞目录 → 改成绝对唯一 `--run-dir`（uuid）。
- **修复共享技能卡目录污染**（见"现存 Bug ②"，否则连顺序跑都会串味）。
- **跨进程限流**：见下。
- 机制选 **subprocess CLI**，不要 `multiprocessing.spawn`（Windows 上有 import 副作用 + 引擎/agent 不可 pickle）。

> 现状：`evaluation/runner.py:51-56` 的批量 runner 是**严格顺序**，且用 `DemoAgent`（不调真实 LLM）。**目前没有任何并发跑真实对局的机制**，需新写启动器。

### (c) LLM API 是否允许并发 —— 允许

- **DeepSeek**：不设硬性 RPM/TPM 限制，高负载倾向保持连接/放慢响应而非拒绝；并发调用允许。（联网查到的口径还提到 `deepseek-v4-flash` 容许较高并发上限——**此具体数字以你 DeepSeek 控制台实时配额为准**，结论"允许并发"不依赖该数字。）
- **火山方舟 / Doubao**：有**按账号 + 按基础模型**的 RPM/TPM 上限（默认量级 ~万级 RPM / 百万级 TPM），超限返回 429。
- **建议并发度**：单局内天然上限 = 玩家数（6–12）；跨多局单机**全局并发 16–32** 对 DeepSeek 余量很大、也稳在 Doubao 限额内。务必保留 429 指数退避（`agentscope_agent.py:233-241` 已有）。
- ⚠️ **跨进程限流缺口**：进程级并行时，K 进程 × 每进程 ~N 并发 = **K×N 峰值并发且无共享限流器**，在计费后端会触发 429 风暴。需硬 cap K 或加共享令牌桶。

---

## 第三部分 · 原始提速方案（被拷打对象）

- **P0a** — 把 `serial_calls.py` 的全局 `Lock` 换成 per-engine 有界 `Semaphore`（≈玩家数），只串行同一 agent，放开不同 agent 并发。原称"最大单点提速"。
- **P0b** — 干掉 O(N²) 投票意向：`track_vote_intentions=False`，和/或只收最终意向，和/或 `asyncio.gather` 并行 per-listener 循环。原称"纯分析、无影响"。
- **P1a** — 给模型客户端加单次超时 + 小 `max_retries`。
- **P1b** — 进程级批量启动器，唯一 run 目录，修 `cli.py:93` 时间戳撞目录。
- **P2** — 进程内多局：per-game `random.Random(seed)`；赛后管线改可 await。

---

## 第四部分 · 红队拷打结论（含对抗验证判定）

| #   | 严重度      | 打哪一项 | 指控（已核实证据）                                                                                                                                                                                                                                                                                   | 判定        |
| --- | ----------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| 1   | 🔴 critical | baseline | **赛后管线现在就在崩**：`pipeline.py:136` 在运行中的事件循环里又调 `asyncio.run` → `RuntimeError`；调用点 `runner.py:141` 在 try/except 之外，协程自己的 try 接不住。eval 默认开意向 + DemoAgent 产 records → **每次 eval 都触发**，中断整批。                                                       | ✅ 确认     |
| 2   | 🔴 critical | P1b/P2   | **技能卡写进包内共享目录**：赛后把 `{skill_id}.md` 写到 `agent_team/skills/<role>/`（无 run id，`skill_extractor.py:242-248`），运行时又被 `@lru_cache` 读回拼 system prompt（`skill_loader.py:13-46`）。→ 任意多局（**连顺序跑**）互相覆盖、污染他局 prompt；`skills/` 已提交几百个生成卡片进 git。 | ✅ 确认     |
| 3   | 🟠 high     | P0a      | **"最大提速"被夸大**：发言天生串行（`hub.broadcast` 把发言写进所有人记忆供后续读取，`information_hub.py:350/364/380`）；夜晚有硬依赖（女巫必须看到狼刀结果 `werewolf_target`，`night_phase.py:206/267-273`）。P0a 只能并行投票 + 投票意向扇出。                                                      | ✅ 确认     |
| 4   | 🟠 high     | P1a      | **现状加超时有害**：超时落进 `except Exception` 的 break 分支（非 429）→ 0 重试 → 直接随机/套话兜底（`agentscope_agent.py:237-242`，兜底是 `random.choice` 投票/假发言）。一张假票可能决定胜负。SDK `max_retries` 会与 app 3 层 × ReActAgent `max_iters=10` 相乘。                                   | ✅ 确认     |
| 5   | 🟠 high     | P1b      | **无跨进程限流**：K×N×重试 峰值并发无共享限流器 → Doubao 429 风暴；相对 run 目录受 cwd 影响。                                                                                                                                                                                                        | ✅ 合理     |
| 6   | 🟠 high     | P0b      | "纯分析、无影响"**不准确**。                                                                                                                                                                                                                                                                         | ⚠️ 部分成立 |
| 7   | 🟠 high     | P2       | "模块级 random 太多，per-game RNG 没用"。                                                                                                                                                                                                                                                            | ❌ 被推翻   |
| 8   | 🟡 medium   | 全局     | **全程零 profiling**：`max_tokens=2048` 对所有调用硬编码（连选座/是否 1-3 token 的也是）；单局瓶颈是串行、生成受限的发言链，并发缩不短它。                                                                                                                                                           | ✅ 确认     |

### 两条需诚实纠正的（验证阶段反过来打了评审）

- **#6（P0b）⚠️ 部分成立**：关掉投票意向**不会**"删掉整条管线"。真实对局走 `cli.py:94 → finalize_run.py:52 → run_post_game_pipeline`，**无条件执行且优雅降级**（缺记录回退 events.jsonl，空 swing 报告照出）。真实影响是：(a) **只有离线 `EvaluationRunner` 会跳过**赛后步骤（`runner.py:138` 的 `if records:` 闸门）；(b) **persuasion / swing / intention 三类分析在所有路径变空**；其余（log views、role-skill、prompt proposals、benefit、LLM replay）照常。
    - 评审有一条对：**"只收最终意向"这个子选项要丢掉**——swing 是相邻 before/after 差分（`vote_intention.py:125`），只留最终值会把所有 swing **结构性归零**，产出"看似有数据其实全 0"的废报告。要降量应减少听众/发言人数。
- **#7（P2 RNG）❌ 被推翻**：评审看错代码。`runner.py:73` 是 `random.seed(seed)`（给**全局单例**播种），不是 `random.Random(seed)`（孤立实例）。`base.py:134` 洗牌、`night_phase.py:205` 平票 `random.choice` 正是取自该全局单例 → **顺序跑的复现性现在是好的**。per-game RNG **仅在进程内并行时才需要**。

---

## 第五部分 · 两个"现在就存在"的 Bug（与提速无关，建议最先修）

1. **eval 链路 100% 崩**（指控 #1，✅）。修法：删掉 `pipeline.py:130-136` 同步包装里的嵌套 `asyncio.run`，因 `run_scenario` 本就是 async，直接 `await run_post_game_pipeline(...)`；调用点包 try/except（符合该文件"单局失败不拖累整批"契约）。加回归测试：开 `track_vote_intentions=True` 跑一局，断言赛后产物存在。
2. **技能卡污染源码树**（指控 #2，✅）。修法：写到 run 作用域目录（`skill_extractor.py:257` 已有 `agent_skills_root` 参数，传 `ctx.run_dir/'agent_skills'`），批量/eval 时关掉写库，晋升共享库改成显式串行步；丢掉/失效 `list_role_skill_files` 的 `lru_cache`；**清理已误入 git 的 `src/llm_werewolf/agent_team/skills/` 卡片**。

---

## 第六部分 · GitNexus 影响范围（编辑目标 → 上游爆炸半径）

| 编辑目标                               | 对应方案项   | 风险        | 直接调用者（d=1，改签名会断）                                                                                                    | 含义                           |
| -------------------------------------- | ------------ | ----------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `run_serial_agent_call`                | P0a 换锁     | 🔴 CRITICAL | `_call_agentscope_agent`、`get_structured_response`、`run_eval_replay`                                                           | 6 符号 / 5 执行流 / 2 模块     |
| `create_react_agent`                   | P1a 超时     | 🔴 CRITICAL | `configure_role`、`run_eval_replay`                                                                                              | 影响每次 agent 创建            |
| `run_roundtable`（facade）             | P0a/P0b      | 🟡 MEDIUM   | `run_day_phase`、`_run_werewolf_discussion`、`_conduct_campaign_speeches`、`_conduct_pk_speeches`、`_conduct_voting_pk_speeches` | 被 5 个阶段共用                |
| `_collect_vote_intentions`             | P0b          | 🟢 LOW      | 仅 `run_roundtable`                                                                                                              | 完全内聚                       |
| `create_game_config_from_player_count` | P0b 配置默认 | 🟢 LOW      | （图中 0，索引可能略旧）                                                                                                         | 结构安全；行为上影响所有预设局 |

### 关键交叉印证

- 两个 CRITICAL 目标（`run_serial_agent_call`、`create_react_agent`）的上游**都扇入 `run_eval_replay` → 赛后管线**。红队又**独立**在那条管线挖出 live crash + 共享目录污染 → 赛后管线**既高爆炸半径、又确有 bug**。改锁/工厂后**必须同时回归实时局和赛后复盘**。
- `_collect_vote_intentions` 为 LOW（仅 `run_roundtable` 调用）→ 对应"唯一能安全并行的就是这个跨-agent 扇出"。
- `run_roundtable` 被 5 阶段共用（含狼人夜聊）→ 对应"发言到处串行、夜晚必须拉黑名单"。

> ⚠️ 两个 CRITICAL 改动须**保持调用契约**：P0a 改 `serial_calls.py` 时保持 `run_serial_agent_call` 签名不变（内部换 Semaphore）；P1a 给 `create_react_agent` 加超时须用**带默认值的可选参数**，否则两个直接调用点全断。
> 📌 索引新鲜度：`create_game_config_from_player_count` 上游显示 0，但 `bootstrap.py:78` 明确调它（边未被索引捕获，可能因 git 中已改文件导致索引略旧）。精确依赖图建议先 `npx gitnexus analyze` 重建。

---

## 第七部分 · 加固后的方案（重排序）

| 优先级 | 动作                                                                                                                                                                                                                                     | 相对原方案改了什么                        | 风险                       | 文件                                                  |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- | -------------------------- | ----------------------------------------------------- |
| **P0** | **先测量**：给一局真实 6p 打点（每次调用墙钟 + prompt/completion tokens + DeepSeek cache 命中），按阶段分桶，用数据决定"延迟受限 vs 生成受限"再动锁。                                                                                    | 新增（原方案纯静态分析）                  | 低                         | `agentscope_agent.py:205-260`、`factory.py:89-95`     |
| **P0** | **修 eval live crash**（Bug ①）                                                                                                                                                                                                          | 从 P2 提到 P0，定性为现存崩溃             | 低、高价值                 | `pipeline.py:130-136`、`runner.py:135-145`            |
| **P0** | **修技能卡共享目录**（Bug ②）                                                                                                                                                                                                            | 全新                                      | 中                         | `skill_extractor.py:221-276`、`skill_loader.py:9-51`  |
| **P0** | **`track_vote_intentions` 改显式开关**：默认值只改 `game_config.py:46` **一处**（**不是 `presets.py:114`**——那行不传此字段），快速/批量配置显式传 `False` 并打 WARN。最高 ROI 提速（砍 ~70-85% 调用）。                                  | 纠正"纯分析"措辞 + 纠正错误行号           | 全局翻默认=中；按配置关=低 | `game_config.py:46-47`、`base.py:85-89`               |
| **P1** | **收敛重试**：SDK `max_retries=0`（别叠加）；`schema_retries` 降到 1-2；给 ReActAgent 传小 `max_iters`(3-4)。目标 ≤6 物理调用/决策。                                                                                                     | 推翻"加 SDK max_retries"                  | 低-中                      | `factory.py:89-105`、`bridge.py:746-766`              |
| **P1** | **加宽松超时**（60-90s 起，随 max_tokens 放大）via `client_kwargs`；`APITimeoutError` 加进可重试分支或让兜底可观测；**统计 fallback 率**。须在 P0a 之后。                                                                                | 纠正"超时会被静默兜底"                    | 中（太短=毒化对局）        | `factory.py:85-95`、`agentscope_agent.py:233-245`     |
| **P1** | **生成侧便宜的赢**：决策类调用（选座/是否/意向）用小 `max_tokens`(~16-32)，发言才留 2048；暴露 `max_speakers/max_rounds`；验证 prefix-cache 稳定性。                                                                                     | 全新                                      | 低                         | `factory.py:85`、`day_phase.py:99-131`                |
| **P2** | **锁→并发**（测量证明锁确是瓶颈后）：per-agent `Lock`(按 player_id) + per-engine 有界 `Semaphore`；**只对 `_collect_vote_intentions` 跨-agent 扇出**用 `asyncio.gather`；**黑名单夜晚阶段 + 发言循环**；保留 `AGENT_SERIAL_DELAY` 节流。 | 收窄范围 + per-agent 锁 + 黑名单          | 高                         | `serial_calls.py:18-38`、`information_hub.py:219-264` |
| **P2** | **per-game 确定性**（仅为进程内并行）：注入 `random.Random` 贯穿 `setup_game`/`base.py:134`/`night_phase.py:205` 所有 choice/shuffle，别只移动 seed。                                                                                    | 纠正：顺序跑现已可复现                    | 中                         | `runner.py:73`、`base.py:134`                         |
| **P2** | **批量启动器**：subprocess CLI（非 `multiprocessing.spawn`）；绝对唯一 `--run-dir`(uuid)；**跨进程限流**（硬 cap K 或共享令牌桶）；`--max-cost` 守卫；批量默认 `skip_llm`。                                                              | 纠正 Windows spawn 陷阱 + 加限流/成本守卫 | 中                         | `cli.py:93`、`eval_cli.py`、`runner.py`               |

### 推荐起步顺序

1. **先修两个现存 Bug**（eval crash + 技能卡目录）—— 零并发风险，且让 baseline 测得准。
2. **把投票意向做成显式开关并在快速配置里关掉** —— 立刻让单局/批量都快起来。
3. **加测量打点** —— 用真实数据决定后面是否值得碰锁。
4. 之后再按 P1 / P2 推进；**每改一个符号前先跑 `gitnexus_impact` 复核**（CLAUDE.md 要求）。

---

## 附录

### A. 关键文件索引

| 主题                     | 文件:行                                                                                                    |
| ------------------------ | ---------------------------------------------------------------------------------------------------------- |
| 全局串行锁               | `src/llm_werewolf/agent_team/serial_calls.py:18,29-38`                                                     |
| 锁的三个调用点           | `agentscope_agent.py:220,278`、`evaluation/post_game/eval_agent.py:150`                                    |
| 投票意向 O(N²)           | `agent_team/information_hub.py:219,315,403`                                                                |
| 意向开关默认值           | `game_runtime/config/game_config.py:46-47`；`game_runtime/engine/base.py:85-97`                            |
| 重试栈                   | `agentscope_agent.py:218,276,233-241`；`bridge.py:746-766`                                                 |
| 模型/超时构造            | `agent_team/factory.py:85-105`；`configs/llm-6p-deepseek.yaml:6`                                           |
| 赛后管线嵌套 asyncio.run | `evaluation/post_game/pipeline.py:130-136`；`evaluation/runner.py:138-145`                                 |
| 技能卡写入/读取          | `evaluation/post_game/skill_extractor.py:221-276`；`agent_team/skill_loader.py:9-51`                       |
| 顺序批量 runner          | `evaluation/runner.py:51-56,73,171-176`                                                                    |
| 全局 RNG 使用点          | `evaluation/runner.py:73`；`game_runtime/engine/base.py:133-134`；`game_runtime/engine/night_phase.py:205` |
| 发言串行（MsgHub）       | `agent_team/information_hub.py:350,364,380`                                                                |
| 夜晚硬依赖（女巫看狼刀） | `game_runtime/engine/night_phase.py:206,267-273`；`game_runtime/night_scheduler.py:72-77,133`              |

### B. 🔐 安全提醒（重要）

仓库根目录 `API.txt` **提交了真实的 DeepSeek 与 Doubao/Ark API 密钥**到 git（已进提交历史）。建议：**立即吊销并重新生成**这两个 key，将 `API.txt` 加入 `.gitignore`，密钥只放 `.env`（YAML 用 `api_key_env` 引用变量名）。本报告未复制任何密钥明文。

### C. 复现/验证命令

```bash
# 重建 GitNexus 索引（影响图若过旧）
npx gitnexus analyze

# 单局测量（建议先加打点）
uv run llm-werewolf --config configs/llm-6p-deepseek.yaml
```
