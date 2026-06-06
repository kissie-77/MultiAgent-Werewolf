# UI 模块

> **模块**：ui
> **状态**：active
> **最后更新**：2026-06-02
> **关联代码**：`src/llm_werewolf/ui/`
> **关联测试**：`tests/ui/`

## 职责

展示层：**ConsolePresenter**（Rich 控制台事件格式化）。只读事件与状态，不修改游戏逻辑。

> **说明**：历史上的 Textual TUI（`WerewolfTUI` / `run_tui`）已移除；CLI 对局通过 `interface` 的 `werewolf` 命令 + `ConsolePresenter` 输出。Web 观战见 `frontend`。

## 不负责

- 游戏规则与引擎（见 `game_runtime`）
- Agent 决策与执行（见 `agent_team`）
- CLI/API 入口与装配（见 `interface`）
- Web 前端页面（见 `frontend`）

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `ui/console_presenter.py` | 控制台展示器：Rich Panel/Table、夜间行动缓冲 |
| `ui/components/` | 预留组件包（当前无独立 panel 实现文件） |

## 依赖关系

- **可依赖**：`game_runtime`（读事件与状态）
- **被依赖**：`interface`（CLI 对局挂载 `presenter.present_event`）

## 文档索引

| 文档 | 用途 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 稳定设计与接口契约 |
| [ROADMAP.md](./ROADMAP.md) | 开发进度与计划 |

## 快速入口

```python
from llm_werewolf.ui.console_presenter import ConsolePresenter
from llm_werewolf.game_runtime.i18n.locale import Locale

presenter = ConsolePresenter(Locale("zh-CN"))
presenter.present_event(event)
```
