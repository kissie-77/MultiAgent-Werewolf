# Agent Team 设计

> **模块**：agent_team
> **状态**：active
> **最后更新**：2026-05-24
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
    → MemoryManager（记忆管理）
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

### 5.1 四层记忆架构

```
WorkingMemory（工作记忆）
    - 短期上下文，保留最近 N 轮发言
    - 按轮次自动压缩
    - 包含信念矩阵快照（B1/B2/W 面板）

EpisodicMemory（情景记忆）
    - 关键事件记录（死亡、查验、投票结果）
    - 用于复盘和长期推理

SemanticMemory（语义记忆）
    - 长期知识卡片，按角色分类
    - 赛后通过 Coach 提取和更新
    - 支持相似度检索

ProceduralMemory（程序记忆）
    - 角色策略计划（default / complicated）
    - Skill 描述和权重
    - 游戏开始时注入
```

### 5.2 记忆生命周期

```
游戏开始 → on_game_start()
    → 注入角色 Skill
    → 注入程序记忆（策略计划）
    → 初始化工作记忆

每轮结束 → on_round_end()
    → 压缩工作记忆

游戏结束 → on_game_end()
    → 更新语义记忆
    → 提取语义候选
    → 清理过期卡片
```

## 6. 通信系统

### 6.1 信息隔离

Agent 之间通过 MessageRouter 控制信息可见性：

| 通道 | 可见范围 | 示例 |
|------|----------|------|
| PUBLIC | 所有存活玩家 | 白天发言、死亡公告 |
| WOLF_TEAM | 仅狼人 | 狼人夜间讨论 |
| PRIVATE | 仅特定角色 | 预言家查验结果、女巫用药 |

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
    → evaluation 写入 agent_team/skills/
    → agent_team/skill_loader 读取
    → memory 注入描述或上下文
    → Agent 使用 skill 决策
```

关键规则：
- `evaluation` 可以写入 `agent_team/skills`
- `agent_team` 只读取 `agent_team/skills`
- Skill 文件按角色分类存放（guard/、prophet/、villager/、wolf/）

## 9. 兜底回复机制

当 LLM 调用失败时，Agent 通过 `_generate_fallback_response` 生成兜底回复：

- 选座阶段：从 prompt 中提取座位号或使用当前玩家座位号
- 狼队私聊：使用协调话术模板
- 白天讨论：按角色生成有博弈性的推理发言
- 最终兜底：返回符合长度要求的默认发言（≥15字）

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
- `evaluation` 可写入 `agent_team/skills`

## 12. 相关文档

- 进度：[ROADMAP.md](./ROADMAP.md)
- 记忆板块开发记录：[../memory/](../memory/)
- 工程结构方案：[../architecture/工程结构整理方案.md](../architecture/工程结构整理方案.md)
