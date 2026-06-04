# Agent Team 设计

> **模块**：agent_team
> **状态**：active
> **最后更新**：2026-06-02
> **关联代码**：`src/llm_werewolf/agent_team/`

## 1. 目标

提供多 Agent 执行层：将游戏引擎的阶段指令转化为 Agent 的发言和决策，管理 Agent 的记忆、通信、信息隔离和 Skill 使用。

## 2. 范围

### 做

- 接入 AgentScope 框架，驱动 LLM Agent
- 管理多 Agent 通信与信息隔离（PUBLIC / WOLF_TEAM / PRIVATE 通道）
- 管理 Agent 记忆（工作记忆、情景记忆、语义记忆、程序记忆）
- 读取和使用赛后生成的 Skill 文件
- 解析 LLM 输出为结构化决策（发言、投票、技能选择）
- 提供兜底回复机制，确保游戏流程不因 LLM 失败而中断

### 不做

- 不定义游戏规则（归 `game_runtime`）
- 不定义 Prompt 策略（归 `strategy`）
- 不生成 Skill（归 `evaluation/post_game/skill_generation`）
- 不直接调用游戏引擎（通过 PhaseInteraction 接口通信）

## 3. 核心架构

```
PhaseInteraction（游戏引擎接口）
    → Bridge（统一适配层）
    → Agent（AgentScopeWerewolfAgent / DemoAgent）
    → RuntimeMemoryManager（记忆管理；别名 MemoryManager）
    → SkillLoader（Skill 读取）
    → MessageRouter（消息路由）
    → InformationHub（信息中枢）
```

## 4. 关键概念

| 概念 | 说明 |
|------|------|
| AgentScopeWerewolfAgent | 基于 AgentScope 的狼人杀 Agent 实现 |
| PromptAgentMixin | Prompt 注入 Mixin，提供角色提示词和策略 |
| WerewolfAdapterBridge | 统一适配层：解析 LLM 输出、驱动 Agent 调用、转换决策 |
| MessageRouter | 消息路由器：根据通道和游戏状态决定谁能听到什么 |
| InformationHub | 信息中枢：管理 Agent 之间的消息传递 |
| RuntimeMemoryManager | 运行时记忆管理器：协调四层记忆 |
| WorkingMemory | 工作记忆：短期上下文，按轮次压缩 |
| EpisodicMemory | 情景记忆：关键事件记录 |
| SemanticMemory | 语义记忆：长期知识卡片，按角色分类 |
| ProceduralMemory | 程序记忆：角色策略计划和 Skill 描述 |
| SkillLoader | Skill 加载器：读取赛后生成的 Skill 文件 |

## 5. 记忆系统

四层记忆（Working / Episodic / Semantic / Procedural）由 `RuntimeMemoryManager` 统一调度；语义记忆以 Skill MD 为主，ReMe 已下线；与 Coach 分层详见 **[memory/DESIGN.md](./memory/DESIGN.md)**。

简要生命周期：

```text
on_game_start → 注入 Skill + 程序记忆
on_round_end  → 压缩工作记忆
on_game_end   → 更新 skill 权重 + 可选语义候选提炼
```

## 6. 通信系统

### 6.1 信息隔离

Agent 之间通过 MessageRouter 控制信息可见性：

| 通道 | 可见范围 | 示例 |
|------|----------|------|
| PUBLIC | 所有存活玩家 | 白天发言、死亡公告 |
| WOLF_TEAM | 仅狼人 | 狼人夜间讨论 |
| PRIVATE | 仅特定角色 | 预言家查验结果、女巫用药 |

Agent 可见上下文必须只包含局内信息。运行身份、调试信息和后端实现细节不能进入 Agent 决策上下文，包括“人类玩家 / AI / model / backend / demo”等文本。人机混战中的真实参与者统一称为“人类玩家”，该身份只用于 CLI/UI 输入输出和座位绑定，不作为局内推理信息。

### 6.2 消息路由流程

```
Agent 产出发言（public_speech / private_thought）
    → Bridge 解析
    → MessageRouter 根据通道解析受众
    → InformationHub 投递给目标玩家
    → 记录为 Event（带 visible_to 字段）
```

## 7. 结构化决策

Bridge 层负责将 LLM 输出解析为结构化决策：

| 决策类型 | 说明 | 格式 |
|----------|------|------|
| SpeechDecision | 圆桌发言 | public_speech（≥15字）+ private_thought |
| SeatChoiceDecision | 选座（刀人/守人/查验） | [[座位号]] |
| VoteIntentionDecision | 投票意向 | target + reason |
| YesNoDecision | 是否用药 | [[1]] 或 [[0]] |
| WitchNightDecision | 女巫夜间决策 | 是否用药 + 目标 |
| MindStateDecision | 信念矩阵更新 | B1/B2/W 面板 |

## 8. Skill 生命周期

```
evaluation/post_game/coach 复盘
    → evaluation 写入 agent_team/skills/<role>/<skill_version>/
    → agent_team/skill_loader 读取
    → memory 注入描述或上下文
    → Agent 使用 skill 决策
```

关键规则：
- `evaluation` 可以写入 `agent_team/skills`
- `agent_team` 只读取 `agent_team/skills`
- Skill 文件按 `skills/<role>/<version>/` 存放（guard/、prophet/、villager/、wolf/ 等）

## 9. 兜底回复机制

当 LLM 调用失败时，Agent 通过 `_generate_fallback_response` 生成兜底回复：

- 选座阶段：从 prompt 中提取座位号或使用当前玩家座位号
- 狼队私聊：使用协调话术模板
- 白天讨论：按角色生成有博弈性的推理发言
- 最终兜底：返回符合长度要求的默认发言（≥15字）

### 9.1 AgentScope 结构化调用中断处理

AgentScope 结构化调用必须区分“模型没有返回合法结构化结果”和“调用被取消或超时造成的框架固定中断文本”。

当调用链出现类似 `I noticed that you have interrupted me. What can I do for you?` 的中断文本时，该文本不是玩家发言，也不是合法决策。它不应进入后续玩家可见记忆，否则会污染下一轮结构化调用。

处理原则：

- 识别 interrupted 文本和 `CancelledError`。
- 清理 memory 中由中断调用残留的 interrupted / tool_result 内容。
- 对结构化调用执行有限重试。
- 重试仍失败时，再走原有兜底决策逻辑。

### 9.2 Agent 人数边界

AgentScope Agent 不假设固定 12 人局。运行时由入口配置绑定本局 `player_count`，兜底选座逻辑按当前局人数限制候选范围。

人数边界：

- 支持 6-20 人。
- 优先从当前 prompt 候选中推断可选座位。
- 无法推断时使用绑定的 `player_count`。
- 不把固定人数写死在 Agent 决策逻辑中。

### 9.3 Fallback 可观测性

`agent_team` **不** import `observability`。interface 在对局期间挂载 `RunObservabilityLogHandler`，采集 bridge 等路径的 `using fallback` warning → `<run_dir>/provider_events.jsonl`（`kind=agent_fallback`），由规则 `agent_fallback_per_run`（默认 >5/局）告警。静默 fallback 路径的完整覆盖见 [observability/ROADMAP.md](../observability/ROADMAP.md) Phase 2。

## 10. 接口与扩展点

| 入口 | 类型 | 说明 |
|------|------|------|
| `create_agent(player, config)` | 工厂函数 | 创建 Agent 实例 |
| `create_react_agent(player, config)` | 工厂函数 | 创建 ReAct Agent |
| `configure_agents_for_players(players, config)` | 批量配置 | 为所有玩家配置 Agent |
| `WerewolfAdapterBridge` | 适配层 | 解析 LLM 输出、驱动 Agent |
| `RuntimeMemoryManager` | 记忆管理 | 协调四层记忆生命周期 |

## 11. 依赖与边界

遵循工程结构整理方案：

- `agent_team → game_runtime.types`、`game_runtime.config`、`game_runtime.prompts`
- `agent_team → strategy`（决策 schema、Prompt、信念状态）
- `agent_team` 不依赖 `evaluation`（只读 Skill 产物，不调用 Coach）
- `agent_team` 不依赖 `observability`（降级信号经 logging 由 interface 采集）
- `evaluation` 可写入 `agent_team/skills`

## 12. 相关文档

- 进度：[ROADMAP.md](./ROADMAP.md)
- 记忆子模块：[memory/DESIGN.md](./memory/DESIGN.md) · [memory/ROADMAP.md](./memory/ROADMAP.md)
- 工程结构方案：[../architecture/工程结构整理方案.md](../architecture/工程结构整理方案.md)
- 告警与 fallback 监控：[../observability/DESIGN.md](../observability/DESIGN.md)
