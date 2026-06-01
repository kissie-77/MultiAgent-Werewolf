# Interface 模块

> **模块**：interface
> **状态**：active
> **最后更新**：2026-05-24
> **关联代码**：`src/llm_werewolf/interface/`
> **关联测试**：`tests/interface/`

## 职责

装配层与入口：CLI/TUI/API 入口、配置加载、模式选择、跨板块装配。负责将各模块组装成可运行的游戏，提供多种交互方式（命令行、终端 UI、Web API）。

## 不负责

- 游戏规则与引擎（见 `game_runtime`）
- Agent 执行与记忆（见 `agent_team`）
- Prompt 策略与决策 schema（见 `strategy`）
- 赛后评测逻辑（见 `evaluation`；本模块负责触发入口）
- Web 前端页面（见 `frontend`）

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `interface/cli/` | CLI 入口：主入口、投票摇摆分析、评测触发、TUI |
| `interface/cli/runtime/` | 核心实现：bootstrap、finalize_run、modes、overrides |
| `interface/bootstrap.py` 等 | 兼容 re-export，指向 `cli/runtime/` |
| `interface/api/` | Web API：FastAPI 应用、路由、服务层、数据模型 |
| `interface/api/routes/` | API 路由：动作、页面、遗留接口 |
| `interface/api/services/` | API 服务：游戏会话、配置解析、阵容定制、启动模式、回放、运行管理 |
| `interface/api/models/` | API 数据模型：动作、页面、通用模型 |
| `interface/tui.py` | 终端 UI：实时对局展示（werewolf-tui） |
| `interface/eval_cli.py` | `werewolf-eval` 入口（批量离线评测） |
| `interface/vote_swing_cli.py` | 投票摇摆分析 CLI |

## 依赖关系

- **可依赖**：`game_runtime`、`agent_team`、`strategy`、`evaluation`、`ui`
- **被依赖**：无（装配层，不被其他业务模块依赖）

## 文档索引

| 文档 | 用途 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 稳定设计与接口契约 |
| [ROADMAP.md](./ROADMAP.md) | 开发进度与计划 |

## 快速入口

```powershell
# 控制台 LLM 对局（首参为 YAML 路径，无 play 子命令）
uv run werewolf configs/llm-9p-doubao.yaml

# 人机混合（示例：1 号位为人类）
uv run werewolf configs/llm-9p-doubao.yaml --human_seat 1

# 启动 Web API（默认 127.0.0.1:8000）
uv run werewolf-api

# 批量离线正确性评测
uv run werewolf-eval --scenario smoke_6p_basic --games 3 --output_dir eval_runs/manual-smoke

# PostGame：对局结束后 finalize_run 自动触发，或 POST /api/v1/runs/{run_id}/post-game
```
