# UI 开发进度

> **模块**：ui
> **状态**：active
> **最后更新**：2026-06-02

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| ConsolePresenter | ✅ Done | Rich 输出、夜间缓冲、投票表格 |
| Textual TUI | ⏸ Removed | `WerewolfTUI` / `run_tui` 已删除 |
| 多语言 Locale | 🔄 In Progress | 与 `game_runtime.locale` 集成 |
| Web 观战 UI | 📋 Planned | 见 `frontend` 模块 |

## 已完成

- [x] ConsolePresenter 基础功能
- [x] Rich Panel/Table 美化输出
- [x] 夜间行动缓冲展示
- [x] 特殊事件处理（警长、投票、死亡）

## 进行中

- [ ] Locale 字符串覆盖完善

## 计划中

- [ ] 控制台输出级别/verbosity 配置

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-06-02 | 文档对齐：TUI 已移除，仅保留 ConsolePresenter |
| 2026-05-24 | 初始化 ui 三件套 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Removed`
