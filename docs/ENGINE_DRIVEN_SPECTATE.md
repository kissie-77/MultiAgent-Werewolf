# 纯 LLM 观战 · 引擎驱动 API —— 使用与变更说明

> 本次改造把"AI 狼人杀观战"从 **日志驱动**(前端读 `events.jsonl` 反推游戏状态)改成 **引擎驱动**
> (前端直接问游戏引擎的实时权威状态)。新增 **可控**(暂停/继续/单步/变速)与 **鲁棒**(SSE 实时流 +
> 断线续传 + 读盘兜底)能力。设计/计划见 `docs/superpowers/specs/2026-06-03-engine-driven-game-api-design.md`
> 与 `docs/superpowers/plans/2026-06-03-engine-driven-game-api.md`。

---

## 一、快速启动

### 方式 A：一键(推荐)
双击仓库根目录的 **`start-spectate.bat`**。它会：
1. 起后端 FastAPI（`http://127.0.0.1:8000`）；
2. 起前端 Vite（`http://127.0.0.1:5173`，首次自动 `npm install`）；
3. **轮询到前端真正就绪后** 自动打开浏览器（不再死等固定秒数）。

> ⚠️ 一律用 **`127.0.0.1`**，不要用 `localhost`。本机 `localhost` 会解析到 IPv6 `[::1]`，
> 而服务绑定在 IPv4，导致连不上（`vite.config.ts` 已固定 `host: "127.0.0.1"`）。

停止：双击 **`stop-spectate.bat`**（按端口 8000/5173 结束进程），或直接关掉两个新开的窗口。

### 方式 B：手动（两个终端）
```bash
# 终端 1 —— 后端
cd <repo>
uv run werewolf-api --host 127.0.0.1 --port 8000

# 终端 2 —— 前端
cd <repo>/frontend
npm install            # 仅首次
npm run dev:spectate
```
浏览器打开 **http://127.0.0.1:5173**。

### 进去之后怎么玩
1. 配置页：选人数（如 6）。
2. **API Key**：在 DeepSeek 栏粘贴密钥（见 `Apikey.txt`，已被 `.gitignore` 忽略，不会进仓库）；
   provider 选 **DeepSeek**，model 选 **`deepseek-chat`**
   （注意：`configs/llm-6p-deepseek.yaml` 默认写的是 `deepseek-v4-flash`，真跑请覆盖为 `deepseek-chat`）。
3. 开局 → 实时观战。
4. **控制条**（本次新增）：**暂停 / 继续 / 单步 / 变速(1×/2×/4×)**。
   暂停会在**阶段边界真停引擎**（不空烧 LLM 额度），发言/夜聊/技能走对话框，阶段切换由引擎权威驱动。

---

## 二、API 参考（后端 `/api/v1`）

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | `/games/{run_id}/state` | **权威实时状态**：直接序列化活引擎；打完/被回收的局回落读盘 |
| GET | `/games/{run_id}/stream` | **SSE 事件流**：`id:<seq>` + `event:game` + `data:<JSON>`；`Last-Event-ID` 自动续传 |
| POST | `/games/{run_id}/control` | `{action: pause\|resume\|step\|speed, value?}`，返回 `{run_id, play_state, speed, phase}` |
| POST | `/games/start` | 开局（沿用；body 可带逐座位 provider/model/api_key） |
| POST | `/games/{run_id}/cancel` | 取消（沿用） |

### `/state` 关键字段（spec §5.1）
```jsonc
{
  "status": "running|paused|ended|cancelled|error",
  "play_state": "playing|paused",
  "speed": 1,                       // 1|2|4
  "phase": "night",                 // 权威 GamePhase：setup/night/sheriff_election/day_discussion/day_voting/ended
  "sub_phase": "werewolf_chat",     // 子阶段提示（狼聊/女巫决策/预言家查验…），可能为 null
  "round": 2,
  "current_actor_seat": 5,
  "winner": null,
  "sheriff_seat": 3,
  "alive_count": 6, "dead_count": 2,
  "last_night": { "deaths":[{"seat":7,"cause":"wolf_kill"}], "saved_seat":null, "guarded_seat":4, "poisoned_seat":null },
  "votes": { "by_seat": {"1":5}, "tally": {"5":2} },
  "cursor": 142,                    // 0-based seq，与 /stream、/view 对齐
  "players": [ {"seat":1,"name":"…","role":"Seer","camp":"villager","is_alive":true,"is_sheriff":false,"model":"deepseek-chat","status_flags":["alive"]} ]
}
```

### `/stream` 事件（spec §5.2）
- `type ∈ speech | skill | vote | death | phase | sub_phase | system | belief | vote_intention`
- `skill.kind` 全集（含 5 个新结构化技能）：`wolf_kill, white_wolf_kill, wolf_beauty_charm, nightmare_block,
  guardian_wolf_guard, raven_mark, witch_save, witch_poison, seer_check, guard, graveyard_check, hunter_shoot, badge_transfer`
- 断线：浏览器 `EventSource` 自动重连并带 `Last-Event-ID`，服务端从内存环形缓冲补发 `seq` 之后的事件；
  若已被回收则从 `events.jsonl` 补发，绝不漏帧。

---

## 三、架构：日志驱动 → 引擎驱动

**改造前（日志驱动）**：`engine.play_game()` 一口气把整局跑完，只通过 `on_event` 把事件追加到磁盘
`events.jsonl`；读接口（`view.py`）每次重读日志、**反推** 阶段/死活/警长/胜负。引擎实例打完即丢，状态不可查。

**改造后（引擎驱动）**：
- `GameSession` **保活引擎**；`_run_game` 用 `engine.step()` **逐阶段泵推进**，过一道**控制闸**（暂停=真停、单步、变速）。
- 阶段间在 `next_phase()` 清空前**抓取夜晚结果**（`last_night` 不丢）。
- `on_event` **一源两写**：磁盘 `events.jsonl`（回放/复盘照旧）+ 内存 `EventHub`（SSE 实时推、0-based `seq`）。
- `GET /state` 直接序列化活引擎 → 权威 `phase/round/...`；前端按 `GamePhase` 枚举驱动 UI。
- 补全信号：`sheriff_election/day_voting/ended` 的 `phase_changed`、子阶段信号、5 个原本无类型的技能事件、
  拓宽 `role_data`（Hunter/Seer）。
- 前端：`EventSource` 取代轮询；删掉字符串猜 phase、假 30 秒倒计时、双重结束信号。

---

## 四、测试与排错

### 跑测试
> ⚠️ 本机 pytest 默认 `addopts`（`-n=auto` xdist + `--doctest-modules` + `--cov-fail-under=80`）会**卡死**，必须覆盖：
```bash
uv run pytest tests/interface tests/game_runtime -o addopts='' -p no:xdist -p no:cov -q
cd frontend && npm run lint && npx vitest run && npm run build
```

### 常见问题
| 现象 | 原因 / 处理 |
|---|---|
| 浏览器打不开/拒绝连接 | 用 `127.0.0.1` 不要 `localhost`；首次 vite 重新优化依赖较慢，新版 bat 会等就绪再开 |
| bat 窗口报 `'uv'/'npm' 不是内部或外部命令` | 系统 PATH 没有 uv/npm/node，需安装或加进 PATH |
| `address already in use` | 先运行 `stop-spectate.bat` 清端口 8000/5173 再重启 |
| 真跑 LLM 无响应 | model 用 `deepseek-chat`；key 填对（DeepSeek 栏或 `DEEPSEEK_API_KEY` 环境变量） |
| 代码被莫名重排/Pydantic 报错 | **不要全仓跑** `.pre-commit-config.yaml` 的 `ruff-check/ruff-format`（曾把运行期 import 挪进 `TYPE_CHECKING` 破坏 Pydantic） |

---

## 五、变更记录

**范围**：相对上一版 `main`（`84e49d3`）共 **55 个提交 / 65 文件 / +12418 / −362**。
全程在隔离 worktree（`feat/engine-driven-api`）开发，按 5 里程碑 TDD + 双评审（spec 合规 + 代码质量）+ 修复回环，
最终 fast-forward 合并回 `main`。

### 设计/计划
- `f5a17d5` 设计 spec（step 泵 + SSE + 鲁棒）
- `675adcd` 实施计划（5 里程碑，TDD）

### M1 —— 保活引擎 + `GET /state`
`a2dd974 31b95f5 46531b0 81beb51 4f49323 4a5b705 cb368db`
引擎驻留会话；`models/state.py`/`services/state.py`；活状态 + 读盘兜底；新增 `/state` 路由。

### M2 —— step 泵 + 控制闸
`26f7c2f 526018d 6ab2870 824d19f c82958e ae8c872`（+ 评审修复 `c4d88c5 79ea294`）
`play_game()` 换成 `step()` 泵循环 + 控制闸（暂停/继续/单步/变速）；`last_night` 清空前抓取；`POST /control`；
`step()` 与 `play_game()` 行为对齐（含等价性测试）。
> 质量评审抓到真 bug：`c4d88c5` 夜晚抓取的相位判断写反（`last_night` 本会永远抓不到）。

### M3 —— 引擎信号
`e3a8435 02d8a26 be55e3c 5b31690 01c384b 81bb28b 1a67c01 a86aa3f 2726bb4 dcb7fb0`
补全 `phase_changed`（警长竞选/投票/结束）；子阶段信号（狼聊/女巫/预言家）；5 个技能结构化事件
（白狼王/狼美人/噩梦/守卫狼→`guardian_wolf_guard`/乌鸦）；拓宽 `role_data`；§9 对账测试。

### M4 —— EventHub + SSE
`1459391 334e7de e1af62d 81d738e af39c8d ab6cdd2 e8a0260 24d07cd e71e475 64f4e47`
内存 `EventHub`（0-based seq + 环形缓冲补发）；`on_event` 一源两写；`GET /stream`（`Last-Event-ID` 续传 +
被回收时读盘补缺 + 终止错误帧）；`view.py` 分类新技能/子阶段事件并填充 `/state.sub_phase`、`current_actor_seat`。

### M5 —— 前端
`b4f85ab eb11ffb f6a972b 9d07212 286909e 06b79bc ec4aac7 c16f8a5 00cfca4`（+ `de79b20 1118087 5eadba2`）
`EventSource` /stream + `/state` 刷新 + `/control` 动作；按 `GamePhase` 驱动 UI；控制条；结构化技能/投票/死亡渲染 +
子阶段高亮；删假倒计时/双结束信号；Vite 代理对 SSE 关闭缓冲。

### 最终联调修复 / 收尾
- `61bfc30 88b6a72` —— **跨端契约修复**：SSE 事件 `day`→`round`、`sub_phase` 形状统一，并把前端 mock 改成真 wire shape 当护栏。
- `348c7df 1ab4ef3` —— Minor 清理 6 项（status_map 去重、删冗余赋值、超长行、终止 error 也落盘、`current_actor_seat` 随阶段清空、警长竞选发言计入）。
- `4ef33a4` —— 合并收尾：vite 绑 IPv4 host、`Apikey.txt` 入 `.gitignore`、启动脚本入库。
- `a3bb789` —— `start-spectate.bat` 改为等前端就绪再开浏览器。

### 验证结果
- 后端 `tests/game_runtime + tests/interface`：**411 passed**。
- 前端：`npm run lint` 干净 / **29 vitest passed** / `npm run build` 成功。
- **真机端到端**：真 DeepSeek 6 人局经 step 泵整局跑完；`/state` 权威实时；SSE 直连与穿 Vite 代理均为增量推送；
  `/control` 暂停在阶段边界真停引擎、resume 继续；`round`/`sub_phase`/技能结构化事件线上正确。
- 全程经修复回环抓修 **3 个真 bug**（M2 夜晚相位写反、SSE `day/round` 契约、最终审查发现的形状不一致）。
