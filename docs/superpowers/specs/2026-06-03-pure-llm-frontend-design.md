# 纯 LLM 对战观战模式 — 前端改造 + 后端 API 设计

- **日期**：2026-06-03
- **状态**：设计已评审通过，待写实施计划
- **目标读者**：A（AgentScope/agent_team）、B（GameEngine）、C（前端/API/日志）

## 1. 背景与目标

当前 `frontend/` 是 React 19 + Three.js + Vite 界面，通过 **Express(`server.ts`, Gemini)** 跑游戏逻辑，主打"一个人类 + AI"的人机局。同时 Python 侧有一套成熟的 GameEngine（信念矩阵 / 24 角色 / 评测）与 FastAPI（`/api/v1`），但前端并未对接。

**本次目标**：把现有 React 主界面改造成**纯 LLM 对战的观战界面**——所有座位都是 LLM，无人类操作；发言走对话框、技能/投票走内嵌事件、可展示 AI 内心推理；LLM 配置参照 wolfcha 做成**前端逐座位**形态。**后端继续用 Python 引擎当大脑，前端只调 API。**

**参照项目**：`D:\AI_werewolf\NEW\wolfcha`（Next.js）。仅借鉴其 **UI 形态**（对话气泡、逐座位 ModelRef 配置、localStorage 管 key、temperature 预设），**不**照搬其"前端当裁判、前端直连 LLM"的编排方式。

### 非目标（本版不做）

- 人机混合 / 人类参与的 web 局（Python 侧 `game_sessions.py:115` 已明确 block）。
- 复盘页改造、信念矩阵可视化面板（列入第二阶段）。
- 真·逐 token 流式（本版为"整句到达 + 前端打字机"）。
- LLM 驱动的实时控制（暂停/变速纯前端，不回灌引擎）。
- key 持久化到后端磁盘。

## 2. 已锁定的设计决策

| # | 决策点 | 结论 |
|---|--------|------|
| 1 | 游戏大脑 | **Python 引擎**；前端复用现有 React UI，只调 API |
| 2 | 数据投递 | **增量轮询** `GET /games/{run_id}/view?since=N`（~1s 一次） |
| 3 | 观战视角 | **上帝视角全量流 + `reveal` 标签 + 前端悬念开关**（后端单路径全推，前端决定遮挡） |
| 4 | LLM 配置 | **前端逐座位** 选 provider/model + 填 key（存 localStorage） |
| 5 | 技能展示 | **对话流内嵌文字事件**（🔮查验 / 🐺刀 / 🗳️投票 / 💀出局） |
| 6 | 播放控制 | **自动播放 + 暂停/继续 + 变速**，节奏全前端控 |
| 7 | 改动范围 | **开局配置页 + 主界面观战**（本功能闭环） |
| 8 | Key 处理 | **localStorage 存 + 开局随 body 传**，Python 仅会话内存用、**不落盘** |
| 9 | 私密推理 | **展示** AI 内心 OS（`private_thought`） |
| 10 | 归约层 | **方案B：后端给"渲染就绪投影"**（`/view`），前端做薄 |

## 3. 架构与数据流

一句话：Python 引擎在后台把整局 LLM 对战**跑到底**、事件落 `events.jsonl`；后端 `/view` 投影接口把"事件 + 当前状态"揉成**渲染就绪** JSON；前端**轮询**该接口，玩家表直接吃快照，对话/技能/内心OS 进本地队列，再按用户控制的节奏吐到对话框。

```
┌─────────────┐   ① POST /games/start (逐座位 provider/model/key)  ┌──────────────────────────┐
│  React 前端  │  ───────────────────────────────────────────────▶ │  FastAPI /api/v1          │
│ (复用现有UI) │   ← { run_id }                                      │  GameSessionManager       │
│             │                                                     │   └ 后台 asyncio Task     │
│  store.ts   │   ② 轮询 GET /games/{id}/view?since=N               │      GameEngine.play_game │
│  (变薄)     │  ───────────────────────────────────────────────▶ │      (跑到底, 不等前端)    │
│             │   ← { snapshot(渲染就绪), events[](已塑形), cursor } │      on_event→events.jsonl │
│ 本地事件队列 │                                                     │  /view = 新增投影层:       │
│ +节奏机     │   ③ POST /games/{id}/cancel (停)                    │   读 events.jsonl[N:] +    │
│             │  ───────────────────────────────────────────────▶ │   extract_snapshot → UI形 │
└─────────────┘                                                     └──────────────────────────┘
```

**三个关键性质**：

1. **对局后台跑到底，与前端节奏解耦**。LLM 快慢、前端看不看，引擎都自顾自把事件写进 `events.jsonl`；前端只是"回放游标"。
2. **播放控制（暂停/继续/变速）是纯前端的**。暂停=不再从本地队列吐字；变速=调吐字速率。**后端无 pause 接口**，唯一后台控制是 `cancel`。
3. **规则真相在快照（引擎权威），展示在事件流**。前端不重算"谁死了/几票"，避免前后端口径打架（方案B 的核心收益）。

## 4. 后端 API 契约

仅动 3 个端点，全在 `/api/v1`。

### 4.1 `POST /api/v1/games/start` — 扩展请求体

新增 `inline` 模式接收逐座位配置；`config_id`/`preset` 旧路径保留。

```jsonc
{
  "mode": "inline",                   // "inline" | "preset"
  "config_id": "llm-9p-doubao",       // inline 下作"打底模板"(语言/记忆/角色版本等非密配置)
  "rules": {
    "player_count": 9,                // 6–20
    "language": "zh-CN",
    "enable_sheriff": true,
    "badge_flow": false,
    "reveal_mode_default": "god"      // 前端悬念开关初值，仅初值
  },
  "players": [
    {
      "seat": 1, "name": "Player1",
      "provider": "deepseek",         // 前端 UI 分组用；后端以 base_url 为准
      "model": "deepseek-chat",
      "base_url": "https://api.deepseek.com/v1",
      "api_key": "sk-xxx",            // localStorage 来；仅会话内存用、不落盘
      "temperature": 1.1              // 可选；缺省走后端 phase 预设
    }
    // ... 逐座位，长度 = player_count
  ]
}
```

响应沿用现有 `StartGameResponse`（`{ run_id, status, run_dir, player_count, ... }`）。角色仍由引擎按人数预设洗牌（`engine/base.py setup_game`），前端不指定。

### 4.2 `GET /api/v1/games/{run_id}/view?since=N` — 新增投影接口（方案B 核心）

一接口同返"渲染就绪快照 + 自 N 之后的增量事件"。

```jsonc
{
  "cursor": 142,                      // 下次带 since=142
  "status": "running",                // running | ended | cancelled | error
  "error": null,

  "snapshot": {                       // 引擎权威, 幂等, 直接喂玩家表/顶栏
    "day": 2, "phase": "DAY_VOTING", "phase_label": "第2天 · 放逐投票",
    "winner": null, "alive_count": 6, "dead_count": 3, "sheriff_seat": 4,
    "players": [
      {
        "seat": 1, "name": "Player1", "provider": "deepseek", "model": "deepseek-chat",
        "role": "预言家", "camp": "好人", "is_alive": true, "is_sheriff": false,
        "death": null                 // 或 {day, phase, cause:"狼刀|放逐|毒|枪", reveal:"on_death"}
      }
    ],
    "vote_tally": {
      "round": 2, "counts": { "5": 4, "3": 1 },
      "result": { "executed_seat": 5, "tied": false }
    }
  },

  "events": [                         // 自 N 之后, 已塑形为 UI 形态
    {
      "seq": 138, "type": "speech", "day": 2, "phase": "DAY_DISCUSSION",
      "speaker": { "seat": 1, "name": "Player1", "role": "预言家" },
      "public_text": "我昨晚验了5号，是查杀，今天必须投他。",
      "private_thought": "其实更怀疑3号，但先立5号查杀稳局面。",  // 上帝视角才带
      "reveal": "now", "visibility": "public"
    },
    {
      "seq": 139, "type": "skill", "day": 1, "phase": "NIGHT",
      "skill": { "kind": "seer_check", "actor": {"seat":1,"role":"预言家"},
                 "target": {"seat":5,"name":"Player5"}, "result": "查杀" },
      "text": "🔮 预言家(1号) 查验 5号 → 查杀",
      "reveal": "on_game_end", "visibility": "god"
    },
    { "seq": 140, "type": "vote",
      "vote": { "voter": {"seat":2}, "target": {"seat":5}, "weight": 1.0 },
      "text": "🗳️ 2号 → 5号", "reveal": "now", "visibility": "public" },
    { "seq": 141, "type": "death",
      "death": { "seat": 5, "name": "Player5", "role": "狼人", "cause": "放逐" },
      "text": "💀 5号(狼人) 被放逐", "reveal": "now", "visibility": "public" },
    { "seq": 142, "type": "phase", "from": "DAY_VOTING", "to": "NIGHT",
      "text": "—— 第2天 · 夜晚 ——", "reveal": "now", "visibility": "public" }
  ]
}
```

**`reveal` / `visibility` 语义**：后端全推（上帝视角），前端按标签遮挡。
- `reveal`：`now` 永显；`on_death` 该座位死后揭；`on_game_end` 终局揭。
- 上帝视角 = 无视 reveal 全显；悬念模式 = 按 reveal 遮身份/夜间技能。
- `visibility`（`public|wolf|god`）为样式分层辅助（内心OS、狼队夜谈用不同底色）。
- `type` 取值：`speech | skill | vote | death | phase | system | belief | vote_intention`。
- `skill.kind`：`wolf_kill | seer_check | witch_save | witch_poison | guard | hunter_shoot | badge_transfer | ...`。

### 4.3 `POST /api/v1/games/{run_id}/cancel` — 复用现状

前端"停止"按钮调用，停掉后台对局 Task。暂停/变速**不调后端**。

### 4.4 改动一览

| 端点 | 动作 | 说明 |
|------|------|------|
| `POST /games/start` | **改** | 加 `mode:"inline"` + `players[]`（provider/model/key/temperature）；key 仅会话内存 |
| `GET /games/{id}/view?since=N` | **新增** | 投影层：快照(权威) + 增量事件(已塑形)；前端唯一主力接口 |
| `POST /games/{id}/cancel` | 复用 | 停后台对局 |
| `GET /games/{id}/status` | 保留 | 旧端点不动，`/view` 为其超集 |

## 5. 后端内部改动（落到文件）

### 5.1 配置层：让前端 model/key/temperature 进引擎
| 文件 | 改动 |
|---|---|
| `game_runtime/config/player_config.py` `PlayerConfig` | 新增 `api_key: str\|None`（字面量，web 用）+ `temperature: float\|None`；保留 `api_key_env`（CLI/YAML 不变） |
| `agent_team/agents/factory.py:227` `create_react_agent` | key 解析改 `config.api_key or os.getenv(config.api_key_env)`；`generate_kwargs` 接上 `temperature` |
| provider→base_url | 前端直接传 `base_url`，后端不加映射表 |

### 5.2 开局层：内联配置路径
| 文件 | 改动 |
|---|---|
| `interface/api/models/actions.py` `StartGameRequest` | 加 `players: list[PlayerSpec]\|None`（seat/name/provider/model/base_url/api_key/temperature）；`config_id` 退化为打底模板 |
| `interface/api/services/roster_customize.py` `prepare_start_players_config` | 扩展：把 `request.players` 逐座位字段灌进 `PlayersConfig` |
| `interface/api/services/game_sessions.py:146` | **写 `launch_roster.json` 前抹掉 `api_key`**（`model_dump(exclude={"api_key"})`）——key 绝不落盘 |

### 5.3 事件层：补齐展示字段（多数已有）
- **发言事件**：确保 `data` 带 `private_thought`。核对 `engine/day_phase.py` + `phase_interaction` 发言落点，当前公开发言**很可能未带**私密推理，需补字段。
- **夜间技能/投票**：`engine/action_processor.py` / `engine/voting_phase.py` 已带 actor/target/result/decision metadata，核对补缺。
- 全程复用 `on_event → IncrementalEventWriter → events.jsonl`，**无新管道**。

### 5.4 投影层（唯一新模块）
- 新增 `interface/api/services/view.py`：`build_view(run_dir, since:int) -> ViewResponse`
  - 读 `events.jsonl[N:]`（`event_from_dict`）→ `map_event_to_ui()` 按 `event_type` 分流，生成展示文案（走 `Locale`），打 `reveal`/`visibility` 标签。
  - 复用 `extract_game_snapshot(run_dir)`（`services/replay.py`）拼 render-ready 快照。
  - `cursor` = 已读行数。
- 新路由：`interface/api/routes/actions.py` 加 `GET /games/{run_id}/view`（或新建 `routes/view.py`）。

### 5.5 不动的
`cancel` 复用、**无 pause**；`IncrementalEventWriter`、后台 `play_game` Task、`events.jsonl`、`get_status` 全保留。

**后端工作量结论**：真正新代码就一个 `view.py` 投影层；其余是"加字段 + 改一行 key 解析 + 抹一个落盘字段 + 补一个事件字段"。

## 6. 前端逐文件改动

核心：方案B 下 **store 变薄**——只做"轮询 → 合并快照 → 事件入队 → 按节奏吐字"。

### 6.1 store 的心脏：轮询 + 渲染队列 + 节奏机（最大工作量）
```
startGame() ─▶ POST /games/start (逐座位配置+key from localStorage) ─▶ 存 run_id
每~1s: GET /games/{run_id}/view?since=cursor
  snapshot ─▶ set players/phase/day/voteTally (组件直接渲染)
  events[] ─▶ 推入 renderQueue, 更新 cursor
节奏机(独立定时器, isPlaying 时按 speed 弹出):
  speech ─▶ 打字机逐字进 speechLogs
  skill/vote/death/phase ─▶ 整行进 speechLogs
  暂停=停弹出; 变速=调弹出/吐字速率;  全前端
```

### 6.2 逐文件
| 文件 | 改动 |
|---|---|
| `src/store.ts` | 重写数据层：`/api/game/*`(Express) → `/api/v1/*`(Python)。删人类动作；加 `startGame/pollView/cancelGame` + `renderQueue/cursor/isPlaying/speed/revealMode` + 节奏机 |
| `src/components/GameSetup.tsx` | 加逐座位 LLM 配置（provider 下拉 + model + API Key→localStorage）；人数 stepper 保留，角色选择隐藏。借鉴 wolfcha `api-keys.ts` + `ModelRef` + `GAME_TEMPERATURE` |
| `src/components/SpeechConsole.tsx` | 发言→气泡；skill/vote/death/phase→内嵌事件行；新增**内心OS 块**(`private_thought`，区分底色/可折叠)；按 `revealMode`+事件 `reveal` 做悬念遮挡 |
| `src/components/ControlPanel.tsx` | 换成播放控制台：▶/⏸ + 速度滑块 + ⏹停止(cancel) + 上帝/悬念开关。删所有人类输入 |
| `src/components/CardDeck.tsx` | 改只读；身份按 `revealMode`+座位 `reveal` 显/遮 |
| `src/components/SkillBar.tsx` | 本版移除（无人类技能） |
| `src/types.ts` | 对齐 `/view`：`Player` 加 provider/model/role/camp/isSheriff/death；新增 `ViewEvent` 联合类型、`Snapshot` |
| `src/components/ThreeCanvas.tsx` | 基本保留；高亮当前发言座位 |
| `src/components/TopHeader.tsx` | day/phase/存活数 吃 snapshot |
| `src/components/GameOverPanel.tsx` | winner 吃 snapshot；可留"看复盘"入口 |

### 6.3 运行/接线
- 前端改打 Python `:8000`（CORS 已放行 `localhost:3000/5173`，`app.py:58`）。
- Express `server.ts` 游戏逻辑退役；静态服务可保留空壳或直接 `vite dev` 走 5173（实现时定）。

## 7. 测试策略

- **后端**（pytest，覆盖率门槛 80%）：
  - `view.py`：给定一份 `events.jsonl` fixture，断言 `build_view(since=N)` 的 cursor / 事件分流 / reveal 标签 / 快照字段正确。
  - `start_game` inline 模式：断言逐座位 model/key/temperature 进 `PlayerConfig`；断言 `launch_roster.json` **不含** `api_key`（安全回归测试）。
  - `factory.create_react_agent`：断言字面量 `api_key` 优先于 `api_key_env`、`temperature` 进 `generate_kwargs`。
  - 事件字段：断言发言事件 `data` 含 `private_thought`。
- **前端**（手测为主，本版）：开局配置 → 观战流 → 暂停/变速 → 悬念/上帝切换 → 停止；断网/出错的轮询降级。

## 8. 风险与待确认

1. **投影文案与 i18n**：`/view` 的 `text` 走 `Locale`，需覆盖所有 `skill.kind` 与 phase 的展示模板；缺失 key 要有兜底。
2. **`private_thought` 是否一直可得**：依赖 bridge 产出 `SpeechDecision.private_thought`；结构化失败兜底路径可能为空，前端需容空。
3. **轮询频率 vs events.jsonl 读放大**：每次从 `since=N` 读尾部即可，注意大文件按行 seek/缓存行数，避免整文件重读。
4. **key 安全边界**：本地工具场景可接受 key 走 body；务必确认 `launch_roster.json`、任何日志、`run_meta.json` 均不含 key。
5. **Express 退役范围**：静态服务保留与否，影响开发启动命令，实现时定。
6. **belief/vote_intention 事件**：本版仅"带上数据"，可视化面板留第二阶段；前端先忽略或极简展示。

## 9. 阶段划分

- **本版（闭环）**：第 4–6 节全部。
- **第二阶段**：复盘页同款回放、信念矩阵/投票意向可视化面板、真逐 token 流式、provider 预设注册表。
