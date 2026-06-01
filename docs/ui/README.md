# UI 模块

> **模块**：ui
> **状态**：active
> **最后更新**：2026-05-24
> **关联代码**：`src/llm_werewolf/ui/`
> **关联测试**：`tests/ui/`

## 职责

展示层：控制台展示器、TUI 应用、UI 组件（聊天面板、游戏面板、玩家面板）、样式定义。只读事件与状态，负责将游戏过程以美观的方式展示给用户。

## 不负责

- 游戏规则与引擎（见 `game_runtime`）
- Agent 决策与执行（见 `agent_team`）
- CLI/TUI 入口与装配（见 `interface`）
- Web 前端页面（见 `frontend`）

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `ui/components/` | UI 组件：聊天面板、游戏面板、玩家面板 |
| `ui/console_presenter.py` | 控制台展示器：Rich 库美化输出、事件格式化 |
| `ui/tui_app.py` | TUI 应用：Textual 框架终端 UI |
| `ui/styles.py` | 样式定义：颜色、布局、组件样式 |

## 依赖关系

- **可依赖**：`game_runtime`（读事件与状态）
- **被依赖**：`interface`（TUI 入口）

## 文档索引

| 文档 | 用途 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 稳定设计与接口契约 |
| [ROADMAP.md](./ROADMAP.md) | 开发进度与计划 |

## 快速入口

```python
from llm_werewolf.ui import ConsolePresenter, WerewolfTUI, run_tui
```
