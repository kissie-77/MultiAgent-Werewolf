# Frontend 开发进度

> **模块**：frontend
> **状态**：draft
> **最后更新**：2026-06-09

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| Express + Three.js 原型 | ✅ Done | 本地 demo（port 3000） |
| FastAPI 对接（直连 + 解信封） | ✅ Done | Vite 代理 + 废弃 mock |
| 实时观战 M1/M2/M2b | ✅ Done | SSE god 流 + gameReducer + 信念/票型 + 结算/复盘 |
| 内容页接后端（B 档：Runs/Models/Share） | ✅ Done | mapper 层吸收契约接缝 |
| M3 人机对战（座位视图 + 真人输入） | ✅ Done | `HumanInputPanel` + `humanInput.ts` + 座位令牌；真机 2 局打通 |
| Leaderboard 可视化 | ✅ Done | `ModelsPage` 排行表/雷达对比/模型详情（依赖 evaluation 数据） |
| 复盘 / PostGame 产物展示 | ✅ Done | `ReplayPage` 四标签 + `GameOverPanel` 轮询就绪 + `MvpTab` |
| 音效系统集成 | ✅ Done | `SoundManager` 双总线 + 36/40 音频资产就位（BGM 5 段待生成） |

## 已完成

- [x] React 19 + Three.js 基础组件（ThreeCanvas、GameSetup 等）
- [x] Zustand 状态、Vite 构建链
- [x] Express 开发服务器原型（`npm run dev:mock`）
- [x] React Router 多页路由（17 个页面组件，19 条路由定义）
- [x] Vite dev 代理 `/api` → `werewolf-api:8000`；`make dev-web`
- [x] SpectatePanel：POST `/games/start` + 轮询 `/games/{run_id}/status`
- [x] 内容页联调：features / about / how-to-play / strategy / roles / models / runs
- [x] 智脑页（Models）：`ModelsPage` 排行表/排序 + `ModelComparePage` 对比分析 + `ModelDetailPage` 详细参数 + 空列表态
- [x] 聊天日志身份显示：`SpeechConsole` 内 `isRoleRevealed` 算法自动适配上帝/座位视角，无需手动开关
- [x] 3D 对局 UI 与 `snapshot` / `liveCue.thinking` 字段映射：`ThreeCanvas` 读取 `liveCue.thinking.seat`，`SpeakerSeat` 展示思考态青色光环
- [x] 复盘 / PostGame 展示：`ReplayPage`（Timeline/Belief/Vote Swing/MVP）、`GameOverPanel` 轮询就绪后展示 MVP + 全板 + 深度复盘链接
- [x] 音效系统：`SoundManager`（双 GainNode 总线 + unlock + playSfx/playBgm + 持久化）、`castMap` 覆盖 15 种 EffectType、store SSE 钩子全量派发
- [x] 音频资产：36/40 个文件已归位 `frontend/public/audio/{skill,event,ui}/`

## 进行中

- [ ] BGM 生成（5 段：lobby / amb_day / amb_night / tension / settlement）—— 外部 AI 生成，当前 `frontend/public/audio/bgm/` 为空

## 计划中

- [ ] 生产构建与部署方案（`vite.config.ts` 已有 code-split 配置，缺 Dockerfile / nginx.conf）

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-06-09 | 文档状态审核：将 Models、复盘、3D 映射、音效等多项由计划/进行中修正为已完成；还原被误删的 docs/frontend 目录 |
| 2026-06-06 | 人机座位视图修复：后端脱敏名单（6 卡牌 + 本人徽标 + 他人秘匿）+ reducer 事件时间线/公开发言气泡 + 全 22 角色立绘（material/tarot 部署 PascalCase + 映射）；真机回归通过；spec/plan 见 `docs/superpowers/{specs,plans}/2026-06-06-human-seat-view-and-role-art*` |
| 2026-06-06 | B 档内容页接后端 + M3 人机对战座位输入 + 结算页/立绘修复；详见 [前后端打通与人机对战报告](../reports/前后端打通与人机对战-2026-06-06.md) |
| 2026-06-05 | 前端联调：Router + Vite 代理 + SpectatePanel + 6 页 API 对接 |
| 2026-05-23 | 初始化 DESIGN / ROADMAP，消除 README 死链 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
