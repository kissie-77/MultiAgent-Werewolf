# RuntimeMemoryManager 与 Coach 分层说明

## 背景

项目早期由 `MemoryManager` 同时承担两类职责：

1. 运行时记忆编排
2. 经验提炼与赛后教练入口

这样虽然能工作，但职责边界偏宽，不利于后续继续演进 `Coach` 系统。

因此这次调整的目标不是删除运行时记忆管理，而是把它**收缩为更纯粹的运行时层**，同时让 `Coach` 明确承担教练职责。

## 调整后的分层

### 1. RuntimeMemoryManager

`RuntimeMemoryManager` 负责运行时记忆编排，只处理对局过程中必须实时发生的事情：

- 持有 `WorkingMemory`
- 持有 `EpisodicMemory`
- 持有 `SemanticMemory`
- 持有 `ProceduralMemory`
- 处理 `on_game_start / on_round_end / on_game_end`
- 决策前上下文组装
- 收集发言、事件、决策
- 记录本局使用过的 skill，供赛后权重更新

它的定位是：

**运行时记忆调度器，而不是教练系统。**

### 2. Coach

`Coach` 负责经验提炼与赛后教练相关能力：

- 从 episode / 对局报告中提炼语义经验候选
- 为 Skill 附加 episode 证据
- 输出 `coach_summary.json`
- 承接后续的复盘增强、写回策略、版本化教练闭环

它的定位是：

**赛后分析与策略进化层。**

## 当前闭环怎么跑

### 对局中

1. `RuntimeMemoryManager` 收集运行时信息
2. Working / Episodic / Semantic / Procedural 四层记忆分别维护
3. 决策时只注入运行时需要的上下文

### 对局结束

1. `RuntimeMemoryManager.on_game_end()` 更新本局使用过的 skill 权重
2. 如果开启提炼，则调用 `Coach.extract_semantic_candidates(...)`
3. `Coach` 返回新的经验候选
4. `RuntimeMemoryManager` 调用 `SemanticMemory.add_or_merge_card(...)` 写回
5. `SemanticMemory.evict_excess(...)` 做数量控制

### 赛后复盘

1. PostGame pipeline 运行
2. `Coach.enrich_skills_with_episodes(...)` 给 skill 补 POV episode 证据
3. 写出 `coach_summary.json`

## 为什么不直接删除 MemoryManager

因为“有 Coach”不等于“运行时记忆编排器不需要了”。

如果直接删掉运行时 manager，会导致下面这些逻辑重新分散回：

- agent
- factory
- 各 memory 子类

这样会让运行时协调逻辑更碎，工程上反而更差。

因此更合理的做法是：

- 保留运行时 manager
- 缩减它的职责范围
- 把教练职责明确迁给 `Coach`

这也是这次改名为 `RuntimeMemoryManager` 的原因。

## 兼容策略

为了避免一次性打断旧代码：

- 新主类名：`RuntimeMemoryManager`
- 保留兼容别名：`MemoryManager`
- `memory_manager.py` 现在是兼容转发层

这样做的目的是：

- 外部调用方可以逐步迁移
- 答辩和文档里可以直接使用新的更准确名字

## 当前收益

这次分层后的主要收益有：

1. 运行时层和教练层职责更清楚
2. `Coach` 不再只是赛后 enrich 附件，而是正式拥有经验提炼职责
3. 后续继续扩展 `Coach` 时，不需要再改坏运行时记忆编排
4. 项目在答辩表达上更完整：有运行时层，也有教练层

## 后续还能继续收的点

当前已经完成“提炼职责迁给 Coach”，但还有一处可以继续演进：

- 现在 `RuntimeMemoryManager` 仍然负责调用 `SemanticMemory.add_or_merge_card(...)` 完成写回

如果后面想让 `Coach` 更完整，还可以把：

- 提炼
- 写回
- 淘汰策略协调

进一步收成 `Coach` 的统一入口。

这一步目前不是必须，因为现阶段的职责边界已经足够清晰、稳定、可测试。

## 结论

现在项目中的记忆与教练分层可以概括为：

- `RuntimeMemoryManager`：负责运行时记忆管理
- `Coach`：负责赛后分析与经验提炼

这比“一个大而全的 MemoryManager”更工程化，也比“直接删掉 manager”更稳定、更容易扩展。
