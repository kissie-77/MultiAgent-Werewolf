# Interface 开发进度

> **模块**：interface
> **状态**：active
> **最后更新**：2026-06-02

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| CLI 入口 | ✅ Done | werewolf / werewolf-api / werewolf-eval / werewolf-evidence / werewolf-vote-swing |
| 运行时装配 | ✅ Done | bootstrap、finalize_run、modes |
| 配置加载 | ✅ Done | YAML 解析 + 部分 CLI 覆盖 |
| Web API 基础 | ✅ Done | FastAPI、actions + pages 路由 |
| 控制台展示 | ✅ Done | CLI 挂载 `ui.ConsolePresenter`（TUI 已移除） |
| 人机对战 | ✅ Done | `--human_seat` 混合座位 |
| API 回放功能 | 🔄 In Progress | replay / runs 页面 API |
| CLI 12 人 LLM 对局验证 | ✅ Done | `llm-12p-doubao.yaml` + ARK 连通脚本 |
| Web 前端对接 | 📋 Planned | 与 frontend 模块对接 |

## 已完成

- [x] CLI 主入口（`werewolf <config>`、`--human_seat`、`--players`）
- [x] 运行时装配（prepare_game_roster、wire_agentscope_after_setup）
- [x] 对局结算（finalize_run → PostGame pipeline）
- [x] YAML 配置加载与解析
- [x] FastAPI 应用与 CORS
- [x] API 路由（games/start、status、post-game、pages/*）
- [x] API 服务层（game_sessions、replay、runs 等）
- [x] 控制台 Rich 展示（`ConsolePresenter`；原 Textual TUI 已移除）
- [x] 离线评测 CLI（werewolf-eval，批量 DemoAgent 场景）
- [x] 证据包 CLI（werewolf-evidence）
- [x] 投票摇摆分析 CLI（werewolf-vote-swing）
- [x] 无参数启动入口支持先选参与方式、规则模式，再选择 6-20 人总人数
- [x] 基础对局默认 6 人，警徽流对局和扩展角色对局默认 12 人
- [x] 人机混战按本局实际人数校验人类玩家座位
- [x] `badge_flow` 模式在入口配置中真正启用警长 / 警徽流
- [x] API CORS 来源改为从 `WEREWOLF_CORS_ORIGINS` 读取，并过滤空项
- [x] 默认模型配置切换为 `kimi-k2.5`，未主动配置强制思考参数

- [x] ARK 连通性脚本（`scripts/test_ark_connectivity.py`）

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
| 2026-06-02 | 文档：TUI 移除、ARK 连通验证、12p 配置、产物路径；CLI 入口新增人数选择；人机混战按人数校验座位；修正 CORS 来源解析；默认模型配置切换为 `kimi-k2.5` |
| 2026-05-23 | 修正 CLI/API 文档与实现对齐 |
| 2026-05-24 | 初始化 interface 三件套文档 |
| 2026-05-21 | 重构 CLI 运行时装配逻辑 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
