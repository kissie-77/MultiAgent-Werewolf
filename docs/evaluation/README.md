# Evaluation 模块

> **模块**：evaluation
> **状态**：active
> **最后更新**：2026-06-04
> **关联代码**：`src/llm_werewolf/evaluation/`
> **关联测试**：`tests/evaluation/`
> **Agent Skill**：`.agents/skills/generated/evaluation/`

## 职责

赛后分析层：离线正确性评测、PostGame 复盘（14 步）、多维评分、Leaderboard 与 A/B、Coach Skill 生成与写回、自进化多轮 runner。

- **core/** — DemoAgent 批量评测 + checkers
- **post_game/** — 流水线、Coach、LLM 复盘、Skill 提取
- **leaderboard/** — 实验 entry 聚合与 A/B
- **evolution/** — manifest 继承、prompt_evolver

## 不负责

- 对局规则与阶段推进（`game_runtime`）
- 运行时 Agent 决策（`agent_team`）
- Web 渲染（`frontend` / `interface`）
- 运行时 Prompt 直接覆盖（走 evolution + 人工审核）

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `evaluation/core/` | runner、checkers、scenarios |
| `evaluation/post_game/` | pipeline、Coach、eval_agent |
| `evaluation/post_game/skill_generation/` | Skill 提取、场景合并（+0.15）、稀疏 bump 写回 `skills/<role>/<version>/` |
| `evaluation/scoring/` | intention、benefit、belief_calibration |
| `evaluation/log_views/` | POV 视图 |
| `evaluation/leaderboard/` | entry、A/B CLI |
| `evaluation/evolution/` | `run_evolution_cycle`、manifest |
| `evaluation/signals/` | run 产物扫描信号（供 observability / `werewolf-watch`） |

## 依赖关系

- **可依赖**：`game_runtime`、`strategy`、`agent_team`
- **不可依赖**：`observability`（质量信号由 observability 只读调用 `evaluation/signals/`）
- **被依赖**：`interface`（finalize_run、werewolf-eval、PostGame API）
- **可写入**：`agent_team/skills/<role>/<skill_version>/`

## 文档

本模块仅保留三件套（见 [DOC_TEMPLATE.md](../DOC_TEMPLATE.md)）：

| 文档 | 用途 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 设计、产物、Leaderboard、自进化、边界（**单一真相**） |
| [ROADMAP.md](./ROADMAP.md) | 进度与计划 |
| [review-dashboard.html](./review-dashboard.html) | 复盘系统静态可视化（浏览器打开，备查 PostGame 流水线与产物） |

历史专题原文已迁至 [architecture/evaluation/](../architecture/evaluation/)，内容已合并进 DESIGN，**勿再单独维护**。

## 快速入口

```bash
uv run werewolf-eval --scenario smoke_6p_basic --games 3 --timeout_seconds 20 --output_dir eval_runs/manual-smoke
uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation -q
uv run python -m llm_werewolf.evaluation.leaderboard.cli build eval_runs
uv run python -m llm_werewolf.evaluation.leaderboard.cli compare eval_runs/a/leaderboard_entry.json eval_runs/b/leaderboard_entry.json
```

源码说明：[src/llm_werewolf/evaluation/README.md](../../src/llm_werewolf/evaluation/README.md)
