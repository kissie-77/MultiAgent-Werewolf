# UI 设计

> **模块**：ui
> **状态**：active
> **最后更新**：2026-06-02
> **关联代码**：`src/llm_werewolf/ui/`

## 1. 目标

将游戏事件和状态以可读方式输出到终端（Rich 美化）。**只读**事件与状态，不修改 `GameState`。

## 2. 范围

### 做

- `ConsolePresenter`：格式化 `Event` 输出
- 夜间行动缓冲、投票表格、死亡/警长等特殊展示
- 与 `game_runtime.locale.Locale` 配合的多语言字符串

### 不做

- 不修改游戏状态（归 `game_runtime`）
- 不执行 Agent 决策（归 `agent_team`）
- 不提供 Web 页面（归 `frontend`）
- **不提供 TUI**（已移除；见 `ui/__init__.py`）

## 3. 核心架构

```text
GameEngine.on_event
    → interface/cli/entry 挂载 ConsolePresenter
    → present_event(event)
    → Rich Panel / Table 输出
```

## 4. ConsolePresenter

| 事件类型 | 处理方式 |
|----------|----------|
| 夜间行动 | 缓冲后统一展示 |
| 白天发言 | 实时展示 |
| 投票结果 | 表格展示 |
| 死亡信息 | 醒目提示 |
| 警长选举 | 专区展示 |

人机混战只挂载单个人类视角时，`ConsolePresenter` 必须按 `visible_to` 过滤事件：狼人夜聊、信念矩阵等上帝视角内容不展示给无权限的人类玩家。夜间公开死亡结果在人类闭眼期间先缓冲，等天亮或进入非夜间阶段再展示；人类自己的私密夜间信息则允许实时展示。

## 5. 接口

| 入口 | 说明 |
|------|------|
| `ConsolePresenter(locale)` | 创建展示器 |
| `presenter.present_event(event)` | 展示单个事件 |

## 6. 依赖与边界

- `ui → game_runtime`
- `ui` 不依赖 `agent_team`、`evaluation`、`strategy`
- `interface` CLI 依赖 `ui.console_presenter`

## 7. 相关文档

- 进度：[ROADMAP.md](./ROADMAP.md)
- CLI 入口：[../interface/DESIGN.md](../interface/DESIGN.md)
