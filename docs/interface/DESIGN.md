# Interface 设计

> **模块**：interface
> **状态**：active
> **最后更新**：2026-06-04
> **关联代码**：`src/llm_werewolf/interface/`

## 1. 目标

提供项目的装配层与入口：将各模块组装成可运行的游戏，支持 CLI 与 Web API。负责配置加载、模式选择、跨板块装配、对局结算。

> **说明**：独立 `werewolf-tui` 已移除；CLI 对局通过 `ConsolePresenter`（`ui`）输出 Rich 控制台。

## 2. 范围

### 做

- 解析 YAML 配置文件，创建玩家和角色
- 装配 GameEngine、Agent、InformationHub
- 提供 CLI 入口启动对局（Rich 控制台展示）
- 提供 Web API 服务（FastAPI）
- 触发 PostGame 评测
- 处理对局结算与产物写入

### 不做

- 不定义游戏规则（归 `game_runtime`）
- 不执行 Agent 决策（归 `agent_team`）
- 不定义 Prompt 策略（归 `strategy`）
- 不渲染 Web 页面（归 `frontend`）

## 3. 核心流程

### 3.1 CLI 启动流程

```
无参数启动：选择参与方式、规则模式、人数
    → 加载 YAML 配置
    → prepare_game_roster()：创建玩家、角色、游戏配置
    → GameEngine.setup_game()：初始化游戏状态
    → wire_agentscope_after_setup()：绑定 AgentScope Prompt
    → engine.run_game()：运行对局
    → finalize_run()：结算、写入产物
```

无参数运行 `uv run werewolf` 时，CLI 入口负责收集本局运行配置，但不直接决定角色分配细节。

启动顺序为：

1. 选择参与方式：全 Agent 对局或人机混战。
2. 选择规则模式：基础对局、警徽流对局或扩展角色对局。
3. 选择本局总人数，范围为 6-20。
4. 根据人数生成玩家配置，并交给 `game_runtime` 的人数预设能力分配角色。

默认人数策略：

| 规则模式 | 默认人数 |
|----------|----------|
| 基础对局 | 6 |
| 警徽流对局 | 12 |
| 扩展角色对局 | 12 |

人机混战中，人类玩家座位必须按本局实际人数校验。CLI 可以展示人类玩家相关 UI，但不把“人类玩家 / AI / model / backend / demo”等运行身份信息注入 Agent 决策上下文。

显式传入 `config` 时，配置文件优先于规则模式默认值：如果没有同时传入 `rules=badge_flow` 或 `--badge_flow`，CLI 不会因为内部默认规则自动开启警长 / 警徽流。无参数启动仍按菜单选择的规则模式决定是否开启警长。

### 3.2 Web API 流程

```
FastAPI 启动（werewolf-api）
    → POST /api/v1/games/start：启动游戏
    → GET /api/v1/games/{run_id}/status：轮询状态
    → GET /api/v1/replay/{run_id}：复盘页数据
    → POST /api/v1/runs/{run_id}/post-game：触发或重跑 PostGame
```

## 4. 关键概念

| 概念 | 说明 |
|------|------|
| Bootstrap | 引导函数：创建玩家、绑定角色、装配 AgentScope |
| Modes | 游戏模式：LLM 对局、人机对战、演示模式 |
| CLI Overrides | CLI 参数覆盖：超时、并发等运行时配置 |
| Finalize Run | 对局结算：写入产物、生成复盘 |
| InformationHub | 信息中枢：Agent 之间的消息传递 |
| API Services | API 服务层：游戏会话、配置解析、回放 |
| API Routes | API 路由层：动作、页面、遗留接口 |

## 5. 游戏模式

| 模式 | 说明 | 入口 |
|------|------|------|
| 纯 Agent 对局 | 全部 Agent 自动对局 | `werewolf <config.yaml>` |
| 人机混合 | 指定座位为人类玩家 | `werewolf --participation human_mixed --rules extended_roles --players 18 --human_seat 8` |
| 人数/规则覆盖 | 调整座位数或警长流 | `--players N`、`--badge_flow`、`--participation`、`--rules` |
| 离线评测 | 批量 DemoAgent 场景 | `werewolf-eval` |
| 证据包 / 投票摇摆 | PostGame 产物分析 | `werewolf-evidence`、`werewolf-vote-swing` |

## 6. 配置系统

### 6.1 YAML 配置结构

```yaml
language: zh-CN
agent_backend: agentscope
default_plan: complicated
prompt_version: latest   # 可选；默认每身份用 prompts/roles/<role>/ 下最新版本

# 可选：按身份 pin 版本
# role_versions:
#   prompt_versions:
#     wolf: v2
#   skill_versions:
#     wolf: v2

plan_assignment:
  enabled: true
  mode: role_random      # role_cycle / role_random
  seed: 20260602         # 可选；用于 A/B 复现实验
  role_plans:
    wolf:
      - wolf_conservative
      - wolf_aggressive
      - wolf_skeptical
      - wolf_coordinator

players:
  - name: 玩家1
    model: ep-xxx
    base_url: https://...
    api_key_env: ARK_API_KEY
    # plan: wolf_aggressive  # 可选；手写 plan 优先于自动分流
  # ...

# 可选覆盖
day_timeout: 120
vote_timeout: 60
night_timeout: 90
vote_intention_concurrency: 4
```

### 6.2 CLI 参数覆盖

当前 `werewolf` CLI（`interface/cli/entry.py`）支持的运行时参数：

- `config`：YAML 配置文件路径（位置参数）
- `--participation`：参与方式，如 `all_agent`
- `--rules`：规则模式，如 `basic`、`badge_flow`
- `--players`：覆盖总座位数（6–20）
- `--human_seat`：人类玩家 1-based 座位，逗号分隔多个
- `--badge_flow`：开启警长 / 警徽流

超时、投票意向并发等主要在 **YAML** 中配置（如 `day_timeout`、`vote_timeout`、`vote_intention_concurrency`），由 `prepare_game_roster` 注入 `GameConfig`。

`plan_assignment` 用于角色分配后的自动风格分流。未手写 `plan` 的玩家会按真实角色获得角色专属计划；手写 `players[].plan` 的玩家保持手动指定，便于 A/B 验证。

人机混战的人类输入提示只展示必要信息：身份、当前阶段、可选目标、女巫刀口等自己应看到的行动事实。Agent observation、内部 schema、信念矩阵、策略任务说明不直接展示给人类玩家。

### 6.3 环境变量与 API 连通性

密钥不进 YAML，通过 `api_key_env` / `model_env` 引用仓库根目录 `.env`（由 `game_runtime.env.load_project_dotenv` 加载）。

| 变量 | 用途 |
|------|------|
| `VIBE_API_KEY` | VibeAPI API Key（当前 12 人 Kimi 配置使用） |
| `ARK_API_KEY` | 火山方舟 API Key（Doubao 历史/备用配置使用） |
| `ARK_EP` | 火山方舟推理接入点 ID（如 `ep-20260514115354-xxx`） |
| `AGENT_SERIAL_DELAY_SECONDS` | AgentScope 串行调用间隔，减轻 429 |

常用配置：`configs/llm-12p-kimi.yaml`（当前 12 人 Kimi/VibeAPI 正式局）、`configs/llm-6p-doubao.yaml`、`configs/llm-9p-doubao.yaml`、`configs/demo-6.yaml`。

改 `.env` 后先验证：

```bash
uv run werewolf configs/llm-12p-kimi.yaml        # 当前 12 人 Kimi/VibeAPI CLI 对局
uv run python scripts/test_ark_connectivity.py   # 仅用于 Doubao/ARK 配置连通性，期望 STATUS: OK
```

产物目录：`artifacts/runs/<YYYYMMDD-HHMMSS>/`；对局结束自动触发 PostGame（见 [evaluation/DESIGN.md](../evaluation/DESIGN.md)）。

### 6.4 配置边界

`interface` 可以读取环境变量与 YAML 配置，但不在运行时硬编码模型行为。

- API CORS 来源由 `WEREWOLF_CORS_ORIGINS` 提供，配置值按逗号分隔，并过滤空项。
- 模型供应商、模型名、base URL、API key、超时时间等参数由配置文件提供。
- CLI 入口只选择对局模式、人数与人类玩家座位，不负责 Prompt 内容生成。

## 7. API 设计

### 7.1 主要路由

前缀均为 `/api/v1`。完整索引见 `GET /api/v1/pages` 或 `interface/api/app.py` 的 `PAGE_ROUTE_MAP`。

**动作 / 对局**

| 路由 | 方法 | 说明 |
|------|------|------|
| `/games/modes` | GET | 启动模式列表 |
| `/games/start` | POST | 启动游戏 |
| `/games/{run_id}/status` | GET | 轮询对局状态 |
| `/games/{run_id}/cancel` | POST | 取消对局 |
| `/games/{run_id}/state` | GET | 权威实时状态（引擎驱动观战，见 §11） |
| `/games/{run_id}/stream` | GET | SSE 事件流，`Last-Event-ID` 续传（见 §11） |
| `/games/{run_id}/control` | POST | 暂停/继续/单步/变速（见 §11） |
| `/runs/{run_id}/post-game` | POST | 触发或重跑 PostGame |
| `/runs` | GET | 对局列表（legacy page API） |
| `/runs/{run_id}` | GET | 对局详情 |
| `/replay/{run_id}` | GET | 复盘页数据 |
| `/actions/spec` | GET | 动作契约说明 |
| `/models/compare` | POST | 模型对比 |

**页面数据（供 frontend 消费）**

| 路由 | 方法 | 说明 |
|------|------|------|
| `/pages/home` | GET | 首页 |
| `/pages/game` | GET | 对局页 |
| `/pages/replay` | GET | 复盘页（query: `run_id`） |
| `/pages/roles` | GET | 角色列表 |
| `/pages/roles/{role_key}` | GET | 角色详情 |
| `/pages/models` | GET | 模型列表 |

### 7.2 服务层

API 服务层负责业务逻辑：

- `game_sessions.py`：游戏会话管理
- `config_resolve.py`：配置解析
- `roster_customize.py`：阵容定制
- `start_modes.py`：启动模式
- `replay.py`：对局回放
- `runs.py`：对局管理
- `board.py`：游戏面板
- `content.py`：内容服务
- `catalog.py`：角色目录

## 8. 装配流程

### 8.1 prepare_game_roster

```python
agents, roles, game_config = prepare_game_roster(players_config)
```

- 从 YAML 配置创建玩家列表
- 创建角色实例（洗牌后分配）
- 生成游戏配置（人数、超时等）

### 8.2 wire_agentscope_after_setup

```python
wire_agentscope_after_setup(engine, players_config)
```

- 在 GameEngine.setup_game() 之后调用
- 为各玩家配置 AgentScope 系统 prompt
- 创建 ReAct Agent 实例

### 8.3 finalize_run

```python
await finalize_run(
    engine,
    run_dir,
    *,
    game_result_text=None,
    config_path=None,
    role_version_manifest=players_config.role_version_manifest(),
)
```

实现位于 `interface/cli/runtime/finalize_run.py`：

- `persist_run_artifacts`：写入 `events.jsonl`、`vote_intentions.jsonl`、`beliefs.jsonl` 等
- `run_post_game_pipeline`：触发 evaluation PostGame（14 步）
- **observability hook**：PostGame 后 `emit_from_post_game`；更新 `run_meta.post_game_status`、`alert_count`

### 8.4 运行时可观测挂载

对局期间（CLI `entry.py`、API `game_sessions._run_game`）：

1. `attach_run_log_handler(run_dir)` — 采集 429 / structured_invoke / agent fallback → `provider_events.jsonl`
2. 对局结束 `detach_run_log_handler()`（`finally`）

详见 [observability/DESIGN.md](../observability/DESIGN.md)。

## 9. 接口与扩展点

| 入口 | 类型 | 说明 |
|------|------|------|
| `prepare_game_roster(players_config)` | 函数 | 准备游戏阵容 |
| `wire_agentscope_after_setup(engine, config)` | 函数 | 装配 AgentScope |
| `finalize_run(engine, run_dir, ...)` | 异步函数 | 持久化产物 + PostGame + 告警 |
| `create_app()` | 函数 | 创建 FastAPI 应用（含 `/health`、`/ready`） |
| `werewolf` / `werewolf-api` / `werewolf-eval` / **`werewolf-watch`** | CLI | 见 `pyproject.toml` `[project.scripts]` |

## 10. 依赖与边界

遵循工程结构整理方案：

- `interface → game_runtime`、`agent_team`、`strategy`、`evaluation`、`ui`、**`observability`**
- `interface` 是装配层，不被其他业务模块依赖
- `interface` 可以写入 `evaluation` 产物目录

## 11. 引擎驱动观战 API（纯 LLM 观战）

> 关联代码：`interface/api/services/{game_sessions,state,view,event_hub,sse_stream}.py`、`interface/api/models/{state,view,actions}.py`、`interface/api/routes/actions.py`。引擎侧信号见 [../game_runtime/ROADMAP.md](../game_runtime/ROADMAP.md)，前端消费见 [../frontend/ROADMAP.md](../frontend/ROADMAP.md)。

### 11.1 动机：日志驱动 → 引擎驱动

旧观战为"日志驱动"：`play_game()` 一口气跑完整局，仅经 `on_event` 写入 `events.jsonl`；读接口重读日志、反推阶段/死活/胜负，引擎打完即丢、状态不可查。改造后为"引擎驱动"：保活引擎、逐阶段推进、直接上报权威状态。

### 11.2 运行模型

- `GameSession` 保活 `engine`；`_run_game` 用 `engine.step()` 逐阶段泵推进，过一道控制闸（playing/paused + 单步 + 变速）。
- 阶段间在 `next_phase()` 清空前抓取夜晚结果（`last_night`），保证不丢。
- `on_event` 一源两写：磁盘 `events.jsonl`（回放/复盘照旧）+ 内存 `EventHub`（0-based `seq`、环形缓冲、SSE 实时推送）。

### 11.3 接口契约

| 路由 | 方法 | 说明 |
|------|------|------|
| `/games/{run_id}/state` | GET | 权威实时状态：序列化活引擎；打完/被回收回落读盘 |
| `/games/{run_id}/stream` | GET (SSE) | `id:<seq>` + `event:game` + `data:<JSON>`；`Last-Event-ID` 续传，缓冲外则读盘补缺 |
| `/games/{run_id}/control` | POST | `{action: pause\|resume\|step\|speed, value?}` → `{run_id, play_state, speed, phase}` |

`/state` 关键字段：`phase`(权威 GamePhase)、`sub_phase`、`round`、`play_state`、`speed`、`current_actor_seat`、`winner`、`sheriff_seat`、`alive_count`/`dead_count`、`last_night`、`votes`、`cursor`、`players[]`。`/stream` 事件 `type ∈ {speech, skill, vote, death, phase, sub_phase, system, belief, vote_intention}`；`seq`/`/state.cursor`/`Last-Event-ID` 三者均 0-based 对齐。

### 11.4 鲁棒性

暂停在阶段边界真停引擎（不空烧 LLM）；断线由浏览器 `EventSource` 自动重连续传、`/state` 全量兜底；运行出错发终止 `system` 事件并落盘；事件分类与可见性由服务端权威给出，前端不猜。完整启动见 [README 快速入口](./README.md#快速入口)，变更记录见 [ROADMAP](./ROADMAP.md)。

## 12. 相关文档

- 进度：[ROADMAP.md](./ROADMAP.md)
- 工程结构方案：[../architecture/工程结构整理方案.md](../architecture/工程结构整理方案.md)
- 人机对战说明：[../reports/人机对战与命令行模式.md](../reports/人机对战与命令行模式.md)
- Kimi/VibeAPI 正式局配置：`configs/llm-12p-kimi.yaml`
- ARK 连通测试：`scripts/test_ark_connectivity.py`（仅用于 Doubao/ARK 配置）
