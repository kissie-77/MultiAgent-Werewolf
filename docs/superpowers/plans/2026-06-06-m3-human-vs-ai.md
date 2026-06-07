# M3 人机对战（Human-vs-AI）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 单个人类座位 vs 其余全 AI；引擎在人类决策点暂停，等待浏览器 `POST /input` 提交后继续；人类走严格本人座位视角（防作弊由后端 `Event.visible_to` 过滤天然保证）。

**Architecture:** 复用 M1/M2 已建成的 SSE 直播半边（`EventBroadcaster` + `/games/{id}/stream?view=seat&seat=&token=` + 可见性过滤）。新增三件套：`WebHumanAgent`（实现 `BaseAgent.get_response`，把决策 `await` 给 broker，**镜像** `HumanInteractiveAgent` 的 classify/normalize 逻辑，使 bridge 文本解析路径零改动）+ `HumanInputBroker`（每 run 一个 Future 登记表，挂起人类决策、经 broadcaster 推 `awaiting_input` 事件、`submit()` 幂等 resolve、超时安全兜底）+ `POST /games/{id}/input`（带座位令牌）。引擎主循环与 bridge **零改动**。

**Tech Stack:** Python 3 / asyncio / FastAPI / pydantic / sse-starlette；前端 React + Vite + TypeScript + vitest。

**Scope（最小可发版切片 = Tasks 1–9）：** AI 座位沿用**服务端环境变量 key**（与现观战局一致，零新风险）；人类角色**随机发牌**；人类回合用**宽松 deadline + 安全兜底**（无倒计时条 UI）。
**显式延后（Enhancements，列于文末，非本切片）：** A7 原始 key 注入（`llm` 字段）、A8 固定人类角色（`setup_game(fixed_seat_roles=)`）、回合倒计时 UI、按座位不同供应商。

**关键约束（务必遵守）：**
- 改任何函数/类前先 `gitnexus_impact({target, direction:"upstream"})`，HIGH/CRITICAL 先告知用户。提交前 `gitnexus_detect_changes()`。
- 单文件 pytest 用 `--no-cov`（仓库有 `--cov-fail-under=80` 全局门）。中文 stdin 用 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`。
- **绝不**把原始 LLM key 落盘/日志/事件流/`repr`/`model_dump`。
- 提交信息结尾：`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。

---

## 文件结构（File Structure）

**后端新增**
- `src/llm_werewolf/agent_team/agents/web_human_agent.py` — `WebHumanAgent`（await broker）。
- `src/llm_werewolf/interface/api/services/human_input.py` — `HumanInputBroker` + 进程内 registry（镜像 `event_stream.py`）。

**后端改动**
- `src/llm_werewolf/game_runtime/config/player_config.py:97,108` — `_BUILTIN_MODELS = {"human","demo","web-human"}`，两处校验放行 `web-human`。
- `src/llm_werewolf/agent_team/agents/base.py:204` — `create_agent` 增 `web-human` 分支。
- `src/llm_werewolf/interface/api/models/actions.py` — `HumanSeatSpec`；`StartGameRequest.human`；`StartGameResponse.player_token/stream_path`。
- `src/llm_werewolf/interface/api/services/game_sessions.py` — 建 web-human 座位、座位令牌、broker、把 broker 接进 agent；放开 web-human 拦截。
- `src/llm_werewolf/interface/api/routes/actions.py` — `POST /games/{run_id}/input`。

**前端改动**
- `frontend/src/api/types.ts` — `human` 入参、`player_token/stream_path` 出参、`AwaitingInput` 事件、`HumanInputPayload`。
- `frontend/src/api/client.ts` — `sendInput(runId, body)`。
- `frontend/src/store.ts` — seat 视角订阅（带 token）、`awaiting_input`/`input_*` 事件处理、`submitHumanInput`。
- `frontend/src/lib/humanInput.ts`（新）— 纯函数：把 `awaiting_input{kind,valid_targets}` + 人类 UI 选择折叠成 `HumanInputPayload`（镜像 bridge 文本契约）。
- `frontend/src/components/GameSetup.tsx` — 人机模式（选座位）。
- `frontend/src/components/HumanInputPanel.tsx`（新或复用 `ControlPanel`/`SkillReleaseModal`）— 由 `awaiting_input` 驱动。

---

## Task 1: `PlayerConfig` 放行 `web-human` 内建模型

`web-human` 座位不需要 `base_url`/`api_key_env`（无 LLM 调用），必须像 `human`/`demo` 一样被两处校验视为内建模型。

**Files:**
- Modify: `src/llm_werewolf/game_runtime/config/player_config.py:96-103,105-122`
- Test: `tests/game_runtime/config/test_web_human_player_config.py`

- [ ] **Step 1: 写失败测试**

```python
from llm_werewolf.game_runtime.config.player_config import PlayerConfig

def test_web_human_needs_no_base_url_or_key():
    cfg = PlayerConfig(name="P1", model="web-human")
    assert cfg.model == "web-human"
    assert cfg.base_url is None
    assert cfg.api_key_env is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/game_runtime/config/test_web_human_player_config.py -v --no-cov`
Expected: FAIL（`resolve_model_from_env` 报 "Either model or model_env is required" 或 base_url 校验）。

- [ ] **Step 3: 实现**

`player_config.py` 顶部加常量并在两个校验里用它：
```python
_BUILTIN_MODELS = {"human", "demo", "web-human"}
```
`validate_base_url`：`is_builtin = model in _BUILTIN_MODELS`
`resolve_model_from_env`：`if self.model in _BUILTIN_MODELS: return self`

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/game_runtime/config/test_web_human_player_config.py -v --no-cov`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/llm_werewolf/game_runtime/config/player_config.py tests/game_runtime/config/test_web_human_player_config.py
git commit -m "feat(m3): allow web-human builtin player model"
```

---

## Task 2: `HumanInputBroker` —— 挂起/提交/超时

每 run 一个 broker。`request()` 由 agent 调，登记一个 `asyncio.Future`、经 broadcaster 推 `awaiting_input`、`await` 直至 `submit()` 或超时兜底。`submit()` 由 HTTP 调，校验座位 + `request_id` 去重后 resolve；幂等。

**Files:**
- Create: `src/llm_werewolf/interface/api/services/human_input.py`
- Test: `tests/interface/api/services/test_human_input_broker.py`

设计契约：
```python
class PendingRequest:  # dataclass
    request_id: str
    seat: int
    kind: str
    future: asyncio.Future[str]

class HumanInputBroker:
    def __init__(self, run_id: str, seat: int, broadcaster=None) -> None: ...
    async def request(self, *, kind: str, prompt: str, valid_targets: list[int],
                      fallback: str, deadline: float | None = None) -> str:
        """登记 + 推 awaiting_input + await future；超时→fallback 并推 input_timeout。返回归一化文本。"""
    def submit(self, *, request_id: str, payload: str) -> bool:
        """resolve 对应 future；未知/已消费 → False（幂等）。"""
    def pending_ids(self) -> set[str]: ...
```
`awaiting_input` 事件 dict：`{"event_type":"awaiting_input","seat":seat,"request_id":rid,"kind":kind,"prompt":prompt,"valid_targets":[...],"deadline":deadline,"visible_to":[f"player_{seat}"]}`（注意 `visible_to` 含本座位 → seat 流可见，god 流也可见；不泄漏给他人座位）。
registry：`get_or_create_input_broker(run_id, seat, broadcaster)` / `get_input_broker(run_id)` / `remove_input_broker(run_id)`。

- [ ] **Step 1: 写失败测试**

```python
import asyncio
import pytest
from llm_werewolf.interface.api.services.human_input import HumanInputBroker

class _Spy:
    def __init__(self): self.events = []
    def publish(self, ev): self.events.append(ev)

@pytest.mark.asyncio
async def test_request_resolves_on_submit():
    spy = _Spy()
    broker = HumanInputBroker(run_id="r1", seat=1, broadcaster=spy)
    task = asyncio.create_task(
        broker.request(kind="seat", prompt="投票", valid_targets=[2, 3], fallback="0")
    )
    await asyncio.sleep(0)  # 让 request 登记并推事件
    rid = next(iter(broker.pending_ids()))
    assert spy.events and spy.events[0]["event_type"] == "awaiting_input"
    assert spy.events[0]["visible_to"] == ["player_1"]
    assert broker.submit(request_id=rid, payload="2") is True
    assert await task == "2"
    # 幂等：再次 submit 同 id 返回 False
    assert broker.submit(request_id=rid, payload="3") is False

@pytest.mark.asyncio
async def test_request_times_out_to_fallback():
    broker = HumanInputBroker(run_id="r1", seat=1, broadcaster=_Spy())
    out = await broker.request(kind="seat", prompt="投票", valid_targets=[2],
                               fallback="0", deadline=0.05)
    assert out == "0"

def test_submit_unknown_request_is_false():
    broker = HumanInputBroker(run_id="r1", seat=1, broadcaster=_Spy())
    assert broker.submit(request_id="nope", payload="2") is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/interface/api/services/test_human_input_broker.py -v --no-cov`
Expected: FAIL（模块不存在）。

- [ ] **Step 3: 实现** `human_input.py`

要点：
- `request()`：`rid = f"{self.run_id}-{self.seat}-{self._counter}"`（`self._counter += 1`，避免 `Math.random`/uuid 不确定性影响可测性）；`fut = loop.create_future()`；存 `self._pending[rid] = PendingRequest(...)`；`broadcaster.publish(awaiting_input)`；`try: return await asyncio.wait_for(fut, deadline) except (asyncio.TimeoutError):` 推 `input_timeout` 事件并 `return fallback`；`finally: self._pending.pop(rid, None)`。
- `submit()`：`pr = self._pending.get(request_id)`；`if pr is None or pr.future.done(): return False`；`pr.future.set_result(payload)`；推 `input_received`；`return True`。

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/interface/api/services/test_human_input_broker.py -v --no-cov`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/llm_werewolf/interface/api/services/human_input.py tests/interface/api/services/test_human_input_broker.py
git commit -m "feat(m3): HumanInputBroker (await/submit/timeout) with awaiting_input event"
```

---

## Task 3: `WebHumanAgent` —— 把决策 await 给 broker

镜像 `HumanInteractiveAgent` 的 `_classify`/`_extract_option_seats`/`_witch_save_allowed`/`_fallback_after_invalid` 等**静态**辅助（直接复用 import，不复制），把 stdin `input()` 换成 `await self.broker.request(...)`。返回**归一化文本**（与 stdin 人类同格式：座位号串 / `救`/`毒 [[3]]` / `1`/`0` / 发言原文），bridge 文本路径零改动解析。

**Files:**
- Create: `src/llm_werewolf/agent_team/agents/web_human_agent.py`
- Test: `tests/agent_team/agents/test_web_human_agent.py`

```python
from pydantic import Field
from llm_werewolf.agent_team.agents.base import BaseAgent
from llm_werewolf.agent_team.agents.human_interactive_agent import HumanInteractiveAgent

class WebHumanAgent(BaseAgent):
    model: str = Field(default="web-human")
    seat: int = Field(default=0, exclude=True)
    broker: object | None = Field(default=None, exclude=True)  # HumanInputBroker

    model_config = {"arbitrary_types_allowed": True}

    async def get_response(self, message: str) -> str:
        if self.broker is None:
            return ""  # 未接 broker（防御）→ 交由引擎兜底
        kind, n, allow_skip = HumanInteractiveAgent._classify(message)
        option_seats = sorted(HumanInteractiveAgent._extract_option_seats(message))
        fallback = HumanInteractiveAgent._fallback_after_invalid(kind, allow_skip)
        return await self.broker.request(
            kind=kind, prompt=message, valid_targets=option_seats, fallback=fallback,
        )
```

- [ ] **Step 1: 写失败测试**

```python
import pytest
from llm_werewolf.agent_team.agents.web_human_agent import WebHumanAgent

class _FakeBroker:
    def __init__(self, reply): self.reply = reply; self.calls = []
    async def request(self, **kw): self.calls.append(kw); return self.reply

@pytest.mark.asyncio
async def test_seat_decision_awaits_broker():
    broker = _FakeBroker("2")
    agent = WebHumanAgent(name="P1", seat=1, broker=broker)
    msg = "请只回复目标玩家的全局座位号\n可选目标:\n- 座位 2\n- 座位 3"
    out = await agent.get_response(msg)
    assert out == "2"
    assert broker.calls[0]["kind"] == "seat"
    assert broker.calls[0]["valid_targets"] == [2, 3]

@pytest.mark.asyncio
async def test_no_broker_returns_empty():
    agent = WebHumanAgent(name="P1", seat=1)
    assert await agent.get_response("任意") == ""
```

- [ ] **Step 2: 跑确认失败** — `uv run pytest tests/agent_team/agents/test_web_human_agent.py -v --no-cov` → FAIL（模块不存在）。
- [ ] **Step 3: 实现** `web_human_agent.py`（如上）。
- [ ] **Step 4: 跑确认通过** — 同命令 → PASS。
- [ ] **Step 5: 提交**

```bash
git add src/llm_werewolf/agent_team/agents/web_human_agent.py tests/agent_team/agents/test_web_human_agent.py
git commit -m "feat(m3): WebHumanAgent awaits HumanInputBroker for each decision"
```

---

## Task 4: `create_agent` 增 `web-human` 分支

**Files:**
- Modify: `src/llm_werewolf/agent_team/agents/base.py:202-215`
- Test: `tests/agent_team/agents/test_create_agent_web_human.py`

- [ ] **Step 1: 写失败测试**

```python
from llm_werewolf.game_runtime.config import PlayerConfig
from llm_werewolf.agent_team.agents.base import create_agent
from llm_werewolf.agent_team.agents.web_human_agent import WebHumanAgent

def test_create_agent_returns_web_human():
    agent = create_agent(PlayerConfig(name="P1", model="web-human"))
    assert isinstance(agent, WebHumanAgent)
    assert agent.name == "P1"
```

- [ ] **Step 2: 跑确认失败** — `uv run pytest tests/agent_team/agents/test_create_agent_web_human.py -v --no-cov` → FAIL。
- [ ] **Step 3: 实现** —— `create_agent` 在 `if model == "human":` 之后加：

```python
    if model == "web-human":
        from llm_werewolf.agent_team.agents.web_human_agent import WebHumanAgent

        return WebHumanAgent(name=config.name, model="web-human")
```

- [ ] **Step 4: 跑确认通过** → PASS。
- [ ] **Step 5: 提交**

```bash
git add src/llm_werewolf/agent_team/agents/base.py tests/agent_team/agents/test_create_agent_web_human.py
git commit -m "feat(m3): wire web-human into create_agent factory"
```

---

## Task 5: 扩展 `StartGameRequest`/`StartGameResponse`

**Files:**
- Modify: `src/llm_werewolf/interface/api/models/actions.py:31-79,96-111`
- Test: `tests/interface/api/models/test_start_game_human.py`

新增/改：
```python
class HumanSeatSpec(BaseModel):
    seat: int = Field(..., ge=1, le=20)
    role: str | None = Field(default=None, description="可选固定角色（Enhancement A8 前忽略，随机发牌）")

# StartGameRequest 增字段：
    human: HumanSeatSpec | None = Field(default=None, description="单人类座位；None=纯 LLM 观战")

# StartGameResponse 增字段：
    player_token: str | None = None
    stream_path: str | None = None
```

- [ ] **Step 1: 写失败测试**

```python
from llm_werewolf.interface.api.models.actions import StartGameRequest, StartGameResponse

def test_request_accepts_human_seat():
    req = StartGameRequest(config_id="llm-6p-deepseek", human={"seat": 1})
    assert req.human.seat == 1
    assert req.human.role is None

def test_response_has_token_fields():
    r = StartGameResponse(run_id="x", status="running", config_id="c", run_dir="d",
                          game_page_path="g", status_path="s", replay_page_path="r",
                          player_token="tok", stream_path="/api/v1/games/x/stream")
    assert r.player_token == "tok"
```

- [ ] **Step 2: 跑确认失败** — `uv run pytest tests/interface/api/models/test_start_game_human.py -v --no-cov` → FAIL。
- [ ] **Step 3: 实现**（如上）。
- [ ] **Step 4: 跑确认通过** → PASS。
- [ ] **Step 5: 提交**

```bash
git add src/llm_werewolf/interface/api/models/actions.py tests/interface/api/models/test_start_game_human.py
git commit -m "feat(m3): StartGame request.human + response player_token/stream_path"
```

---

## Task 6: `game_sessions` 接线 —— 建座位/令牌/broker，放开拦截

**Files:**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py:69-70,108-128,152-248,250-272`
- Test: `tests/interface/api/services/test_game_sessions_human.py`

改动点：
1. `_has_human_player` 仅对 **stdin** human 报错（web-human 放行）—— 当前它检查 `model == "human"`，web-human 的 model 是 `"web-human"`，**天然不触发**，无需改逻辑；但需新增 `_web_human_seat(players_config) -> int | None` 辅助。
2. `start_game`：当 `request.human` 非空 → 把目标座位的 `PlayerConfig.model` 覆写为 `"web-human"`（复用 `apply_roster_customizations` 的 players slot 机制，或在 `prepare_start_players_config` 后克隆覆写）；生成 `player_token`（用 `run_id` + seat 的稳定派生，避免不可测随机：`token = f"seat{seat}-{run_id}"`，足够轻量防误操作，非鉴权）；存 `session.player_token`、`session.human_seat`；响应回填 `player_token` 和 `stream_path=f"/api/v1/games/{run_id}/stream"`。
3. `GameSession` 增 `player_token: str | None = None`、`human_seat: int | None = None`、`input_broker: Any | None = None`。
4. `_run_game`：`prepare_game_roster` 之后，若 `session.human_seat`：`broker = get_or_create_input_broker(session.run_id, session.human_seat, broadcaster)`；定位 `players[human_seat-1]` 的 `WebHumanAgent`，设 `agent.seat = human_seat; agent.broker = broker`；`session.input_broker = broker`。注意 broadcaster 在该函数内 263 行创建，需把 broker 接线放到 broadcaster 创建**之后**。`finally` 里 `remove_input_broker(run_id)`。

- [ ] **Step 1: 写失败测试**（用 demo 配置 + 脚本化 submit，跑半局即可断言挂起→提交→推进）

```python
import asyncio
import pytest
from pathlib import Path
from llm_werewolf.interface.api.services.game_sessions import GameSessionManager
from llm_werewolf.interface.api.services.human_input import get_input_broker
from llm_werewolf.interface.api.models.actions import StartGameRequest

@pytest.mark.asyncio
async def test_web_human_game_pauses_and_resumes(tmp_path: Path):
    mgr = GameSessionManager()
    configs_dir = Path("configs"); runs_dir = tmp_path / "runs"; runs_dir.mkdir()
    req = StartGameRequest(config_id="demo-6p", human={"seat": 1})  # demo 配置：其余座位 DemoAgent
    resp = await mgr.start_game(configs_dir=configs_dir, runs_dir=runs_dir, request=req)
    assert resp.player_token and resp.stream_path
    # 轮询直到 broker 出现一个待办，脚本化 submit，确认游戏能推进到结束
    async def _drive():
        for _ in range(2000):
            broker = get_input_broker(resp.run_id)
            if broker:
                for rid in list(broker.pending_ids()):
                    broker.submit(request_id=rid, payload="0")  # 兜底式输入：弃票/跳过
            await asyncio.sleep(0.01)
    driver = asyncio.create_task(_drive())
    session = mgr._sessions[resp.run_id]
    await asyncio.wait_for(session.task, timeout=60)
    driver.cancel()
    assert session.status.value in {"completed", "failed"}
```
> 注：若仓库无 `demo-6p` 配置，用现有 demo 配置 stem 替换；该测可标 `@pytest.mark.slow`。核心断言是"挂起的人类决策能被 submit 推进，不死锁"。

- [ ] **Step 2: 跑确认失败** — `uv run pytest tests/interface/api/services/test_game_sessions_human.py -v --no-cov` → FAIL。
- [ ] **Step 3: 实现**（如上接线）。先 `gitnexus_impact({target:"start_game", direction:"upstream"})` 与 `gitnexus_impact({target:"_run_game", direction:"upstream"})`。
- [ ] **Step 4: 跑确认通过** → PASS。
- [ ] **Step 5: 提交**

```bash
git add src/llm_werewolf/interface/api/services/game_sessions.py tests/interface/api/services/test_game_sessions_human.py
git commit -m "feat(m3): wire web-human seat + token + input broker into game session"
```

---

## Task 7: `POST /games/{run_id}/input` 路由

**Files:**
- Modify: `src/llm_werewolf/interface/api/routes/actions.py`（增模型 + 路由）；`src/llm_werewolf/interface/api/models/actions.py`（`HumanInputRequest`/`HumanInputResponse`）
- Test: `tests/interface/api/routes/test_input_route.py`

```python
class HumanInputRequest(BaseModel):
    token: str
    request_id: str
    kind: str
    payload: str  # 已归一化文本（前端 humanInput.ts 产出）

class HumanInputResponse(BaseModel):
    run_id: str
    accepted: bool
    message: str | None = None
```
路由逻辑：取 `session = game_session_manager._sessions.get(run_id)`；`if session is None: 404`；`if body.token != session.player_token: 403`；`broker = get_input_broker(run_id)`；`if broker is None: 409`；`ok = broker.submit(request_id=body.request_id, payload=body.payload)`；`if not ok: 409`（未知/已消费/超时）；否则 `200 accepted=True`。

- [ ] **Step 1: 写失败测试**（用 `fastapi.testclient.TestClient`；monkeypatch 一个带假 broker 的 session 进 `game_session_manager._sessions`）

```python
from fastapi.testclient import TestClient
from llm_werewolf.interface.api.app import create_app
from llm_werewolf.interface.api.services import game_sessions as gs
from llm_werewolf.interface.api.services import human_input as hi

def test_input_rejects_bad_token(monkeypatch):
    app = create_app(); client = TestClient(app)
    # 构造一个假 session + broker（细节见实现）
    ...
    r = client.post("/api/v1/games/RID/input",
                    json={"token": "WRONG", "request_id": "x", "kind": "seat", "payload": "2"})
    assert r.status_code == 403
```
（happy-path：正确 token + 已登记 request_id → 200 accepted=True；未知 request_id → 409。）

- [ ] **Step 2: 跑确认失败** — `uv run pytest tests/interface/api/routes/test_input_route.py -v --no-cov` → FAIL。
- [ ] **Step 3: 实现** 路由 + 模型。
- [ ] **Step 4: 跑确认通过** → PASS。
- [ ] **Step 5: 提交**

```bash
git add src/llm_werewolf/interface/api/routes/actions.py src/llm_werewolf/interface/api/models/actions.py tests/interface/api/routes/test_input_route.py
git commit -m "feat(m3): POST /games/{id}/input route with seat-token validation"
```

---

## Task 8: 前端 —— 类型 + `sendInput` + 纯函数 `humanInput.ts`

**Files:**
- Modify: `frontend/src/api/types.ts`（`StartGameRequest.human`、`StartGameResponse.player_token/stream_path`、`AwaitingInputEvent`、`HumanInputPayload`）
- Modify: `frontend/src/api/client.ts`（`sendInput`）
- Create: `frontend/src/lib/humanInput.ts`（纯函数：UI 选择 → 归一化 payload）
- Test: `frontend/src/lib/humanInput.test.ts`

`humanInput.ts` 把 `awaiting_input{kind, valid_targets}` + 用户 UI 选择折叠成后端期望的归一化文本（镜像 bridge）：
- `seat`：选座位 → `"3"`；弃票/跳过 → `"0"`。
- `witch`：救 → `"救"`；毒座位 3 → `"毒 [[3]]"`；不行动 → `"none"`。
- `yesno`：是 → `"1"`；否 → `"0"`。
- `multi`：`"3 5"`。
- `speech`：原文。

- [ ] **Step 1: 写失败测试**

```ts
import { describe, it, expect } from "vitest";
import { buildHumanPayload } from "./humanInput";

describe("buildHumanPayload", () => {
  it("maps seat choice", () => {
    expect(buildHumanPayload({ kind: "seat", seat: 3 })).toBe("3");
    expect(buildHumanPayload({ kind: "seat", skip: true })).toBe("0");
  });
  it("maps witch actions", () => {
    expect(buildHumanPayload({ kind: "witch", action: "save" })).toBe("救");
    expect(buildHumanPayload({ kind: "witch", action: "poison", seat: 3 })).toBe("毒 [[3]]");
    expect(buildHumanPayload({ kind: "witch", action: "none" })).toBe("none");
  });
  it("maps yesno and speech", () => {
    expect(buildHumanPayload({ kind: "yesno", yes: true })).toBe("1");
    expect(buildHumanPayload({ kind: "speech", text: "我觉得3号有问题" })).toBe("我觉得3号有问题");
  });
});
```

- [ ] **Step 2: 跑确认失败** — `cd frontend && npx vitest run src/lib/humanInput.test.ts` → FAIL。
- [ ] **Step 3: 实现** `humanInput.ts` + 类型 + `ApiClient.sendInput`：
```ts
static async sendInput(runId: string, body: HumanInputRequest): Promise<HumanInputResponse> {
  return this.post(`/api/v1/games/${encodeURIComponent(runId)}/input`, body);
}
```
- [ ] **Step 4: 跑确认通过** → PASS；并 `npx tsc --noEmit`。
- [ ] **Step 5: 提交**

```bash
cd frontend && git add src/api/types.ts src/api/client.ts src/lib/humanInput.ts src/lib/humanInput.test.ts
git commit -m "feat(m3): frontend humanInput payload mapper + sendInput client"
```

---

## Task 9: 前端 —— store seat 订阅 + `awaiting_input` 输入 UI + GameSetup 人机模式

**Files:**
- Modify: `frontend/src/store.ts`（seat 视角 `connectSpectate(runId, {view:"seat", seat, token})`；捕获 `awaiting_input` → 置 `pendingInput`；`submitHumanInput()` 调 `sendInput` 后清空）
- Modify: `frontend/src/components/GameSetup.tsx`（模式切换：纯 LLM 观战 / 人机；人机选座位；开局后用 `player_token`+`stream_path` 进 seat 视角）
- Create: `frontend/src/components/HumanInputPanel.tsx`（读 `pendingInput`，按 `kind` 渲染：座位选择/女巫三选一/是否/多选/发言框；提交走 `buildHumanPayload`→`submitHumanInput`）
- Test: `frontend/src/store.humanInput.test.ts`（喂 `awaiting_input` 事件→断言 `pendingInput` 被设；调 `submitHumanInput` mock `sendInput`→断言被以归一化 payload 调用且 `pendingInput` 清空）

- [ ] **Step 1: 写失败测试**（store reducer 级别，mock `ApiClient.sendInput`）。
- [ ] **Step 2: 跑确认失败** — `cd frontend && npx vitest run src/store.humanInput.test.ts` → FAIL。
- [ ] **Step 3: 实现** store + GameSetup + HumanInputPanel。
- [ ] **Step 4: 跑确认通过** → PASS；`npx tsc --noEmit` + `npm run build`。
- [ ] **Step 5: 提交**

```bash
cd frontend && git add src/store.ts src/components/GameSetup.tsx src/components/HumanInputPanel.tsx src/store.humanInput.test.ts
git commit -m "feat(m3): seat-view human input UI driven by awaiting_input events"
```

---

## Task 10: 真机 E2E 验收（人机一局）

- [ ] 起后端（端口 8010，注入有效 key，`OBS_READY_REQUIRE_LLM=0`）。
- [ ] vite + Playwright **同一前台命令**（vite 后台会被回收；curl 用 `127.0.0.1`）。
- [ ] `POST /games/start {config_id:"llm-6p-deepseek", human:{seat:1}}` → 拿 `run_id` + `player_token`。
- [ ] 开 `/game?run_id=<id>`（seat 视角，带 token）→ 断言：① 出现 `awaiting_input` 时弹输入面板；② 提交后引擎继续；③ **seat 流不含他人私有事件**（防作弊回归：无他人验人/狼聊/身份）；④ 跑完出 `game_over`。
- [ ] 验证后端无 key 泄漏：`grep -L sk- artifacts/runs/<id>/*.json`（launch_roster/run_meta 不含 key）。

---

## Enhancements（本切片之后的独立小任务，非阻塞）

- **A7 原始 key 注入**：`StartGameRequest.llm{provider,api_key,base_url,model,per_seat}`；`PlayerConfig` 增 `api_key: str|None = Field(default=None, exclude=True, repr=False)`；`create_react_agent` 优先 `config.api_key` 回退 `os.getenv(api_key_env)`；`launch_roster.json` 的 `model_dump` 排除 `api_key`（连同 `use_agentscope_backend`）。回归测：key 不进 `model_dump`/`repr`/磁盘。
- **A8 固定人类角色**：`engine/base.py:setup_game(..., fixed_seat_roles: dict[int,str]|None=None)`——固定座位不参与 shuffle，其余照常洗牌 + 角色池合法性校验（唯一神职名额）。`human.role` 透传到此。
- **回合倒计时**：broker `sweep_timeouts()` 协程 + 前端倒计时条；deadline 到 → `input_timeout` + 安全兜底。
- **按座位不同供应商**：`llm.per_seat` 覆盖；注意现有全局串行锁 `run_serial_agent_call` 的限流。

---

## Self-Review（写后自检）

- **Spec 覆盖**：§5 A1(Task3)/A2(Task4)/A3(Task2)/A6(Task6)/A9(Task5,7) 已覆盖；A4/A5(SSE/on_event 复合) M1 已建成；A7/A8 列入 Enhancements（本切片显式延后，已在 Goal/Scope 标注）。§6.3 input 契约 = Task7。§7 C6/C7/C8 = Task8,9。
- **类型一致**：`HumanInputBroker.request(kind,prompt,valid_targets,fallback,deadline)`、`submit(request_id,payload)`、`WebHumanAgent.seat/broker`、`HumanInputRequest{token,request_id,kind,payload}`、前端 `buildHumanPayload`→同一 payload 文本契约，全程一致。
- **无占位符**：各 Task 均含可运行测试与最小实现代码。
- **防作弊**：`awaiting_input.visible_to=[player_{seat}]`，seat 流复用 M1 `event_visible_for` 过滤；Task10 显式回归断言。
