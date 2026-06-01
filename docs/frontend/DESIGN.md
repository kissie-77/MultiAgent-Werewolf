# Frontend 设计

> **模块**：frontend
> **状态**：draft
> **最后更新**：2026-05-23
> **关联代码**：`frontend/`

## 1. 目标

提供浏览器端 3D 观战与交互界面（React 19 + Three.js），对接 `interface` FastAPI（`:8000`），逐步替代当前 Express + Gemini 原型（`:3000`）。

## 2. 范围

### 做

- 游戏状态可视化、事件流、发言与技能 UI
- 调用 `/api/v1/games/start`、`/games/{run_id}/status` 等
- 复盘页对接 `/api/v1/replay/{run_id}`、`POST /runs/{run_id}/post-game`

### 不做

- 不实现游戏规则（见 `game_runtime`）
- 不托管 FastAPI（见 `interface`）

## 3. 当前原型 vs 目标

| 项 | 当前 `frontend/` | 目标 |
|----|------------------|------|
| 运行时 | Express + Vite dev（`server.ts`） | 静态构建 + FastAPI 或独立静态托管 |
| 后端 | Gemini 直连原型 | `werewolf-api` REST |
| 页面 | 单页 Demo | 14 页站点（见 [前端规划.md](../archive/前端规划.md)） |

## 4. 依赖与边界

- `frontend → interface/api`（HTTP）
- 详细页面与 API 映射见 [前端规划.md](../archive/前端规划.md)

## 5. 相关文档

- 进度：[ROADMAP.md](./ROADMAP.md)
- 页面规划：[../archive/前端规划.md](../archive/前端规划.md)
