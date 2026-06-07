# Frontend 模块

> **模块**：frontend
> **状态**：draft
> **最后更新**：2026-06-07
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
| `frontend/src/components/AppRouter.tsx` | 路由与布局 |
| `frontend/src/pages/GameApp.tsx` | 全屏对局页 |
| `frontend/src/store.ts` | Zustand 状态（SSE 观战 / 人机输入） |
| `frontend/src/api/client.ts` | API 客户端与 `unwrap` |
| `frontend/src/lib/*` | 页面映射、gameReducer、配置 |
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
| [DEV.md](./DEV.md) | 本地开发、env、代理、排错 |
| [../../CONTRIBUTING.md](../../CONTRIBUTING.md) | 配置单一真源与提交约定 |
| [DESIGN.md](./DESIGN.md) | 稳定设计与接口契约 |
| [ROADMAP.md](./ROADMAP.md) | 开发进度与计划 |

## 快速入口

见 [DEV.md](./DEV.md) 与仓库根 [README.md](../../README.md)（§本地全栈开发）。
