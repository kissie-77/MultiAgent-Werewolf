# ③ 无用第二次 round-trip 消除 · 改动报告

> 日期：2026-05-28
> 分支：`fix-second-round-trip` → 合并入 `main`
> 配套：实验数据见 [`第二次round-trip消除-真实对局AB实验报告.md`](第二次round-trip消除-真实对局AB实验报告.md)；瓶颈定性见 [`对局性能瓶颈-影响程度量化报告.md`](对局性能瓶颈-影响程度量化报告.md)。

---

## 1 · 改了什么 / 为什么

**问题（性能报告 ③）**：agentscope `ReActAgent.reply()` 在结构化决策时，仅当模型同一条消息**既吐工具调用又吐文本**才立即结束；doubao 只吐 `generate_response` 工具调用、不吐文本，于是框架注入 `<system-hint>` 再打**第二次 LLM 往返**纯粹为生成文本——而游戏只读结构化 `metadata`，这第二次往返及其 reasoning 全被丢弃。等于给几乎每个决策乘了一个常数 2。

**修复**：在 repo 内子类化 `ReActAgent`，**只覆写 `_reasoning()`**——当"需结构化输出 + 有 tool_use + 无 text"时，给返回消息补一个空 `TextBlock`，使上游 `reply()` 现有的退出条件（`has_content_blocks("text")`）在**首轮即命中并 break**，省掉第二次往返。

**为何选这个落点**：
- 零复制 agentscope 循环逻辑（不像整段覆写 `reply()`），升级自动继承。
- 经 `factory.create_react_agent` 单点接线（全工程唯一构造漏斗，覆盖运行时 + eval）。
- 守卫精确锁定浪费场景：普通文本调用、以及模型本就同时吐文本的调用，都完全走基类原逻辑。
- 正确性安全：游戏读 `Msg.metadata`，从不读这段（现已为空的）返回文本；空 `TextBlock` 只作用于返回消息、**不写入 memory**（经测试证实）。

---

## 2 · 文件清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `src/llm_werewolf/agent_team/fast_react_agent.py` | 新增 | `FastReActAgent`：覆写 `_reasoning()` 补空 TextBlock（核心修复，~35 行）|
| `src/llm_werewolf/agent_team/factory.py` | 改动 | `create_react_agent` 构造 `FastReActAgent` 取代 `ReActAgent`（+import，共 2 行）|
| `tests/agent_team/test_react_single_roundtrip.py` | 新增 | 往返计数 / 对照 / prompt 合法性 3 个测试 |
| `scripts/timed_game.py` | 新增 | 自包含非侵入对局计时器（A/B 度量用，跨两臂同脚本）|
| `tests/instrumentation/test_timed_game.py` | 新增 | 计时器聚合逻辑单测 |
| `docs/第二次round-trip消除-真实对局AB实验报告.md` | 新增 | 真实 doubao A/B 实验报告 |
| `docs/第二次round-trip消除-改动报告.md` | 新增 | 本文件 |
| `runs_timing/*.json` `*.events.jsonl` | 新增 | 实验产物（时序指标 + 对局 transcript）|

**未触及**：意向轮询 ②、`max_tokens`/超时 ⑤、全局串行锁 ① 等其它瓶颈——本改动只隔离 ③。

---

## 3 · 影响面（结合 GitNexus）

遵 `CLAUDE.md` 要求，编辑唯一被修改的符号 `create_react_agent` 前先跑 `gitnexus_impact(direction=upstream)`。

**`gitnexus_impact("create_react_agent", upstream)` → 风险 `CRITICAL`**（直接调用方 2、受影响流程 5、受影响模块 2）：

| 受影响流程 | 文件 | 命中 | 最早断点步 |
|---|---|---|---|
| `run_post_game_pipeline_sync` | `evaluation/post_game/pipeline.py` | 12 | step 2 |
| `bind_role_prompt` | `agent_team/agentscope_agent.py` | 12 | step 1 |
| `run_post_game_pipeline` | `evaluation/post_game/pipeline.py` | 2 | step 1 |
| `run_eval_replay` | `evaluation/post_game/eval_agent.py` | 2 | step 1 |
| `configure_role` | `agent_team/agentscope_agent.py` | 1 | step 1 |

**调用深度（byDepth）**：
- **d=1（直接调用方，会先受影响）**：`AgentScopeWerewolfAgent.configure_role`（运行时建 agent）、`run_eval_replay`（赛后 eval 建 agent）。
- **d=2**：`AgentScopeWerewolfAgent.bind_role_prompt`、`run_llm_replay`。
- **d=3**：`run_post_game_pipeline`。
- **受影响模块**：`Agent_team`（直接）、`Post_game`（直接）。

**判读**：CRITICAL 反映的是**覆盖面广**而非**易坏**。改动是行为保持的子类替换——`FastReActAgent` 继承 `ReActAgent`，构造签名与对外接口完全一致，仅在结构化决策时跳过被丢弃的第二次往返。覆盖面广**正是预期且想要的**：修复必须同时作用于运行时（`configure_role`）与赛后 eval（`run_eval_replay`）两条建 agent 链，而二者都汇于 `create_react_agent` 这一个漏斗，故一处改动即全覆盖。`tests/agent_team` 85 passed 守住了这些下游流程的契约。

**GitNexus 方法学注记（口径透明）**：
- `gitnexus_context("FastReActAgent")` 返回 *Symbol not found*——因为 GitNexus 索引锚定在主树且尚停留在 `6eaf793`（提交后有 *index is stale* 提示），**新符号 / worktree 未提交改动对索引不可见**。
- 同理 `gitnexus_detect_changes` 在主树索引下报 *No changes detected*——它看不到 worktree 里的未提交文件。
- 因此影响分析以**被修改符号 `create_react_agent` 的既有调用图**为准（上表），这对"在该漏斗前插入子类"的改动正是正确口径。合并入 `main` 后建议跑 `npx gitnexus analyze` 重建索引，使 `FastReActAgent` 节点入图。

---

## 4 · 验证

- **确定性单测**（CI 级，无需 API）：
  - 往返计数 **2 → 1**（模型只吐工具调用、不吐文本时）。修复前 RED 为 `assert 2 == 1`。
  - 对照：模型同步吐工具调用 + 文本时仍 1 次（不破坏既有快路径）。
  - prompt 合法性：补的空 TextBlock 不写入 memory，每个 tool_call 仍被 tool_result 应答，末尾无残留纯文本轮。
- 全量 `tests/agent_team` **85 passed**（基线 84 + 新增 1），零回归；计时器单测 2 passed。
- **真实对局 A/B**（doubao 6p，详见实验报告）：
  - 浪费的纯文本往返 **36.4% → 0%**；浪费 reasoning token **38,518 → 0**。
  - 单次 HTTP 中位延迟 **11.57s → 5.93s**。
  - 同等长度对局墙钟收益估 **~⅓–⅖**（原始 4.4× 含局长混淆，不作承重）。
- **对局质量**：独立评审两臂 transcript，结论 `NO_QUALITY_REGRESSION`（发言完整、决策合理、推理连贯、零空发言）。

---

## 5 · 兼容性与后续

- **模型相关**：doubao 必中第二次往返分支，收益确定；deepseek 视其是否顺带吐文本而定，需单独测。
- **agentscope 升级**：若未来上游改动 `:466` 的 break 条件，最坏情况是静默退回"2 次"行为——不崩、不出错。
- **复现注意**：`.env` 仍钉失效旧 ARK key，复现实验需显式覆盖为 API.txt 中可用 key。
- **后续杠杆**（未做）：② 意向 O(N²)、⑤ max_tokens/超时、① 锁→并发；可在本修复基础上叠加。
- **降方差建议**：当前实验单样本，§实验报告的墙钟收益为估算；跑 ≥3 局取均值、或计时器按 tool/no-tool 分桶记录每次 wall，可升级为实测。
