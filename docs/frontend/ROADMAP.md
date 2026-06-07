# Frontend 开发进度

> **模块**：frontend
> **状态**：draft
> **最后更新**：2026-06-07

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| Express + Three.js 原型 | ✅ Done | 本地 demo（port 3000） |
| FastAPI 对接（直连 + 解信封） | ✅ Done | Vite 代理 + 废弃 mock |
| 实时观战 M1/M2/M2b | ✅ Done | SSE god 流 + gameReducer + 信念/票型 + 结算/复盘 |
| 日志观战（无 session） | ✅ Done | status 分流 + replay 时间线回放 + 历史对局下拉 |
| 供应商设置 UI | ✅ Done | `GET /settings/providers` + 动态 env 字段 |
| 内容页接后端（B 档：Runs/Models/Share） | ✅ Done | mapper 层吸收契约接缝 |
| M3 人机对战（座位视图 + 真人输入） | ✅ Done | `HumanInputPanel` + `humanInput.ts` + 座位令牌；真机 2 局打通 |
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

- [ ] 日志回放模式下 InsightDock 信念/票型（当前仅 live SSE 有数据）
- [ ] `gameReducer` 相位映射补全（`first_night` 等）
- [ ] 3D 对局 UI 与引擎 snapshot 字段映射

## 计划中

- [ ] 14 页路由与页面 API 对齐
- [ ] 复盘 / PostGame 产物展示
- [ ] 生产构建与部署方案

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-06-07 | 日志观战、run 元数据、供应商设置、战绩/分享人数兜底；详见 [前端联调问题修复记录](../reports/前端联调问题修复记录-2026-06-07.md) |
| 2026-06-06 | B 档内容页接后端 + M3 人机对战座位输入 + 结算页/立绘修复；详见 [前后端打通与人机对战报告](../reports/前后端打通与人机对战-2026-06-06.md) |
| 2026-06-05 | 前端联调：Router + Vite 代理 + SpectatePanel + 6 页 API 对接 |
| 2026-05-23 | 初始化 DESIGN / ROADMAP，消除 README 死链 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
