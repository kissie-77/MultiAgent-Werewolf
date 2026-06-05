# Frontend 开发进度

> **模块**：frontend
> **状态**：draft
> **最后更新**：2026-06-05

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| Express + Three.js 原型 | ✅ Done | 本地 demo（port 3000） |
| FastAPI 对接 | 🔄 In Progress | Vite 代理 + 观战 SpectatePanel |
| 14 页站点 | 🔄 In Progress | 路由 + 6 页已接 `/api/v1/pages/*` |
| Leaderboard 可视化 | 📋 Planned | 依赖 evaluation |

## 已完成

- [x] React 19 + Three.js 基础组件（ThreeCanvas、GameSetup 等）
- [x] Zustand 状态、Vite 构建链
- [x] Express 开发服务器原型（`npm run dev:mock`）
- [x] React Router 多页路由（`/` `/game` `/features` 等）
- [x] Vite dev 代理 `/api` → `werewolf-api:8000`；`make dev-web`
- [x] SpectatePanel：POST `/games/start` + 轮询 `/games/{run_id}/status`
- [x] 内容页联调：features / about / how-to-play / strategy / roles

## 进行中

- [ ] 3D 对局 UI 与引擎 snapshot 字段映射
- [ ] 复盘页 `/replay/:runId` 对接

## 计划中

- [ ] 14 页路由与页面 API 对齐
- [ ] 复盘 / PostGame 产物展示
- [ ] 生产构建与部署方案

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-06-05 | 前端联调：Router + Vite 代理 + SpectatePanel + 6 页 API 对接 |
| 2026-05-23 | 初始化 DESIGN / ROADMAP，消除 README 死链 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
