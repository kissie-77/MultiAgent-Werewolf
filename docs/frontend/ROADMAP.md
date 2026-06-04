# Frontend 开发进度

> **模块**：frontend
> **状态**：draft
> **最后更新**：2026-06-04

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| Express + Three.js 原型 | ✅ Done | 本地 demo（port 3000） |
| FastAPI 对接 | 🔄 In Progress | 观战 poll start/status |
| 14 页站点 | 📋 Planned | 见前端规划.md |
| Leaderboard 可视化 | 📋 Planned | 依赖 evaluation |
| 引擎驱动观战前端 | ✅ Done | EventSource /stream + 按 phase 驱动 + 控制条 |

## 已完成

- [x] React 19 + Three.js 基础组件（ThreeCanvas、GameSetup 等）
- [x] Zustand 状态、Vite 构建链
- [x] Express 开发服务器原型
- [x] 引擎驱动观战：`EventSource` 订阅 `/stream`（取代轮询）、按 `GamePhase` 驱动 UI、控制条（暂停/单步/变速）调 `/control`、结构化技能/投票/死亡渲染 + 子阶段高亮；删假倒计时与双结束信号

## 进行中

- [ ] 切换 API base 至 `werewolf-api`（:8000）
- [ ] 观战模式：POST start + GET status 轮询

## 计划中

- [ ] 14 页路由与页面 API 对齐
- [ ] 复盘 / PostGame 产物展示
- [ ] 生产构建与部署方案

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-06-04 | 引擎驱动观战前端：SSE 传输 + 按 phase 驱动 + 控制条 + 结构化渲染（后端契约见 interface/DESIGN.md §11） |
| 2026-05-23 | 初始化 DESIGN / ROADMAP，消除 README 死链 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
