# Memory 设计

> **模块**：agent_team / memory
> **状态**：active
> **最后更新**：2026-05-26
> **关联代码**：`src/llm_werewolf/agent_team/memory/`
> **关联测试**：`tests/agent_team/test_*memory*`、`tests/game_runtime/test_memory_*`

## 1. 目标

为每个 Agent 提供**运行时**可注入、可压缩、可复盘的多层记忆，并在不引入向量外部依赖的前提下，用 **Skill MD** 承担跨局语义记忆。

## 2. 范围

### 做

- 四层记忆统一由 `RuntimeMemoryManager` 调度
- 生命周期钩子：`on_game_start` / `on_round_end` / `on_game_end`
- 决策前上下文组装（工作记忆 + 程序记忆 + 语义 Skill + 信念快照）
- 采集公开发言、可见事件、Agent 决策、本局使用的 skill id
- 工作记忆 LLM 压缩（带重试与 fallback）
- 情景记忆全局查询（PostGame / Coach 消费）
- 语义卡片 JSON 持久化、去重合并、权重更新

### 不做

- 不生成 Skill（`evaluation/post_game/skill_generation`）
- 不做向量 embedding / ReMe（2026-05-26 下线）
- 不在运行时直接写 Prompt YAML
- Coach 的 enrich / coach_summary 不在本包实现（仅被 manager 回调）

### 模块边界

| 组件 | 职责 | 禁止 |
|------|------|------|
| `RuntimeMemoryManager` | 运行时编排、注入、收集 | 赛后 Skill MD 生成 |
| `SemanticMemory` | 读 Skill + 本地策略卡片 | 调用 evaluation |
| `Coach`（evaluation） | 提炼候选、enrich skill、coach_summary | 持有 working/episodic 实例 |
| `skill_loader` | 读 `skills/<role>/<version>/` | 写 Skill 文件 |

## 3. 四层架构

```text
WorkingMemory          EpisodicMemory
  短期上下文              关键事件时间线
  按轮压缩                玩家 POV + 全局查询
  信念矩阵快照            AGENT_THOUGHT（仅复盘）

SemanticMemory         ProceduralMemory
  Skill MD（主）          角色 plan 摘要
  策略卡片 JSON（辅）      PromptManager 封装
  weight 排序 top_k
```

| 层 | 类 | 主要输入 | 主要输出 |
|----|-----|----------|----------|
| 工作 | `WorkingMemory` | 发言、事件、决策 | 压缩摘要、persistent 条 |
| 情景 | `EpisodicMemory` | `event_logger` | `get_all_events()` 等 |
| 语义 | `SemanticMemory` | `skill_loader`、卡片 JSON | 注入 prompt 的 Skill 描述 |
| 程序 | `ProceduralMemory` | `plan_name`、角色 | `[程序记忆]` 摘要 |

## 4. 生命周期

```text
on_game_start(role)
  → 注入 SemanticMemory（load_role_skills，按 weight 降序 top_k）
  → 记录本局 prompt 注入的 skill
  → ProceduralMemory.build_plan_summary → working.add_persistent

每轮 on_round_end(round)
  → working.end_round()（可选 LLMCompressor 压缩）

on_game_end(won)
  → semantic.update_after_game（used skill 权重 win/use）
  → extract_semantic_candidates → add_or_merge_card（若开启）
  → semantic.evict_excess
```

**运行时输入**（已实现）：Agent 决策、白天公开发言、玩家可见关键事件。

**情景 → 语义提炼**（规则式）：关键局势复盘、决策经验、胜利/失败反思 → `StrategyCard` JSON。

## 5. RuntimeMemoryManager 与 Coach 分层

早期 `MemoryManager` 同时承担运行时编排与经验提炼，职责过宽。现拆分为：

### RuntimeMemoryManager（运行时）

- 持有四层 memory 实例
- `on_game_start / on_round_end / on_game_end`
- 决策前上下文组装
- 收集发言、事件、决策、本局 used skill
- **不是**教练系统

### Coach（evaluation/post_game/coach）

- `extract_semantic_candidates` — 从 episode / 报告提炼候选
- `enrich_skills_with_episodes` — Skill 附加 POV 证据
- 输出 `coach_summary.json`
- 赛后分析与策略进化层

### 对局结束协作

1. `RuntimeMemoryManager.on_game_end()` 更新 skill 权重
2. 若开启提炼 → Coach 返回候选 → `SemanticMemory.add_or_merge_card`
3. PostGame → Coach enrich → `coach_summary.json`

**兼容**：`MemoryManager = RuntimeMemoryManager`（`memory_manager.py` 转发）。

**后续可选演进**：将 add_or_merge / evict 进一步收成 Coach 统一入口（非必须）。

## 6. ReMe 下线与 Skill 语义记忆

**决策（2026-05-26）**：ReMe 依赖 embedding + 外部 API，部署与成本高；evaluation 已有 Skill 提取-存储-加载闭环，语义记忆直接复用 Skill `.md`。

**变更**：

- `MemoryConfig` 删除 `reme_*` 字段
- 去掉 `ReMeSemanticBackend` 初始化路径
- `factory.py` 删除 `REME_*` 环境变量
- `reme_backend.py` 已删除；**保留** `LLMCompressor`（纯 LLM，无向量，位于 memory 压缩模块）

**运行时语义来源**：`SemanticMemory` → `skill_loader.load_role_skills()` → `skills/<role>/<version>/*.md`，frontmatter `weight` 降序，取 top_k 注入 prompt。

## 7. Skill MD 格式约定

```yaml
---
skill_id: wolf_r1_player_2_1
prompt_role_key: wolf
status: draft
weight: 1.0
win_count: 0
use_count: 0
created_at: 2026-05-26T00:00:00+00:00
updated_at: 2026-05-26T00:00:00+00:00
source_run: runs/20260526-120000
source_player_id: player_2
camp: werewolf
quality_passed: true
---
```

`skill_md.py` / `skill_extractor` / `skill_loader` 已对齐上述 frontmatter 字段。

## 8. EpisodicMemory 扩展

- 玩家视角查询（原有，不破坏）
- 全局 API：`get_all_events()`、`get_round_events()`、`get_global_key_events()`、`get_thought_events()`
- `EventType.AGENT_THOUGHT` — 仅复盘/教练，不进入公开可见信息

PostGame `episodic_bridge` 复用同一 API；Coach 为 Skill 附加 `evidence.episodic_excerpt`。

## 9. LLMCompressor 容错

`llm_compressor.py` 在每轮结束时压缩 working memory 动态项。

| 行为 | 说明 |
|------|------|
| 重试 | 最多 3 次，指数退避 0.5s → 1.0s → 2.0s |
| 降级 | 全部失败后 fallback 本地压缩，游戏不中断 |
| 日志 | 第 1 次失败 warning；之后每累计 5 次再 warning；成功则清零 |

属依赖链容错增强，不改变四层职责划分。

## 10. 配置

`MemoryConfig`（`game_runtime.config.memory_config`，经 `memory/config.py` 导出）控制：

- 是否启用记忆框架 / 各层开关
- `working_max_rounds`、`working_max_dynamic_items` 等窗口
- 每局注入语义卡片数量、语义存储目录
- `extract_semantic_on_game_end` 是否局末提炼

## 11. 代码结构

```text
src/llm_werewolf/agent_team/memory/
├── runtime_memory_manager.py   # 主类
├── memory_manager.py           # MemoryManager 别名转发
├── working_memory.py
├── episodic_memory.py
├── semantic_memory.py
├── procedural_memory.py
├── semantic_matching.py
├── llm_compressor.py
├── base.py
└── config.py
```

记忆实现归位于 `agent_team/memory/`，**不作为独立第七主模块**（2026-05-25 架构归位）。

## 12. 与 agent_team 其他部分

```text
factory.configure_agents_for_players
  → RuntimeMemoryManager(event_logger, role, plan_name, config)
  → Agent 决策前 manager 组装 context
  → Bridge 解析后 manager 记录决策/发言
```

`factory.py` 的 `bind_prompt` / `configure_role` 分支均传入 `event_logger`（2026-05-26 修复）。

## 13. 依赖与边界

- `memory → game_runtime`（事件、MemoryConfig）
- `memory → strategy`（PromptManager，程序记忆）
- `memory → skill_support.skill_loader`（只读 Skill）
- `evaluation → skills/` 写入；`memory` 只读
- 信念矩阵：working memory 可含 B1/B2/W 快照（见 [architecture/信念矩阵功能设计.md](../../architecture/信念矩阵功能设计.md)）

## 14. 相关文档

| 文档 | 用途 |
|------|------|
| [ROADMAP.md](./ROADMAP.md) | 进度 |
| [agent_team/DESIGN.md](../DESIGN.md) | Agent 层总览 |
| [evaluation/DESIGN.md](../../evaluation/DESIGN.md) | PostGame、Coach、Skill 写回 |
| [architecture/memory/](../../architecture/memory/) | 历史开发记录备查 |
