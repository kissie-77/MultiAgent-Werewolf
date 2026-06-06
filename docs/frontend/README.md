# Frontend 模块

> **模块**：frontend
> **状态**：draft
> **最后更新**：2026-06-05
> **关联代码**：`frontend/`
> **关联测试**：`frontend/tests/`（待建立）

## 职责

Web 前端：React + Three.js 3D 展示、游戏状态可视化、实时事件流展示、用户交互界面。提供浏览器可访问的游戏体验。

## 不负责

- 游戏规则与引擎（见 `game_runtime`）
- Agent 决策与执行（见 `agent_team`）
- API 服务层（见 `interface/api`）
- 终端 UI 展示（见 `ui`）

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `frontend/src/components/` | React 组件：CardDeck、ControlPanel、GameOverPanel、GameSetup、SkillBar、SpeechConsole、ThreeCanvas、TopHeader |
| `frontend/src/App.tsx` | 主应用组件（拖拽面板；卸载时清理 window 监听器） |
| `frontend/src/store.ts` | 状态管理（Zustand）；API 经 `fetchWithRetry` |
| `frontend/src/api/retry.ts` | 带退避的 `fetch` 重试（5xx / 网络抖动） |
| `frontend/src/types.ts` | TypeScript 类型定义（含 `NightSkillAdditional`） |
| `frontend/src/index.css` | 全局样式 |
| `frontend/src/main.tsx` | 入口文件 |
| `frontend/server.ts` | Express 开发服务器 |
| `frontend/vite.config.ts` | Vite 构建配置 |

## 依赖关系

- **可依赖**：`interface/api`（Web API 接口）
- **被依赖**：无（前端展示层）

## 文档索引

| 文档 | 用途 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 稳定设计与接口契约 |
| [ROADMAP.md](./ROADMAP.md) | 开发进度与计划 |

## 快速入口

```bash
# 启动开发服务器
cd frontend && npm run dev

# 构建生产版本
cd frontend && npm run build
```
