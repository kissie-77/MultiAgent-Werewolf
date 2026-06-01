# 文档写作规范与示例

> **用途**：本文件是 `docs/` 的统一规范与模板。新建或整理模块文档时，按此格式撰写。
> **状态**：active
> **最后更新**：2026-05-23

---

## 1. 基本原则

1. **按模块组织**：业务文档放在对应模块目录下，不在 `docs/` 根目录新增业务文档。
2. **三件套**：每个模块固定三份文档——`README.md`（介绍）、`DESIGN.md`（设计）、`ROADMAP.md`（进度）。
3. **少即是多**：优先更新现有文档；只有无法并入 `DESIGN.md` 时才新增同模块下的补充文档。
4. **单一真相**：结论写入模块 `DESIGN.md`；实验/排查过程稿放 `reports/` 或 `archive/`，不在模块里堆重复稿。

### 1.1 模块目录


| 目录                   | 对应代码                             | 说明                       |
| -------------------- | -------------------------------- | ------------------------ |
| `docs/game_runtime/` | `src/llm_werewolf/game_runtime/` | 规则、引擎、状态、事件              |
| `docs/agent_team/`   | `src/llm_werewolf/agent_team/`   | Agent、记忆、通信、Skill 读取     |
| `docs/strategy/`     | `src/llm_werewolf/strategy/`     | Prompt、决策 schema、信念      |
| `docs/evaluation/`   | `src/llm_werewolf/evaluation/`   | 复盘、评分、PostGame、Coach     |
| `docs/interface/`    | `src/llm_werewolf/interface/`    | CLI/TUI/API、装配与配置        |
| `docs/ui/`           | `src/llm_werewolf/ui/`           | 展示与 presenter            |
| `docs/frontend/`     | `frontend/`                      | Web 前端（React + Three.js） |
| `docs/architecture/` | （跨模块）                            | 全局依赖边界、跨板块方案             |


### 1.2 非模块文档放哪


| 类型        | 位置                     | 何时使用              |
| --------- | ---------------------- | ----------------- |
| 未收敛的实验/排查 | `docs/reports/`        | 有数据、结论尚未写入 DESIGN |
| 已过时、仅备查   | `docs/archive/`        | 不再作为执行依据          |
| 全站导航      | `docs/README.md`       | 索引各模块入口           |
| 写作规范      | `docs/DOC_TEMPLATE.md` | 本文件               |


---

## 2. 元信息头（每篇文档必填）

每份 Markdown 在标题下用引用块写元信息：

```markdown
# 文档标题

> **模块**：evaluation
> **状态**：active | draft | deprecated
> **最后更新**：YYYY-MM-DD
> **关联代码**：`src/llm_werewolf/evaluation/`
> **关联测试**：`tests/evaluation/`
> **Agent Skill**：`.agents/skills/generated/evaluation/`
```


| 字段            | 说明                                          |
| ------------- | ------------------------------------------- |
| 模块            | 所属板块名，跨模块文档写 `architecture` 或 `project`     |
| 状态            | `active` 现行依据；`draft` 撰写中；`deprecated` 即将归档 |
| 最后更新          | 正文有实质修改时更新                                  |
| 关联代码/测试/Skill | 方便与实现、GitNexus 索引对照                         |


---

## 3. 模板 A：`README.md`（模块介绍）

**目标**：让读者 5 分钟内知道「这个模块干什么、代码在哪、该读哪份设计」。

```markdown
# Evaluation 模块

> **模块**：evaluation
> **状态**：active
> **最后更新**：2026-05-23
> **关联代码**：`src/llm_werewolf/evaluation/`
> **关联测试**：`tests/evaluation/`
> **Agent Skill**：`.agents/skills/generated/evaluation/`

## 职责

赛后分析层：复盘、评分、PostGame 流水线、Leaderboard、Coach 触发的 Skill 生成。

## 不负责

- 对局规则与阶段推进（见 `game_runtime`）
- 运行时 Agent 决策（见 `agent_team`）
- Web 页面渲染（见 `frontend` / `interface` API）

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `evaluation/core/` | 评测 runner、指标、记录 |
| `evaluation/post_game/` | PostGame 流水线、Coach |
| `evaluation/post_game/skill_generation/` | 赛后 Skill 生成 |
| `evaluation/scoring/` | 多维评分 |
| `evaluation/leaderboard/` | 榜单与 AB 对比 |

## 依赖关系

- **可依赖**：`game_runtime`、`strategy`、`agent_team`（读 Skill 产物）
- **被依赖**：`interface`（eval CLI、API 触发 PostGame）

## 文档索引

| 文档 | 用途 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 稳定设计与接口契约 |
| [ROADMAP.md](./ROADMAP.md) | 开发进度与计划 |

## 快速入口

    # 离线批量评测
    uv run werewolf-eval --scenario smoke_6p_basic --games 3 --output_dir eval_runs/manual-smoke
    # PostGame：对局结束后 finalize_run 自动触发，或 POST /api/v1/runs/{run_id}/post-game
```

---

## 4. 模板 B：`DESIGN.md`（项目设计）

**目标**：记录**相对稳定**的设计决策；变更设计时改此文件，而不是新建 `xxx-改动说明-2026-xx-xx.md`。

```markdown
# Evaluation 设计

> **模块**：evaluation
> **状态**：active
> **最后更新**：2026-05-23
> **关联代码**：`src/llm_werewolf/evaluation/`

## 1. 目标

对局结束后产出可复用的分析资产：时间线、评分、信念校准、Coach 报告、角色 Skill 更新建议。

## 2. 范围

### 做

- 从 `artifacts/runs/<run_id>/` 读取事件与日志
- 跑 PostGame pipeline，写入 report、beliefs、skills 等产物
- Leaderboard 聚合与 AB 对比

### 不做

- 不修改对局进行中的 `GameState`
- 不在此模块直接调用 LLM 做**局内**决策（局内归 `agent_team`）

## 3. 核心流程

game_runtime 事件/日志
    → evaluation/post_game/pipeline
    → 产物：report.md、beliefs.jsonl、skills/*.md、scores.json ...
    → agent_team/skill_loader 读取 skills


## 4. 关键概念


| 概念       | 说明                                                    |
| -------- | ----------------------------------------------------- |
| PostGame | 单场对局赛后分析流水线                                           |
| Coach    | 位于 `post_game/coach/`，负责复盘与 Skill 生成策略                |
| Skill 生成 | `post_game/skill_generation/`，写入 `agent_team/skills/` |


## 5. 接口与产物


| 入口                                 | 类型   | 说明              |
| ---------------------------------- | ---- | --------------- |
| `POST /api/v1/runs/{id}/post-game` | HTTP | Web 触发 PostGame |
| evaluation CLI                     | 命令行  | 批量评测、榜单         |
| `artifacts/runs/<id>/post_game/`   | 目录   | 主要产物位置          |


## 6. 依赖与边界

遵循 [工程结构整理方案](../architecture/工程结构整理方案.md)：

- `evaluation → game_runtime, strategy, agent_team`
- `evaluation` 可**写入** `agent_team/skills/`
- `agent_team` **只读** skills，不在此模块生成

## 7. 相关文档

- 进度：[ROADMAP.md](./ROADMAP.md)
- 历史实验：[reports/](../reports/)

```

---

## 5. 模板 C：`ROADMAP.md`（开发进度）

**目标**：只看这一份就能知道「做了什么、正在做什么、下一步是什么」。**不写长文设计**。

```markdown
# Evaluation 开发进度

> **模块**：evaluation
> **状态**：active
> **最后更新**：2026-05-23

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| PostGame 基础流水线 | ✅ Done | pipeline + 核心产物 |
| Skill 生成重构 | ✅ Done | `skill_generation/` 子包 |
| 信念校准进 PostGame | 🔄 In Progress | 与 strategy 信念矩阵对齐 |
| Leaderboard Web 展示 | 📋 Planned | 依赖 frontend |

## 已完成

- [x] PostGame pipeline 分步执行与重跑
- [x] Coach 与 Skill 生成职责拆分

## 进行中

- [ ] 信念快照写入 replay API 字段
- [ ] 旧文档内容合并进 DESIGN

## 计划中

- [ ] PostGame 增量生成（仅缺啥补啥）

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-05-23 | 初始化 ROADMAP |
```

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`

---

## 6. 何时允许新增「第四份」文档

默认只有 README / DESIGN / ROADMAP。仅以下情况可在**模块目录内**新增一篇：


| 场景     | 做法                                      | 完成后                       |
| ------ | --------------------------------------- | ------------------------- |
| 大型功能专项 | 先写 `DESIGN` 独立章节；实在过长再用 `DESIGN-xxx.md` | 合并进 DESIGN，原文件 deprecated |
| 临时实验记录 | 放 `docs/reports/`，不在模块根目录堆日期稿           | 结论进 DESIGN 后归档            |


**禁止**：在 `docs/` 根目录新建 `xxx报告.md`、`xxx开发记录-日期.md`。

---

## 7. 写作风格

- 用完整句子；代码路径、命令、API 用反引号；文件引用用相对链接。
- 设计与进度分离：DESIGN 不写「下周要做」；ROADMAP 不写大段原理。
- 中文为主；标识符、路径、API 保持英文原名。

---

## 8. 整理 checklist（迁移旧文档时用）

- 模块下已创建 `README.md`、`DESIGN.md`、`ROADMAP.md`
- 旧文档结论已合并，文首标记 `deprecated` 或移入 `archive/`
- `docs/README.md` 已更新模块入口链接
- 元信息头、最后更新日期已填写
- 与 `architecture/工程结构整理方案.md` 依赖描述无冲突

---

## 9. 最小空白模板（复制即用）

将 `{module}`、`{Module 中文名}` 替换后填入各模块目录。

### README.md

```markdown
# {Module 中文名} 模块

> **模块**：{module}
> **状态**：draft
> **最后更新**：YYYY-MM-DD
> **关联代码**：`src/llm_werewolf/{module}/`
> **关联测试**：`tests/{module}/`
> **Agent Skill**：`.agents/skills/generated/{module}/`

## 职责

## 不负责

## 文档索引

- [DESIGN.md](./DESIGN.md)
- [ROADMAP.md](./ROADMAP.md)
```

### DESIGN.md

```markdown
# {Module 中文名} 设计

> **模块**：{module}
> **状态**：draft
> **最后更新**：YYYY-MM-DD
> **关联代码**：`src/llm_werewolf/{module}/`

## 1. 目标

## 2. 范围（做 / 不做）

## 3. 核心流程

## 4. 关键概念

## 5. 接口与扩展点

## 6. 依赖与边界

## 7. 相关文档
```

### ROADMAP.md

```markdown
# {Module 中文名} 开发进度

> **模块**：{module}
> **状态**：draft
> **最后更新**：YYYY-MM-DD

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|

## 已完成

## 进行中

## 计划中

## 变更记录

| 日期 | 摘要 |
|------|------|
```

