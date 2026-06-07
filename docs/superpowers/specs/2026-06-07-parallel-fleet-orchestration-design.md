# 并行多栈开局编排（Parallel Fleet Orchestration）设计

- 日期：2026-06-07
- 分支：`feature/fe-be-integration`
- 关联：`docs/superpowers/specs/2026-06-06-frontend-backend-integration-design.md`（SSE + 人机地基）

## 1. 背景与目标

用户希望「同时开启多个前端和后端」，目的为**并行开局**。经探查确认两个用途同时存在：

1. **批量评测/数据**：并行跑很多局（5–20+），用于评测与复盘数据采集。
2. **人机对战**：多个真人各自开各自的局，互不干扰。

形态选择（已与用户确认）：**多后端 + 多前端的进程编排脚本**——一条命令拉起 N 套（后端 + 前端）各自独立端口，并配套一个把多局开局请求分发到各后端的批量驱动器。

## 2. 现状分析：项目设计能否做到？

**能。后端「单进程并行多局」其实已基本具备，缺的是「跨进程编排」和「run_id 唯一化」。**

| 层 | 现状 | 并行支持 |
|---|---|---|
| 会话管理 `interface/api/services/game_sessions.py` | `GameSessionManager._sessions: dict[run_id → GameSession]`；每次 `start_game` 都 `asyncio.create_task(_run_game)` | ✅ 单后端已能并行多局 |
| SSE 广播 `services/event_stream.py` | `_registry: dict[run_id → EventBroadcaster]` | ✅ 按 run_id 隔离 |
| 人类输入 `services/human_input.py` | `_registry: dict[run_id → HumanInputBroker]` | ✅ 按 run_id 隔离 |
| 引擎/Hub | `GameEngine`、`create_information_hub()` 每局新建 | ✅ 实例隔离 |
| 前端 store `frontend/src/store.ts` | 全局单例 Zustand，单 `EventSource`，**一标签页一局** | ⚠️ 多局=多标签页/多窗口，各带 `?run_id=` |
| 产物目录 `paths.py` + `deps.py` | `runs_dir = Path.cwd()/artifacts/runs`（所有后端共享） | ⚠️ 依赖 run_id 唯一 |
| run_id 生成 `game_sessions.start_game` | `run_id = f"{label}-{ts}"`（**秒级**）+ `mkdir(exist_ok=True)` | 🔴 同 label 同秒 → 碰撞 |

**关键缺陷**：`run_id` 仅到秒，且目录用 `exist_ok=True` 创建。两个后端（甚至单后端同秒双开）用同 label 同秒开局会得到**同一 run_id → 同一 run_dir**：

- `self._sessions[run_id] = session` 覆盖前一局，前一局变不可达；
- 两局的 `events.jsonl` 串写、`god_roster.json` 互覆盖；
- 复盘/状态查询读到混合数据。

这是**既有 bug**（单后端并行开局也中招），是本设计的 keystone 修复点。

## 3. 风险分析

| # | 风险 | 严重度 | 说明 | 缓解 |
|---|---|---|---|---|
| R1 | run_id 碰撞 | 🔴 HIGH | 见 §2 | run_id 唯一化（实例标签 + 微秒 + 目录存在性兜底计数器）；`mkdir(exist_ok=False)` |
| R2 | 共享 runs 目录 | 🟡 MED | 所有后端写同一 `artifacts/runs/`（评测聚合的优点，但依赖 R1） | 默认共享 + 唯一 run_id；保留 `--isolate-runs`（本期不实现，列 Enhancements） |
| R3 | API 限流/共享 key | 🔴 HIGH（评测规模） | N 后端 × M 局共用一个 key → 429 风暴 | batch 驱动器并发上限 + 错峰启动；可选 per-instance key env（透传，不落盘） |
| R4 | 资源耗尽 | 🟡 MED | 每个 vite dev server 重；后端内存随并发局增长 | 前端可选（`--frontends 0` 给评测走 headless） |
| R5 | 单事件循环/GIL | 🟡 MED | 单后端内多局共享一个 asyncio loop；I/O 型 LLM 调用交织良好，CPU 型解析串行 | 限制每后端并发局数，靠加后端横向扩展 |
| R6 | 全局状态接缝 | 🟢 LOW-MED | `runtime_log._active_handler`（provider_events 串台）、`role_version_manifest._active_manifest`（仅跨版本实验） | 多进程天然规避跨后端；修 log handler 为 per-run；manifest 文档化 |
| R7 | 孤儿进程/端口（Windows） | 🟡 MED | Win 进程终止语义不同，崩溃留孤儿 uvicorn/node | supervisor 记录 PID、健壮 teardown、Windows 用 `CREATE_NEW_PROCESS_GROUP` |
| R8 | CORS | 🟢 LOW | dev 下 vite 同源代理 `/api`，无跨域 | 默认无需改；仅直连他端口后端时扩 `WEREWOLF_CORS_ORIGINS` |

## 4. 设计

### 4.1 架构总览

```
werewolf-fleet up --backends 4 --frontends 4 --be-base 8010 --fe-base 5173
   │
   ├─ FleetPlanner（纯函数，可测）
   │     N + base ports → InstanceSpec[]：{idx, be_port, fe_port, tag, be_env, fe_env, urls}
   │
   ├─ ProcessSupervisor（subprocess + 健康检查 + 日志归集 + teardown）
   │     启 uvicorn × N（env: WEREWOLF_INSTANCE_TAG=i, OBS_READY_REQUIRE_LLM=…, --port be_port）
   │     启 vite    × N（env: VITE_API_PROXY=:be_port, --port fe_port）  ← --frontends 0 时跳过
   │     健康检查 GET /health（轮询直到 ok 或超时）；日志 → artifacts/fleet/<stamp>/instN-{backend,frontend}.log
   │     打印 URL 表；SIGINT/Ctrl-C → 逆序 terminate 全部子进程
   │
   └─ werewolf-fleet batch --config <id> --count 20 --concurrency 4 --stagger 1.5 --backends-from <fleet>
         BatchPlanner（纯函数）：count + backend URLs → 轮询 round-robin 分发计划（含并发窗口、错峰间隔）
         执行：POST /api/v1/games/start 分发；轮询 GET /api/v1/games/{run_id}/status 直到终态
         汇总：run_ids / 胜负阵营 / 耗时 / 失败数 → 控制台表 + artifacts/fleet/<stamp>/batch_summary.json
```

### 4.2 后端改动（聚焦、向后兼容）

**(a) run_id 唯一化 — keystone（`game_sessions.py`）**

抽出纯函数：

```python
def build_run_id(label: str, ts: str, *, tag: str | None, exists: Callable[[str], bool]) -> str:
    """{label}-{ts}[-{tag}]，若目录已存在则追加 -2/-3… 直到唯一。"""
```

- `tag` 来自 `os.environ.get("WEREWOLF_INSTANCE_TAG")`（launcher 注入；CLI/单后端无则为 None）。
- `exists` 注入 `lambda rid: (runs_dir / rid).exists()` 便于测试。
- `ts` 提升到含微秒或在碰撞时退到计数器（二者其一即可保证唯一；优先「存在性计数器」语义最直观）。
- `start_game` 中把 `run_dir.mkdir(parents=True, exist_ok=True)` 改为 `exist_ok=False`（唯一性已由 `build_run_id` 保证，碰撞即异常可见）。

向后兼容：无 tag 且无碰撞 → `{label}-{ts}` 不变。**顺带修复单后端同秒双开既有 bug。**

**(b) per-run 日志 handler（`observability/core/runtime_log.py`，R6）**

把全局 `_active_handler: handler | None` 改为 `_active_handlers: dict[str, handler]`（key=run_dir 字符串）：

- `attach_run_log_handler(run_dir)`：建 handler 加入 root logger，登记到 dict（不再先 detach 别人）。
- `detach_run_log_handler(run_dir)`：只移除该 run_dir 的 handler。
- 调用方 `_run_game` 的 `attach/detach` 传 `session.run_dir`。

低风险纯加法；多进程下本就各自独立，此修复保证「单后端多局」也不串台。

### 4.3 fleet 编排器（新增）

- 入口：`pyproject.toml [project.scripts]` 增 `werewolf-fleet = "llm_werewolf.interface.cli.fleet:entry"`（fire CLI，与 `werewolf-api` 一致）。
- 模块：`src/llm_werewolf/interface/cli/fleet/`
  - `planner.py`：`FleetPlanner`（纯函数）+ `BatchPlanner`（纯函数）。
  - `supervisor.py`：`ProcessSupervisor`（subprocess 起停 / 健康轮询 / 日志重定向 / 跨平台 teardown）。
  - `entry.py`：`up` / `batch` 两个子命令的 fire 绑定。

**`InstanceSpec`（纯数据）**

```
idx: int
be_port: int            # be_base + idx
fe_port: int            # fe_base + idx（frontends>0 时）
tag: str                # f"i{idx}"，进入 WEREWOLF_INSTANCE_TAG
backend_cmd: list[str]  # [uv, run, werewolf-api, --port, be_port]（实际用当前解释器/uv）
frontend_cmd: list[str] # [npm, run, dev, --, --port, fe_port]（cwd=frontend）
be_env / fe_env: dict
backend_url / frontend_url: str
```

**健康检查**：`GET http://127.0.0.1:{be_port}/health` 轮询至 `{"status":"ok"}`（超时 → 标记失败并打印该实例日志尾部）。

**跨平台 teardown（R7）**：

- POSIX：子进程置于新进程组，teardown 发 `SIGTERM` 给进程组，超时 `SIGKILL`。
- Windows：`subprocess.Popen(..., creationflags=CREATE_NEW_PROCESS_GROUP)`，teardown 用 `terminate()`（必要时 `taskkill /T`）。
- 注册 `signal`/`atexit`/`try-finally`，确保 Ctrl-C 不留孤儿。

**batch 驱动器（R3）**：

- `BatchPlanner.plan(count, backend_urls, concurrency, stagger)` → 纯函数产出 `[(seq, backend_url, delay_s)]` 轮询分发计划。
- 执行用 `httpx` 异步：并发窗口 ≤ `concurrency`，相邻启动间隔 `stagger` 秒错峰；每局 POST `/games/start`，拿 `run_id` 后轮询 `/games/{run_id}/status` 到终态（completed/failed/cancelled）。
- 汇总写 `batch_summary.json` + 控制台表。

### 4.4 前端：零代码改动

- 多前端纯靠 launcher 注入 `VITE_API_PROXY` + `--port`；「一标签页一局」模型不变。
- 人机对战：launcher 打印 `http://localhost:{fe_port}/` 分发给各真人；开局后照常带 `player_token` 进座位视图（`?run_id=&view=seat&seat=&token=`）。
- 评测：`--frontends 0` 不起任何 vite，batch 直连后端 API。

### 4.5 文档与 Makefile

- `Makefile` 增 `make fleet`（示例：`werewolf-fleet up --backends 2`）。
- `README.md`「本地全栈开发」后追加「并行多栈（fleet）」小节 + 风险/限流提示。

## 5. 测试方案

**纯函数 TDD（pytest，无子进程，主力覆盖）**

- `build_run_id`：同 label+秒+tag → 互异；存在性兜底计数器；无 tag 向后兼容。
- `FleetPlanner`：N=4 / base 8010,5173 → 端口、env、URL 正确且无重叠；`frontends=0` 不产前端命令。
- `BatchPlanner.plan`：round-robin 分发到各后端、并发窗口、错峰间隔计算正确；count<后端数 / count>后端数 边界。
- `runtime_log` per-run：两 run 并存互不踢；`detach(run_a)` 不影响 run_b。

**后端集成（pytest + httpx ASGI，无真 LLM）**

- 用 demo 配置在同一 app 内连开 2 局 → 断言 run_id 互异、两 `events.jsonl` 不串、两 session 都在 registry、两 god_roster 独立。

**冒烟（opt-in，标 `slow`/手动）**

- `werewolf-fleet up --backends 2 --frontends 0` 起 2 个 demo 后端到临时端口 → 健康检查通过 → 各 POST 开 1 demo 局 → 断言两 run_dir 独立 → teardown 后无孤儿进程。

**真机 E2E（手动，Playwright/curl）**

- `fleet up --backends 2 --frontends 2`，两浏览器标签各开各局 → 验证 SSE 各自独立、人机座位令牌互不串。

## 6. 非目标 / YAGNI（本期不做，列 Enhancements）

- `--isolate-runs` 每实例独立 runs 子目录（默认共享）。
- per-instance LLM key 透传（先用共享 env key + 错峰/并发限流扛 R3）。
- 负载均衡器 / docker-compose replicas（C 方案）。
- fleet 日志轮转 / 集中式监控面板。
- 前端「批量开局 + 多局看板」UI（属于「单后端多局」形态，非本期所选形态）。

## 7. 落地顺序（详细计划见 writing-plans 产物）

1. 后端 keystone：`build_run_id` + `mkdir(exist_ok=False)`（TDD）。
2. 后端 R6：`runtime_log` per-run handler（TDD）。
3. `FleetPlanner` / `BatchPlanner` 纯函数（TDD）。
4. `ProcessSupervisor` + `fleet up`（含健康检查/teardown）。
5. `fleet batch` 驱动器（httpx 执行 + 汇总）。
6. 后端集成测试（同 app 连开 2 局）。
7. 文档 + Makefile + 冒烟测试。
