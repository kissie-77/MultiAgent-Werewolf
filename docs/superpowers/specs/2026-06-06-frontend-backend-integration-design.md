# 前后端打通设计：实时观战 + 人机对战

- **日期**: 2026-06-06
- **状态**: 已批准（待写实现计划）
- **分支**: `feature/fe-be-integration`
- **作者**: 与用户协同 brainstorming 产出

---

## 1. 背景与问题

当前仓库的前端（React + Three.js）与 Python FastAPI 后端是**两套平行、尚未对接**的实现：

- 前端 `dev`/`start` 实际依赖 `frontend/server.ts`（Express + Google Gemini），它 **mock 了全部 `/api/v1/pages/*`** 并自带一套 **`/api/game/state|reset|action|exit`** 的有状态对局循环。
- FastAPI 后端有真实的 `/api/v1/pages/*` 与对局编排接口（`/games/start|status|cancel`、`/runs/{id}/post-game`），且后端才是「真正的引擎」：`game_runtime`（引擎/角色/规则）、`agent_team`（多 Agent + 多层记忆）、`strategy`（信念/投票/狼队）、`evaluation`（评分/复盘/自进化）。
- 三类契约不一致：① 后端返回 `ApiResponse{data}` 信封，前端 `ApiClient.get()` 不解包；② `/api/game/*` 在 FastAPI 不存在；③ 真实编排接口前端无人调用；④ 信念矩阵/投票意向在前端是 mock。

**目标**：让前端每个页面与游戏进程都由真实后端驱动，废弃 mock；打通**纯 LLM 观战**与**人机对战**，并让信念矩阵、投票意向随后端实时刷新。

## 2. 目标 / 非目标

**目标**
- 前端直连 FastAPI，统一解 `data` 信封，废弃 Express+Gemini mock。
- 纯 LLM 对战 = 观战：开局 → 实时直播（昼夜、狼队夜聊、预言家验人、女巫用药、守卫守人、警长竞选、白天发言/投票、死亡/遗言、猎人/白痴/骑士等技能、情侣/第三方夜间行动）→ 结算 → 复盘，全部由后端事件流驱动。
- 人机对战：单个人类座位（你 vs 其余全 AI），引擎在人类决策点暂停等待网页输入。
- 信念矩阵、投票意向实时同步刷新（观战 god 视角看全部；人机仅本人视角）。
- LLM API 配置（供应商/Key/模型）在前端填写。

**非目标（本期不做）**
- 多人类座位 / 联机房间（同屏多玩家）。
- 用户登录 / 账户系统（仅轻量座位令牌防替操作）。
- AI 节奏控速（确认：全速直出，不控速）。
- 旧式 stdin 人类座位（`model=="human"`）走 web —— 仍仅 CLI。

## 3. 已锁定决策（来自需求澄清）

| 维度 | 决策 |
|---|---|
| 实时传输 | **SSE**（server→client）+ **POST**（client→server 人类输入） |
| 设计范围 | 观战 + 人机**一起设计**（一份 spec，分里程碑落地） |
| LLM 密钥 | **随开局请求传原始 Key，仅本局内存使用，绝不落盘/日志** |
| 契约方向 | **废弃 Express mock**，前端直连 FastAPI，前端统一解 `data` 信封 |
| 可见性 | 观战 = **上帝视角**；人机 = **严格本人座位视角**（后端按 `Event.visible_to` 过滤） |
| 人类回合 | **默认等待手动提交**，可选回合倒计时；超时 → 安全兜底行动 |
| AI 节奏 | **全速直出，不控速** |
| LLM 配置粒度 | **全局一个供应商 + Key + 模型**，可选按座位覆盖 |
| 部署/并发 | **多局并发，按 `run_id` 隔离**；开局者持**座位令牌**，人类输入 POST 必带令牌 |
| 人类座位数 | **单人类**（你 vs 其余全 AI） |
| 人类角色 | **可指定自己角色**（休闲/测试）；其余座位随机分配 |
| 结算时机 | **立即出胜负 + 亮牌**；MVP/教练等 post-game 后台生成后轮询补充 |

## 4. 核心架构

### 4.1 三个关键机制

**① 人类暂停引擎 —— `WebHumanAgent`（await Future）**
引擎全程 `asyncio`，每个决策走 `AgentProtocol` 的 `get_response/get_structured_response`。新增 `WebHumanAgent`（实现同协议）：轮到它时向本局 `HumanInputBroker` **注册一个待办请求**（决策类型/提示/合法目标/截止时间）并 `await asyncio.Future()`，只挂起「这一个决策」，事件循环继续服务 SSE/POST。浏览器 POST 人类输入 → resolve Future → 引擎继续。**引擎主循环零改动**，复用现有 `bridge` 解析契约（`SeatChoiceDecision`/`SpeechDecision`/`WitchNightDecision`/`YesNoDecision`/`MultiSeatChoiceDecision`/`VoteIntentionDecision`/`MindStateDecision`）。
- 备选 B（`step()` 外部驱动）：人类决策在阶段内部发生，`step()` 粒度太粗，否决。
- 备选 C（单独人类对局引擎）：重复造轮子，否决。

**② SSE 事件源 —— 进程内广播队列 + `events.jsonl` 断线回放**
`engine.on_event` 是单一事件出口（`_log_event → self.on_event(event)`）。把它改为**复合**：`compose(IncrementalEventWriter(run_dir), broadcaster.publish)` —— 同时落文件 + 推到该 run 的内存广播队列。SSE 端点订阅队列（低延迟、全速）；断线重连用 `Last-Event-ID`，broadcaster 先从 `events.jsonl` 回放游标之后的事件再续流。信念矩阵/投票意向本就是带 `visible_to` 的事件（也落 `beliefs.jsonl`/`vote_intentions.jsonl`），同一条流即可带出。

**③ 可见性复用 `Event.visible_to`**
SSE 端点带 `view`：`god`（观战，发全部事件）或 `seat`（人类，仅 `visible_to is None` 或含本座位的事件）。**防作弊由后端事件过滤天然保证**；人类的 `view` 强制等于令牌绑定座位，god 视角对人类局禁用。

### 4.2 一局生命流

```
开局: POST /api/v1/games/start {
        config_id|participation+rules, player_count, badge_flow,
        llm: { provider, api_key, base_url, model, per_seat?{} },   # 原始key, 内存only
        human?: { seat, role? } | null                              # null = 纯LLM观战
      }
   → 后端注入本局内存密钥；human 非空时该座位用 WebHumanAgent
   → 返回 ApiResponse{data: StartGameResponse + player_token + stream_path}

直播: GET /api/v1/games/{run_id}/stream?view=god|seat&token=...   (SSE)
   → 首帧 snapshot 全量 + 逐条 Event；前端 reducer 渲染 3D/发言/票型/信念/弹窗

人类回合: 流中出现 awaiting_input{seat,kind,prompt,valid_targets,deadline}
   → 前端弹输入面板
   → POST /api/v1/games/{run_id}/input { token, request_id, kind, payload }
   → resolve 对应 Future（幂等：request_id 去重）
   → 可选倒计时；超时后端兜底（弃票/不用药/空发言）并推 input_timeout

结算: 终局推 game_over → 前端立即亮牌+胜负；post-game 后台跑，
      前端轮询 GET /games/{run_id}/status（has_post_game/post_game_status）补 MVP/教练

复盘: GET /api/v1/pages/replay?run_id=   （已有真实端点；前端解 data 信封接上）
```

## 5. 后端组件与改动

| # | 组件 | 文件 | 改动 |
|---|---|---|---|
| A1 | **`WebHumanAgent`** | `agent_team/agents/web_human_agent.py`（新） | 实现 `BaseAgent` + `get_response`/`get_structured_response`；`await` 本局 `HumanInputBroker.request(...)`；输出复用 bridge 契约模型。 |
| A2 | `create_agent` 分支 | `agent_team/agents/base.py` | 增 `if model == "web-human": return WebHumanAgent(...)`（与现有 `"human"`/`"demo"` 并列）。 |
| A3 | **`HumanInputBroker`** | `interface/api/services/human_input.py`（新） | 每 run 一个；`pending: dict[(run_id,seat) → PendingRequest(Future, kind, prompt, valid_targets, deadline)]`；`request()`（agent 调，挂起）/`submit(token,request_id,payload)`（HTTP 调，resolve，幂等）/`sweep_timeouts()`（兜底 resolve）。 |
| A4 | **`EventBroadcaster`** | `interface/api/services/event_stream.py`（新） | 每 run 一个 asyncio 广播；`publish(event)` → 各订阅 queue；`subscribe(view, seat)` 产出按 `Event.visible_to` 过滤后的事件 + 递增 `event_id`；`replay_from(cursor)` 读 `events.jsonl`。复用 `IncrementalEventWriter` 的序列化器。 |
| A5 | `on_event` 复合 + 协程 | `interface/api/services/game_sessions.py` | `engine.on_event = compose(IncrementalEventWriter(dir), broadcaster.publish)`；`_run_game` 起 `sweep_timeouts` 协程；human 座位绑定 `WebHumanAgent` + broker；session 持有 broker/broadcaster 引用。 |
| A6 | 放开 web 人类拦截 | `interface/api/services/game_sessions.py:_has_human_player` | web-human 座位不再 `raise`；仅旧式 stdin `"human"` 座位仍报错。 |
| A7 | 原始 key 注入 | `game_runtime/config/player_config.py` + `agent_team/agents/factory.py` | `PlayerConfig` 增 `api_key: str|None = Field(default=None, exclude=True, repr=False)`；`create_react_agent` 优先 `config.api_key`，回退 `os.getenv(config.api_key_env)`；**`launch_roster.json` 的 `model_dump` 排除 `api_key`**（连同现有 `exclude={"use_agentscope_backend"}`）。 |
| A8 | 固定人类角色 | `game_runtime/engine/base.py:setup_game` + roster 准备层 | `setup_game(..., fixed_seat_roles: dict[int,str]|None=None)`：固定座位不参与 shuffle，其余照常洗牌；角色池需校验所选角色存在且数量合法。 |
| A9 | 新 HTTP 路由 | `interface/api/routes/actions.py`（或新 `routes/stream.py`） | `GET /games/{id}/stream`（SSE）、`POST /games/{id}/input`；扩展 `POST /games/start` 请求体；返回新增 `player_token`/`stream_path`。 |

**安全（密钥）**：raw key 仅存内存 `PlayerConfig`；不写 `launch_roster.json`/`run_meta.json`/日志/事件流；不进 `repr`。`/start` 依赖部署层 HTTPS。

## 6. API 契约

所有响应保留 `ApiResponse{success,data,message}` 信封，**前端统一解包**。

### 6.1 `POST /api/v1/games/start`（扩展 `StartGameRequest`）

```jsonc
{
  "config_id": "llm-6p-deepseek",        // 或 participation+rules
  "participation": "all_agent",
  "rules": "basic",                       // basic | badge_flow | extended_roles
  "player_count": 6,                      // 6-20
  "badge_flow": false,
  "llm": {                                // 新增；原始 key，内存 only
    "provider": "deepseek",
    "api_key": "sk-...",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "per_seat": { "2": { "model": "...", "api_key": "...", "base_url": "..." } }  // 可选
  },
  "human": { "seat": 1, "role": "Seer" } | null   // 新增；null=纯LLM观战
  // human.role 可选：给定=固定该角色(需为合法角色目录键且名额合法)；省略=人类座位也随机发牌
}
```
响应 `StartGameResponse` 增字段：`player_token: str`、`stream_path: str`（`/api/v1/games/{run_id}/stream`）。

### 6.2 `GET /api/v1/games/{run_id}/stream`（SSE）

- 查询：`view=god|seat`、`token`（人类局必带且座位匹配；god 仅观战局）。
- SSE `id:` = `event_id`（支持 `Last-Event-ID` 续传）。
- 事件信封：
```jsonc
{ "id": 42, "type": "WEREWOLF_KILLED", "round": 1, "phase": "NIGHT",
  "payload": { ... }, "visible": "public|wolf_team|private" }
```
- 特殊事件：
  - `snapshot`（首帧全量：座位/角色(按视角)/阶段/存活/警长）
  - `awaiting_input { seat, request_id, kind, prompt, valid_targets, deadline }`
  - `input_timeout { seat, request_id, fallback }`
  - `game_over { winner_camp, board_reveal, result_text }`
  - `game_cancelled` / `game_failed { error }`

### 6.3 `POST /api/v1/games/{run_id}/input`

```jsonc
{ "token": "...", "request_id": "...", "kind": "vote|speech|seat_choice|witch_night|yes_no|multi_target|last_words|sheriff_run|sheriff_vote",
  "payload": { /* 形如 bridge 契约: {seat} / {public_speech,private_thought} / {action,seat} / {choice} / {seats} */ } }
```
- 校验 token + 座位 + request_id 未消费 → resolve Future；幂等。
- 错误：403（token/座位不符）、404（无此待办）、409（已消费/已超时）。

### 6.4 复用现有

`GET /games/{id}/status`（结算页轮询）、`POST /games/{id}/cancel`、`GET /games/modes`、`/api/v1/pages/*`、`/api/v1/pages/replay`。

## 7. 前端组件与改动

| # | 区域 | 改动 |
|---|---|---|
| C1 | 删除 mock | 停用 `frontend/server.ts` 的 mock；`dev` 改 Vite + `server.proxy` 把 `/api`→`http://localhost:8000`；`build`/`start` 不再 bundle Express。 |
| C2 | `ApiClient` | `get()` 解包 `.data`；引入 `API_BASE`；新增 `startGame/streamUrl/sendInput/getStatus/cancel`。 |
| C3 | 事件 reducer | `lib/gameReducer.ts`（新）：纯函数，把后端 `EventType` 流折叠成可渲染 `GameState`（座位/昼夜/存活/当前发言者/票型/信念矩阵/弹窗音效触发）。 |
| C4 | store 重写 | `store.ts`：由「POST→替换 state」改为「订阅 SSE→`dispatch(event)`→reducer」；human 输入走 `sendInput`（带 token）；保留 overlays/cast UI 状态。 |
| C5 | 洞察接真数据 | `useGameInsight` 改读 SSE 流的信念/投票事件（替换 mock）；统一两处 `BeliefSnapshot` 类型分歧。 |
| C6 | 开局配置 `GameSetup` | LLM 供应商+Key+模型（全局，可选按座覆盖）；模式：纯LLM观战 / 人机（选座位 + 可指定角色）；板子/人数/警徽流；Key 仅随请求发送，存 localStorage 可选。 |
| C7 | 人类输入 UI | 复用 `SkillReleaseModal`/`ControlPanel`/`SpeechConsole`，由 `awaiting_input` 事件驱动显隐；可选回合倒计时条；输入校验对齐 `valid_targets`。 |
| C8 | 可见性 | 观战默认 `view=god`；人机强制 `view=seat`（后端已过滤）；InsightDock god-toggle 仅观战可用。 |
| C9 | 结算/复盘 | `GameOverPanel` 接 `game_over` 立即亮牌；MVP/教练轮询 status 后补；修 `/share/:runId` 死链；`RunsPage` 接真实 `/runs`（去 mock）。 |

## 8. 错误处理与边界

- **人类超时**：到 `deadline` → broker 安全兜底 resolve（投票=弃票、技能=不用、发言=空/默认）+ 推 `input_timeout`。
- **密钥安全**：见 §5；raw key 不落盘/日志/事件流/`repr`。
- **座位归属**：`input` 必带 `player_token` 且座位匹配，否则 403；观战者无 token 仅订阅。
- **断线/重连**：SSE `Last-Event-ID` 回放；人类断线其回合仍等待（或倒计时兜底）。
- **取消/失败**：`cancel` → `CancelledError` → 推 `game_cancelled`；引擎异常 → `game_failed` 事件 + 现有 `emit_session_failed` 告警。
- **并发**：多 run 各自 broker/broadcaster，`GameSessionManager` 按 run_id 隔离（已是）。
- **背压**：SSE 订阅 queue 有界，慢消费者丢旧帧但保留关键事件（或断开让其重连回放）。

## 9. 测试策略（遵循 repo pytest 约定）

- **后端单测**：`WebHumanAgent` await/resolve/超时兜底；`HumanInputBroker` 幂等 + token 校验；`EventBroadcaster` 按 `visible_to` 过滤（god vs seat 不泄露私有信念/狼聊/身份）；`setup_game` 固定人类角色；factory 原始 key 优先且不进 `model_dump`。
- **集成测**：`DemoAgent` 跑整局 + SSE 订阅断言事件序列与可见性；人机局用「脚本化输入」驱动 `WebHumanAgent` 走完发言/投票/夜技能/遗言。
- **前端**：`gameReducer` 喂事件序列→断言 GameState 快照；`ApiClient` 解包；SSE 重连。
- **防作弊回归**：seat view 流断言不含他人私有信息。

## 10. 文件改动地图 + 落地里程碑

一份 spec，分 4 个可独立验收的里程碑：

```
M0 契约打通
   - frontend: 删 mock、Vite proxy、ApiClient 解包、内容页接真后端（RunsPage/复盘/修死链）
M1 观战直播（纯LLM）
   - backend: EventBroadcaster + SSE 路由 + on_event 复合 + snapshot/Last-Event-ID
   - frontend: gameReducer + store 重写 + god 视角渲染（3D/发言/票/死亡/警长）
M2 信念/票型实时 + 结算
   - 信念矩阵 & 投票意向接 SSE 真数据；结算立即亮牌 + post-game 轮询补 MVP/教练
M3 人机对战
   - backend: WebHumanAgent + HumanInputBroker + input 路由 + 座位令牌 + 倒计时兜底
              + 原始 key 注入（factory/PlayerConfig，排除落盘） + setup_game 固定角色 + 放开拦截
   - frontend: 人机开局配置 + awaiting_input 驱动的输入 UI + seat 视角
```

涉及主要文件：
- 后端新增：`agent_team/agents/web_human_agent.py`、`interface/api/services/human_input.py`、`interface/api/services/event_stream.py`、（可选）`interface/api/routes/stream.py`。
- 后端改动：`agent_team/agents/base.py`、`agent_team/agents/factory.py`、`game_runtime/config/player_config.py`、`game_runtime/engine/base.py`、`interface/api/services/game_sessions.py`、`interface/api/routes/actions.py`、`interface/api/models/actions.py`。
- 前端改动：`frontend/server.ts`（去 mock）、`frontend/vite.config.ts`、`frontend/src/api/client.ts`、`frontend/src/store.ts`、`frontend/src/lib/gameReducer.ts`（新）、`frontend/src/hooks/useGameInsight.ts`、`frontend/src/components/GameSetup.tsx`、`frontend/src/components/ControlPanel.tsx`、`frontend/src/components/SkillReleaseModal.tsx`、`frontend/src/pages/RunsPage.tsx`、`frontend/src/pages/ReplayPage.tsx`、`frontend/src/api/types.ts`/`insightTypes.ts`。

## 11. 风险与开放项

- **引擎事件与 UI 状态的映射完整度**：需逐一核对 `EventType` → reducer 的覆盖（夜聊/验人/用药/守人/警徽流/遗言/猎人枪/情侣/第三方）。M1 起以「事件清单」驱动 reducer 测试。
- **人类决策点的覆盖**：需确认引擎在所有人类相关阶段都通过 `AgentProtocol` 取决策（发言/投票/夜技能/遗言/警长竞选/PK）。实现前用一局 `WebHumanAgent` 脚本化跑通做验证清单。
- **per-seat 不同供应商**的并发与限流（现有全局串行锁 `run_serial_agent_call`）——本期默认全局单供应商，按座覆盖作为可选项谨慎放开。
- **SSE 经 nginx**：需确认 `proxy_buffering off` 等配置（部署层），M1 一并处理。
- **角色池与人类选角的合法性**：选 Seer 等唯一神职时占用名额，需校验剩余分配仍合法。
