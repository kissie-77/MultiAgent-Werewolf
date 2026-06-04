# Interface 开发进度

> **模块**：interface
> **状态**：active
> **最后更新**：2026-06-04

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
| 引擎驱动观战 API（/state·/stream·/control）| ✅ Done | 保活引擎 + step 泵 + 控制闸 + SSE + 真机联调 |

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
- [x] 显式 `config` 不再被 CLI 默认 `badge_flow` 覆盖；只有显式规则或 `--badge_flow` 才开启警长
- [x] 人机混战人类输入提示收敛为必要行动信息，不展示 Agent observation / schema / 策略提示

- [x] ARK 连通性脚本（`scripts/test_ark_connectivity.py`）
- [x] 引擎驱动观战：保活引擎 + `engine.step()` 逐阶段泵 + 控制闸（暂停/继续/单步/变速）
- [x] `GET /games/{id}/state`（权威实时 + 读盘兜底）、SSE `GET /games/{id}/stream`（`Last-Event-ID` 续传）、`POST /games/{id}/control`
- [x] `on_event` 一源两写（`events.jsonl` + 内存 `EventHub`）；真 DeepSeek 端到端联调通过

## 进行中

- [ ] 对局回放 API 完善
- [ ] API 文档自动生成（OpenAPI/Swagger）

## 计划中

- [ ] Web 前端对接（与 frontend 模块协作）
- [ ] 多房间支持（并发多局游戏）
- [ ] 对局录制与回放增强

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-06-04 | 引擎驱动观战 API：保活引擎 + step 泵 + 控制闸 + `GET /state` + SSE `GET /stream`（Last-Event-ID 续传）+ `POST /control`；真 DeepSeek 端到端联调通过（详见 DESIGN §11） |
| 2026-06-02 | 人机混战：显式配置优先级、极简人类输入提示、提交后等待提示 |
| 2026-06-02 | 文档：TUI 移除、ARK 连通验证、12p 配置、产物路径；CLI 入口新增人数选择；人机混战按人数校验座位；修正 CORS 来源解析；默认模型配置切换为 `kimi-k2.5` |
| 2026-05-23 | 修正 CLI/API 文档与实现对齐 |
| 2026-05-24 | 初始化 interface 三件套文档 |
| 2026-05-21 | 重构 CLI 运行时装配逻辑 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
