# Interface 开发进度

> **模块**：interface
> **状态**：active
> **最后更新**：2026-06-07

## 模块目录结构

```
interface/
├── __init__.py
├── api/                    # FastAPI 应用
│   ├── app.py              # 应用入口 + main()
│   ├── deps.py             # 依赖注入
│   ├── models/             # Pydantic 请求/响应模型
│   ├── routes/             # 路由处理器（actions / pages / legacy）
│   └── services/           # 业务逻辑层
└── cli/                    # CLI 入口与运行时装配
    ├── __init__.py          # entry / main 入口
    ├── entry.py             # werewolf 命令主入口
    ├── eval.py              # werewolf-eval（离线批量评测）
    ├── evidence.py          # werewolf-evidence（证据包）
    ├── evolution.py         # prompt 进化 CLI
    ├── vote_swing.py        # werewolf-vote-swing（投票摇摆分析）
    ├── watch.py             # werewolf-watch（告警扫描）
    └── runtime/             # 对局装配核心
        ├── bootstrap.py     # prepare_game_roster / create_information_hub
        ├── finalize_run.py  # 对局结算 + PostGame pipeline
        ├── modes.py         # 游戏模式与配置路径解析
        ├── overrides.py     # CLI 座位覆盖
        ├── player_count.py  # 动态人数调整
        └── startup_menu.py  # 无参数交互式启动菜单
```

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| CLI 入口 | ✅ Done | werewolf / werewolf-api / werewolf-eval / werewolf-evidence / werewolf-vote-swing / **werewolf-watch** |
| 运行时装配 | ✅ Done | bootstrap、finalize_run、modes、**observability log handler** |
| 目录重组 | ✅ Done | 删除 10 个根目录 shim，所有模块归入 `cli/` 和 `cli/runtime/` |
| 配置加载 | ✅ Done | YAML 解析 + 部分 CLI 覆盖 |
| Web API 基础 | ✅ Done | FastAPI、actions + pages 路由 |
| 控制台展示 | ✅ Done | CLI 挂载 `ui.ConsolePresenter`（TUI 已移除） |
| 人机对战 | ✅ Done | `--human_seat` 混合座位 |
| API 回放功能 | ✅ Done | replay / runs 页面 API（`replay.py`：belief_snapshots、wolf_camp_snapshots、heatmap、timeline、MVP；`runs.py`：list/paginate/detail） |
| 标准板子 YAML（4/6/8/12/16） | ✅ Done | `standard-*p.yaml`，默认豆包 |
| 供应商 env 模板 | ✅ Done | 8 家 · [PROVIDERS.md](./PROVIDERS.md) |
| 设置 API（浏览器写 `.env`） | ✅ Done | `GET/POST /settings/api-keys` + `GET /settings/providers` |
| Web 人机 + 观战 SSE | ✅ Done | 座位 token、输入 reject_code、分享 `/share/{id}` |
| 日志观战 / run 元数据 | ✅ Done | SSE 快照补 roster；`replay_only`；`effective_player_count` + `_load_run_roster`（`f1f655d`） |
| 同台多模型（按座 provider） | 📋 Planned | Provider Registry 开局解析 |

## 已完成

- [x] CLI 主入口（`werewolf <config>`、`--human_seat`、`--players`）
- [x] 运行时装配（prepare_game_roster、wire_agentscope_after_setup）
- [x] 对局结算（finalize_run → PostGame pipeline + **告警 dispatch**）
- [x] API `GET /ready`、会话 `post_game_status` / `alert_count`
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
- [x] 目录重组：删除 10 个根目录 backward-compat shim 文件，所有 CLI 模块统一归入 `cli/` 子目录；`watch_cli.py` 迁移至 `cli/watch.py`；17 处外部 import 同步更新

## 进行中

- [ ] 信念矩阵日志聚合 API（前端目前从 replay 时间线自行扫描 `belief_snapshot`）
- [ ] API 文档自动生成（OpenAPI/Swagger）

## 计划中

- [ ] Web 前端对接（与 frontend 模块协作）
- [ ] 多房间支持（并发多局游戏）
- [x] 观战模式（旁观者视角：SSE live + 磁盘日志回放）
- [ ] 对局录制与回放增强

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-06-09 | 代码审核：API 回放功能（replay/runs）已完整实现，标记为 Done；信念矩阵日志聚合 API 已从 replay 消费，标记为 Done |
| 2026-06-07 | 日志观战：`replay_only`、run 元数据推断、providers API、SSE roster 回退；`f1f655d`：`effective_player_count`、god_roster 容错、分享/模型页人数 |
| 2026-06-05 | 目录重组：删除 10 个根目录 shim，`watch_cli.py→cli/watch.py`，17 处 import + pyproject.toml 同步更新 |
| 2026-06-02 | 人机混战：显式配置优先级、极简人类输入提示、提交后等待提示 |
| 2026-06-02 | 文档：TUI 移除、ARK 连通验证、12p 配置、产物路径；CLI 入口新增人数选择；人机混战按人数校验座位；修正 CORS 来源解析；默认模型配置切换为 `kimi-k2.5` |
| 2026-05-23 | 修正 CLI/API 文档与实现对齐 |
| 2026-05-24 | 初始化 interface 三件套文档 |
| 2026-05-21 | 重构 CLI 运行时装配逻辑 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
