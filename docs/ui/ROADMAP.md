# UI 开发进度

> **模块**：ui
> **状态**：active
> **最后更新**：2026-05-24

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| ConsolePresenter | ✅ Done | Rich 库美化输出、事件格式化 |
| TUI 基础框架 | ✅ Done | Textual 应用、三栏布局 |
| UI 组件 | ✅ Done | ChatPanel、GamePanel、PlayerPanel |
| 样式系统 | ✅ Done | 颜色主题、布局定义 |
| 事件缓冲 | ✅ Done | 夜间行动统一展示 |
| 多语言支持 | 🔄 In Progress | 本地化字符串 |
| 主题切换 | 📋 Planned | 亮色/暗色主题 |
| 历史记录回放 | 📋 Planned | TUI 内回放功能 |

## 已完成

- [x] ConsolePresenter 基础功能
- [x] Rich Panel/Table 美化输出
- [x] 夜间行动缓冲展示
- [x] 特殊事件处理（警长、投票、死亡）
- [x] WerewolfTUI 基础框架（Textual）
- [x] 三栏布局（GamePanel + PlayerPanel + ChatPanel）
- [x] UI 组件定义
- [x] 样式系统（颜色、布局）

## 进行中

- [ ] 多语言支持完善（Locale 集成）
- [ ] TUI 交互优化（键盘快捷键、滚动）

## 计划中

- [ ] 主题切换（亮色/暗色）
- [ ] 历史记录回放（TUI 内）
- [ ] 自定义布局配置
- [ ] 导出为 HTML/PDF

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-05-24 | 初始化 ui 三件套文档 |
| 2026-05-22 | 添加 TUI 三栏布局 |
| 2026-05-20 | 完善 ConsolePresenter 事件处理 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
