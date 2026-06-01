# Interface 开发进度

> **模块**：interface
> **状态**：active
> **最后更新**：2026-05-23

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| CLI 入口 | ✅ Done | werewolf / werewolf-tui / werewolf-eval |
| 运行时装配 | ✅ Done | bootstrap、finalize_run、modes |
| 配置加载 | ✅ Done | YAML 解析 + 部分 CLI 覆盖 |
| Web API 基础 | ✅ Done | FastAPI、actions + pages 路由 |
| TUI 展示 | ✅ Done | 终端实时对局展示 |
| 人机对战 | ✅ Done | `--human_seat` 混合座位 |
| API 回放功能 | 🔄 In Progress | replay / runs 页面 API |
| Web 前端对接 | 📋 Planned | 与 frontend 模块对接 |

## 已完成

- [x] CLI 主入口（`werewolf <config>`、`--human_seat`、`--players`）
- [x] 运行时装配（prepare_game_roster、wire_agentscope_after_setup）
- [x] 对局结算（finalize_run → PostGame pipeline）
- [x] YAML 配置加载与解析
- [x] FastAPI 应用与 CORS
- [x] API 路由（games/start、status、post-game、pages/*）
- [x] API 服务层（game_sessions、replay、runs 等）
- [x] TUI 实时对局展示（werewolf-tui）
- [x] 离线评测 CLI（werewolf-eval，批量 DemoAgent 场景）
- [x] 投票摇摆分析 CLI（werewolf-vote-swing）

## 进行中

- [ ] 对局回放 API 完善
- [ ] API 文档自动生成（OpenAPI/Swagger）
- [ ] 游戏状态实时推送（WebSocket/SSE）

## 计划中

- [ ] Web 前端对接（与 frontend 模块协作）
- [ ] 多房间支持（并发多局游戏）
- [ ] 观战模式（旁观者视角）
- [ ] 对局录制与回放增强

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-05-23 | 修正 CLI/API 文档与实现对齐 |
| 2026-05-24 | 初始化 interface 三件套文档 |
| 2026-05-22 | 添加 TUI 实时展示功能 |
| 2026-05-21 | 重构 CLI 运行时装配逻辑 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
