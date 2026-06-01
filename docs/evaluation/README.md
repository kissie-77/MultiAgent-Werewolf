# Evaluation 模块

> **模块**：evaluation
> **状态**：active
> **最后更新**：2026-05-23
> **关联代码**：`src/llm_werewolf/evaluation/`
> **关联测试**：`tests/evaluation/`
> **Agent Skill**：`.agents/skills/generated/evaluation/`

## 职责

赛后分析层：离线正确性评测、PostGame 复盘流水线、多维评分、Leaderboard 与 A/B 对比、Coach 触发的 Skill 生成与写回。

- **离线评测（`core/`）**：用 `DemoAgent` 批量跑场景。
- **PostGame（`post_game/`）**：对局结束后自动或手动触发。
- **Leaderboard（`leaderboard/`）**：聚合多次实验为榜单。

## 不负责

- 对局规则与阶段推进（见 `game_runtime`）
- 运行时 Agent 决策（见 `agent_team`）
- Web 页面渲染（见 `frontend` / `interface`）
- 运行时 Prompt 直接改写（仅 draft JSON）

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `evaluation/core/` | runner、checkers、metrics、scenarios、recorder、reporter |
| `evaluation/post_game/` | PostGame 流水线、Coach、LLM 复盘 |
| `evaluation/post_game/skill_generation/` | Skill 提取、MD、写回 `agent_team/skills/` |
| `evaluation/post_game/scoring/` | MVP、score_contexts |
| `evaluation/scoring/` | intention、benefit、belief_calibration |
| `evaluation/log_views/` | POV 视图与 digest |
| `evaluation/leaderboard/` | entry、聚合、A/B CLI |

## 依赖关系

- **可依赖**：`game_runtime`、`strategy`、`agent_team`
- **被依赖**：`interface`（`finalize_run`、`werewolf-eval`、`POST /api/v1/runs/{id}/post-game`）
- **可写入**：`agent_team/skills/<role>/*.md`（门控双写）

## 文档索引

| 文档 | 用途 |
|------|------|
| [DESIGN.md](./DESIGN.md) | PostGame 步骤、checkers、API、边界 |
| [ROADMAP.md](./ROADMAP.md) | 阶段进度与计划 |
| [PostGame产物地图.md](./PostGame产物地图.md) | 产物详解（历史参考） |
| [Leaderboard与AB对比说明.md](./Leaderboard与AB对比说明.md) | 版本链说明（历史参考） |

## 快速入口

```powershell
uv run werewolf-eval --scenario smoke_6p_basic --games 3 --timeout_seconds 20 --output_dir eval_runs/manual-smoke
uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation -q
# POST /api/v1/runs/{run_id}/post-game
uv run python -m llm_werewolf.evaluation.leaderboard.cli build eval_runs
uv run python -m llm_werewolf.evaluation.leaderboard.cli compare eval_runs/run_a/leaderboard_entry.json eval_runs/run_b/leaderboard_entry.json
```

## 离线评测详情

checkers、metrics、内置场景与 `eval_runs/` 产物结构详见源码文档：

[`src/llm_werewolf/evaluation/README.md`](../../src/llm_werewolf/evaluation/README.md)
