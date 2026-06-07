# Frontend 设计

> **模块**：frontend
> **状态**：draft
> **最后更新**：2026-06-07
> **关联代码**：`frontend/`

## 1. 目标

提供浏览器端 3D 观战与交互界面（React 19 + Three.js），对接 `interface` FastAPI（`:8000`），逐步替代当前 Express + Gemini 原型（`:3000`）。

## 2. 范围

### 做

- 游戏状态可视化、事件流、发言与技能 UI
- 调用 `/api/v1/games/start`、`/games/{run_id}/status`、`/games/{run_id}/stream`（live）等
- **日志观战**：已结束或无 session 时，`connectSpectate` 走 `GET /pages/replay` 时间线 + `spectateLog` 折叠进 `gameReducer`（不依赖内存 broadcaster）
- **可选历史对局**：`GET /runs?replay_only=true` 供开局页下拉选择
- 复盘页对接 `/api/v1/pages/replay`、`POST /runs/{run_id}/post-game`

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

## 5. API 客户端健壮性（2026-06-05）

- 所有 `store` 请求经 `fetchWithRetry`（默认 2 次重试、递增退避）；5xx 可重试，4xx 直接返回。
- `fetchState` 失败时：若 `phase` 已在局中（非 `START_SCREEN`），**保留上一状态**，避免网络抖动把用户踢回开始页。
- 夜间技能附加字段使用 `NightSkillAdditional`，不再使用 `any`。

## 6. 观战数据流（2026-06-07）

```
用户打开 /game?run_id=...
    → GET /games/{run_id}/status
    → status=running 且未结束 → EventSource /games/{id}/stream?view=god
    → 否则 has_replay → GET /pages/replay?view=god → hydrateStateFromLogEvents
    → 无日志 → spectateError + 引导至 /replay 或 /runs
```

开局页「上帝观战」除 `POST /games/start` 新开一局外，可从 `replay_only` 列表载入已有 `events.jsonl`。

## 7. 相关文档

- 进度：[ROADMAP.md](./ROADMAP.md)
- 联调修复记录：[../reports/前端联调问题修复记录-2026-06-07.md](../reports/前端联调问题修复记录-2026-06-07.md)
- 页面规划：[../archive/前端规划.md](../archive/前端规划.md)
