# Strategy 设计

> **模块**：strategy
> **状态**：active
> **最后更新**：2026-05-24
> **关联代码**：`src/llm_werewolf/strategy/`

## 1. 目标

提供统一的策略语言和决策契约：Prompt 版本化管理、结构化决策 schema、信念矩阵、投票意向模型。作为 Agent 和引擎之间的策略层，不依赖任何业务模块。

## 2. 范围

### 做

- 管理角色 Prompt（外置 YAML/Markdown 文件，版本化）
- 定义结构化决策模型（Pydantic BaseModel）
- 管理信念矩阵（B1/B2/狼队 W 面板）
- 定义投票意向追踪与快照
- 定义阶段输出契约（白天/黑夜/圆桌）
- 提供 Prompt 变量注册与加载机制

### 不做

- 不执行 Agent 决策（归 `agent_team`）
- 不管理游戏状态（归 `game_runtime`）
- 不生成赛后 Skill（归 `evaluation`）
- 不直接调用 LLM（归 `agent_team`）

## 3. Prompt 系统

### 3.1 版本化外置文件

Prompt 文件按版本组织在 `prompts/v2/` 目录：

```
prompts/v2/
├── manifest.yaml          # 版本清单
├── variables.yaml         # 变量元数据（variable_id → file + format_keys）
├── text/
│   └── agent_base.md      # 基础 Agent 模板
└── roles/
    ├── villager.yaml      # 平民角色卡片
    ├── prophet.yaml       # 预言家角色卡片
    ├── witch.yaml         # 女巫角色卡片
    ├── wolf.yaml          # 狼人角色卡片
    ├── wolf_king.yaml     # 狼王角色卡片
    ├── guard.yaml         # 守卫角色卡片
    └── hunter.yaml        # 猎人角色卡片
```

### 3.2 PromptRegistry

`PromptRegistry` 负责加载和管理 Prompt 变量：

- 从 `manifest.yaml` 读取版本号
- 从 `variables.yaml` 加载变量元数据
- 按 variable_id 读取文本或角色卡片
- 支持 format_keys 动态注入变量（如 {number}、{role_name}）

### 3.3 角色卡片结构

每个角色卡片（YAML）包含：

- `role_instruction`：角色任务说明
- `suggestion`：策略重点
- `plan`：本局个人计划（default / complicated）

### 3.4 提示词注入流程

```
PromptRegistry 加载 v2 版本
    → RolePrompts 从 registry 注入角色卡片
    → PromptAgentMixin 构建完整 prompt
    → Agent 接收 prompt 生成决策
```

## 4. 结构化决策模型

所有决策模型基于 Pydantic BaseModel，用于 AgentScope ReActAgent 的结构化输出：

| 模型 | 说明 | 关键字段 |
|------|------|----------|
| SpeechDecision | 圆桌发言 | public_speech（≥15字）、private_thought |
| SeatChoiceDecision | 选座（刀人/守人/查验） | seat（0表示跳过） |
| VoteIntentionDecision | 投票意向 | seat、reason |
| YesNoDecision | 是否用药 | decision（0或1） |
| WitchNightDecision | 女巫夜间决策 | use_potion、target |
| MindStateDecision | 信念矩阵更新 | b1、b2、wolf_camp |
| MultiSeatChoiceDecision | 多选座 | seats（列表） |

### 4.1 验证规则

- `public_speech` 必须 ≥ 15 字
- `public_speech` 不能仅为座位号（如 "3"）
- `public_speech` 不能为占位符（如 "（无公开发言）"）
- `seat` 必须 ≥ 0

## 5. 信念矩阵

### 5.1 三个面板

| 面板 | 说明 | 可见范围 |
|------|------|----------|
| B1 | 个人视角的好人/狼人判断 | 仅自己 |
| B2 | 对其他玩家视角的判断 | 仅自己 |
| W（狼队） | 狼人阵营内部信息同步 | 仅狼人 |

### 5.2 信念状态

`MindStateResult` 定义信念矩阵的结构化输出：

- 每个玩家的身份判断（好人/狼人/未知）
- 判断理由
- 置信度

### 5.3 信念更新

- 每轮发言后触发信念更新
- 根据新发言、投票结果、死亡信息更新判断
- 信念快照写入 WorkingMemory 的持久化槽位

## 6. 投票意向系统

### 6.1 意向追踪

- 记录每个玩家的当前投票意向（想投谁 + 理由）
- 支持快照对比（before → after）
- 支持锚点（Anchor）标记关键意向变化

### 6.2 快照格式

```
听完 玩家X 发言后意向：
[玩家1→无, 玩家3→无, ...] → [玩家1→3, 玩家3→无, ...]；N 人改意向
```

## 7. 阶段输出契约

| 阶段 | 输出类型 | 说明 |
|------|----------|------|
| 圆桌（RoundtablePhase） | SpeechDecision | 白天讨论、狼队夜聊、警上发言、遗言 |
| 行动（ActionPhase） | SeatChoiceDecision / YesNoDecision | 夜间选刀、守卫守人、验人、投票、女巫用药 |

## 8. 接口与扩展点

| 入口 | 类型 | 说明 |
|------|------|------|
| `PromptRegistry(version_dir)` | 构造函数 | 加载指定版本的 Prompt |
| `RolePrompts` | 类属性 | 各角色提示词（由 registry 注入） |
| `SpeechDecision` | Pydantic 模型 | 圆桌发言结构化输出 |
| `SeatChoiceDecision` | Pydantic 模型 | 选座结构化输出 |
| `MindStateDecision` | Pydantic 模型 | 信念矩阵结构化输出 |

## 9. 依赖与边界

- `strategy` 不依赖 `game_runtime`、`agent_team`、`evaluation`
- `game_runtime`、`agent_team`、`evaluation` 可依赖 `strategy`
- `strategy` 是纯策略与契约层，无业务逻辑依赖

## 10. 相关文档

- 进度：[ROADMAP.md](./ROADMAP.md)
- Prompt 调优方案：[../architecture/prompt_tuning.md](../architecture/prompt_tuning.md)
- 提示词版本与变量设计：[../architecture/吕祎晗-提示词版本与变量设计.md](../architecture/吕祎晗-提示词版本与变量设计.md)
- 工程结构方案：[../architecture/工程结构整理方案.md](../architecture/工程结构整理方案.md)
