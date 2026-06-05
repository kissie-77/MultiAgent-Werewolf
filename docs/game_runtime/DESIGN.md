# Game Runtime 设计

> **模块**：game_runtime
> **状态**：active
> **最后更新**：2026-06-05
> **关联代码**：`src/llm_werewolf/game_runtime/`

## 1. 目标

提供狼人杀游戏的完整规则引擎：角色系统、状态管理、阶段推进（黑夜/白天/投票）、事件系统、胜负判定。作为整个项目的核心规则层，不依赖任何 Agent 实现。

## 2. 范围

### 做

- 定义所有角色（狼人、预言家、女巫、猎人、守卫等）及其技能
- 管理游戏状态（玩家存活、死亡、投票、技能使用）
- 推进游戏流程（Setup → Night → Day Discussion → Voting → 循环）
- 产生标准化事件（死亡、查验、投票结果等）
- 控制事件可见性（不同角色看到不同信息）
- 判定胜负条件

### 不做

- 不直接调用 LLM 做决策（归 `agent_team`）
- 不处理赛后评测（归 `evaluation`）
- 不提供 UI 渲染（归 `ui` / `frontend`）
- 不管理 Agent 记忆（归 `agent_team/memory`）

## 3. 核心流程

```
GameEngine.run_game()
    → Setup 阶段：初始化角色、注入 PhaseInteraction
    → Night 阶段：
        → 夜间计划规格表决定唤醒批次与顺序
        → 守卫/梦魇狼/守墓狼等预狼阶段技能
        → 狼人讨论 & 刀人
        → 女巫用药（解药/毒药）
        → 预言家查验
        → 守墓人/渡鸦/魔术师等后置夜间角色行动
    → Day 阶段：
        → 公布死亡信息
        → 白天讨论（Agent 发言）
        → 警长选举（可选）
        → 投票放逐
        → 死亡技能触发（猎人带走等）
    → 循环直到胜负判定
```

## 4. 关键概念

| 概念 | 说明 |
|------|------|
| GameEngine | 主引擎类，通过 Mixin 架构组织游戏流程 |
| GameState | 游戏状态管理：玩家、阶段、死亡、投票、技能使用 |
| Player | 玩家模型：座位号、身份、存活状态、阵营 |
| GamePhase | 游戏阶段枚举：SETUP, NIGHT, DAY_DISCUSSION, VOTING |
| Camp | 阵营枚举：VILLAGER, WEREWOLF, NEUTRAL |
| Event | 事件系统：标准化事件定义与可见性控制 |
| RoleDefinition | 角色定义：名称、实现类、阵营、胜利条件 |
| PhaseInteraction | 阶段交互 API：引擎与 Agent 层的通信接口 |
| VictoryChecker | 胜负判定：狼人数量 >= 好人数量则狼人胜 |

## 5. Mixin 架构

GameEngine 通过多个 Mixin 组织职责：

| Mixin | 职责 |
|-------|------|
| GameEngineBase | 核心初始化、主循环、阶段切换 |
| NightPhaseMixin | 夜间行动调度、角色唤醒、技能执行 |
| DayPhaseMixin | 白天讨论、发言顺序控制 |
| VotingPhaseMixin | 投票逻辑、平票处理、PK 发言 |
| SheriffElectionMixin | 警长选举流程 |
| DeathHandlerMixin | 死亡处理、死亡技能触发、死亡信息 |
| ActionProcessorMixin | 通用动作处理 |

## 6. 角色系统

### 6.1 角色目录

所有角色在 `roles/catalog.py` 中统一定义：

| 角色 | 阵营 | 胜利条件 |
|------|------|----------|
| Werewolf | 狼人 | 狼人数量 >= 好人数量 |
| AlphaWolf（狼王） | 狼人 | 同上，死亡可带走一人 |
| WhiteWolf（白狼） | 狼人 | 同上；可夜间自刀；**白天发言可自爆**（`SpeechDecision.self_explode` → 跳过白天投票进黑夜） |
| WolfBeauty（狼美人） | 狼人 | 同上，可魅惑一人 |
| Villager（平民） | 好人 | 淘汰所有狼人 |
| Seer（预言家） | 好人 | 同上，可查验身份 |
| Witch（女巫） | 好人 | 同上，有解药和毒药 |
| Hunter（猎人） | 好人 | 同上，死亡可带走一人 |
| Guard（守卫） | 好人 | 同上，可守护一人 |
| Magician（魔术师） | 好人 | 同上，整局一次夜间交换两名玩家身份 |

### 6.2 夜间死亡结算（女巫 / 守卫）

夜间狼刀结算由 `DeathHandlerMixin.resolve_deaths()` 统一处理，顺序为：

1. 狼人刀口（`_handle_werewolf_kill`）
2. 女巫毒药（`_resolve_witch_poison_death`）
3. 狼美人魅惑连带（`_resolve_wolf_beauty_charm_deaths`）
4. 死亡技能（猎人 / 狼王 / 警徽移交等）

**刀口存活判定**（`_handle_werewolf_kill`）：

| 场景 | 结果 | `death_causes` |
|------|------|----------------|
| 仅守卫保护刀口 | 存活 | — |
| 仅女巫解药救刀口 | 存活 | — |
| 守卫与女巫同夜同救刀口（毒奶） | **死亡** | `guard_witch_conflict` |
| 无保护 | 死亡 | `werewolf` |

**女巫规则**：

- 解药只能救当夜狼刀目标（`werewolf_target`），整局一瓶
- 毒药可毒任意存活玩家，整局一瓶
- 被毒杀玩家记入 `death_causes = witch_poison`，**不能发动死亡技能**（猎人开枪等）

**守卫规则**：

- 不能连续两夜保护同一人（`last_protected` 校验）
- 保护目标写入 `guard_protected`，与女巫解药在结算时合并判定

**死亡链传播**：

- 情侣一方死亡 → 伴侣殉情（加入 `night_deaths` / `day_deaths`）
- 狼美人死亡 → 被魅惑者殉情；若被魅惑者也是情侣，继续传播
- 殉情后加入死亡集合，供 `_handle_death_abilities` 触发后续技能

测试：`tests/game_runtime/test_witch_guard_logic.py`、`tests/game_runtime/test_death_chain.py`

### 6.3 角色实现

- 基础角色类在 `roles/base.py`
- 狼人系角色在 `roles/werewolf.py`
- 好人系角色在 `roles/villager.py`
- 中立角色在 `roles/neutral.py`

### 6.3 夜间计划规格

夜间技能调度由 `game_runtime/registries/role_night_plans.py` 的 `NIGHT_PLAN_SPECS` 声明，`night_scheduler.py` 只读取规格表，不再维护分散的角色名硬编码列表。

每个夜间角色的规格包含：

- `stage`：所属批次，例如 `pre_wolf`、`wolf_phase_special`、`witch`、`post_witch`
- `order`：同批次内顺序
- `planner`：该角色如何向 `PhaseInteraction` 请求目标或决策
- `wolf_vote`：该角色是否参与狼队刀票

复杂角色扩展示范：`Magician` 已通过 `MagicianSwapAction` + `plan_magician_swap` + `NIGHT_PLAN_SPECS` 接入夜间流程。它可以整局一次选择两名存活玩家交换身份，事件 `MAGICIAN_SWAPPED` 仅魔术师本人可见。该实现没有在夜晚主流程里新增魔术师专用分支，用于证明“新增复杂角色主要修改角色/动作/夜间计划注册，而不是改主调度器”。

## 7. 事件系统

### 7.1 事件可见性

事件根据接收者角色有不同的可见性：

- **PUBLIC**：所有玩家可见（如死亡公告、投票结果）
- **WOLF_TEAM**：仅狼人可见（如狼人讨论内容）
- **PRIVATE**：仅特定角色可见（如预言家查验结果仅自己可见）

事件和 observation 的可见性是人机混战的信息隔离边界。`visible_to` 只能表达局内可见范围，不能携带模型、人类、backend、demo 等运行身份信息。`game_runtime` 产生的 observation 应面向“座位、角色、阶段、事件”描述，不面向“谁由什么后端控制”描述。

observation 中的存活概况只展示 `X/Y 人存活`，不直接输出“狼人 N / 好人 M”等隐藏阵营存活数量。阵营数量属于规则推理结果，只能由玩家根据公开事件推断，不能由系统上下文直接注入。

夜间私密 prompt 只应包含本阶段必需的身份、队友、可选目标和行动约束。重复身份卡、重复狼队友描述虽然不属于信息泄露，但会降低人类玩家体验并分散 LLM 注意力，应在 prompt selector 和夜间角色行动上下文中避免重复注入。

### 7.2 事件类型

- 角色行动事件（查验、保护、刀人等）
- 死亡事件（狼刀、投票、技能等）
- 投票事件（意向变化、最终投票）
- 阶段切换事件

## 8. 接口与扩展点

| 入口 | 类型 | 说明 |
|------|------|------|
| `GameEngine(config, language=..., information_hub=...)` | 构造函数 | 初始化游戏引擎；`setup_game` 时 **information_hub 为 None 即 fail-fast** |
| `engine.run_game()` | 方法 | 运行完整对局 |
| `GameState` | 状态对象 | 读写游戏状态 |
| `PhaseInteraction` | 接口 | 引擎与 Agent 层通信 |
| `Event` | 事件对象 | 标准化事件定义 |
| `NIGHT_PLAN_SPECS` | 夜间计划规格表 | 声明角色夜间批次、顺序、planner 和狼队刀票参与关系 |

## 8.1 扩展复杂夜间角色的推荐步骤

新增一个复杂夜间角色时，优先按以下顺序做：

1. 在 `roles/catalog.py` 注册角色定义，并在 `roles/*.py` 实现角色状态。
2. 在 `actions/` 增加对应 `Action`，把状态变更放在 `execute()` 中。
3. 在 `registries/role_night_plans.py` 增加 planner 与 `NIGHT_PLAN_SPECS` 条目。
4. 如需要可追踪日志，补 `EventType`、`event_visibility.py` 和 `ActionProcessorMixin` 的 typed event logger。
5. 补测试：action 行为、事件可见性、scheduler 通过规格表调度。

不要为了单个新角色修改 `NightSkillScheduler` 的主流程分支；如果需要改 scheduler，优先检查是不是缺了通用阶段或规格字段。

## 9. 依赖与边界

遵循工程结构整理方案：

- `game_runtime → strategy`（稳定 DTO / 决策契约）
- `game_runtime` 不依赖 `agent_team`、`evaluation`、`interface`、`ui`
- `agent_team`、`evaluation`、`interface` 可依赖 `game_runtime`

## 10. 配置系统

| 配置类 | 说明 |
|--------|------|
| GameConfig | 游戏总配置：人数、角色配置、超时设置 |
| PlayerConfig | 单个玩家配置：名称、模型、后端 |
| MemoryConfig | 记忆配置：压缩、摘要、检索 |
| Presets | 预设配置：9人局、12人局等标准配置 |

## 11. 序列化

- `GameState` 支持序列化/反序列化，用于复盘和重放
- 事件历史完整记录，支持 PostGame 分析
- 序列化产物放在 `artifacts/runs/<run_id>/` 目录

## 12. 相关文档

- 进度：[ROADMAP.md](./ROADMAP.md)
- 工程结构方案：[../architecture/工程结构整理方案.md](../architecture/工程结构整理方案.md)
- 信念矩阵设计：[../architecture/信念矩阵功能设计.md](../architecture/信念矩阵功能设计.md)
