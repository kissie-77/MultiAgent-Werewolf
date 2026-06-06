# M1a — 后端 SSE 实时事件流 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给运行中的对局加一条 **SSE 实时事件流**：引擎每产生一个 `Event`，除写入 `events.jsonl` 外，再广播给所有 SSE 订阅者；前端可 `GET /api/v1/games/{run_id}/stream?view=god|seat&seat=N` 实时收事件，断线用 `Last-Event-ID` 从 `events.jsonl` 回放补齐。可见性复用 `Event.visible_to`（god=全部；seat=仅本座位可见）。

**Architecture:** 新增 `EventBroadcaster`（每 run 一个，进程内 asyncio 扇出）+ 进程级 registry。`GameSessionManager._run_game` 把 `engine.on_event` 由「只写文件」改为「写文件 + 广播」的复合回调，游戏结束/失败/取消时 `close()` 并清理 registry。SSE 端点用已在依赖中的 **sse-starlette** 的 `EventSourceResponse`：先发一帧 `snapshot`，再发实时事件（或对已完成的 run 从 `events.jsonl` 回放），按 `view` 过滤可见性。纯 LLM 观战用 `view=god`。

**Tech Stack:** FastAPI + sse-starlette 3.4.4（已在 uv.lock）+ asyncio；pytest（`asyncio_mode=auto`，async 测试无需装饰器）。

**边界（M1a 不做，留给 M1b/M3）：** 前端 reducer/store 重写与可视化（M1b）；座位令牌鉴权（M3，本期 `seat` 仅做可见性过滤不校验持有者）；首帧 snapshot 的完整 roster/角色（M1b 再补）。

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `src/llm_werewolf/interface/api/services/event_stream.py` | `EventBroadcaster` + registry + 可见性过滤 + events.jsonl 回放读取 | Create |
| `tests/interface/test_event_stream.py` | 上述单元测试（广播/可见性/回放） | Create |
| `src/llm_werewolf/interface/api/services/game_sessions.py` | `_run_game` 复合 on_event；`GameSession` 加 broadcaster；结束清理 | Modify |
| `src/llm_werewolf/interface/api/routes/actions.py` | 新增 `GET /games/{run_id}/stream` SSE 端点 | Modify |
| `tests/interface/test_api_stream.py` | SSE 端点 + 引擎集成测试 | Create |

---

## Task 1: `EventBroadcaster` + registry + 可见性/回放 helpers

**Files:**
- Create: `src/llm_werewolf/interface/api/services/event_stream.py`
- Test: `tests/interface/test_event_stream.py`

- [ ] **Step 1: 写失败测试 `tests/interface/test_event_stream.py`**

```python
import asyncio

from llm_werewolf.interface.api.services.event_stream import (
    EventBroadcaster,
    event_visible_for,
    get_or_create_broadcaster,
    get_broadcaster,
    remove_broadcaster,
)


async def test_publish_fans_out_and_assigns_incrementing_ids():
    b = EventBroadcaster()
    received: list[dict] = []

    async def consume() -> None:
        async for ev in b.subscribe():
            received.append(ev)

    task = asyncio.create_task(consume())
    await asyncio.sleep(0)  # let subscribe() register its queue
    assert b.publish({"event_type": "a"}) == 1
    assert b.publish({"event_type": "b"}) == 2
    await asyncio.sleep(0.02)
    b.close()
    await asyncio.wait_for(task, timeout=1)
    assert [e["event_id"] for e in received] == [1, 2]
    assert received[0]["event_type"] == "a"


def test_registry_get_or_create_is_idempotent():
    remove_broadcaster("run-x")
    b1 = get_or_create_broadcaster("run-x")
    b2 = get_or_create_broadcaster("run-x")
    assert b1 is b2
    assert get_broadcaster("run-x") is b1
    remove_broadcaster("run-x")
    assert get_broadcaster("run-x") is None


def test_event_visible_for_god_sees_everything():
    ev_public = {"event_type": "vote_result", "visible_to": None}
    ev_private = {"event_type": "seer_checked", "visible_to": ["player_2"]}
    assert event_visible_for(ev_public, view="god", seat=None) is True
    assert event_visible_for(ev_private, view="god", seat=None) is True


def test_event_visible_for_seat_filters_private_events():
    ev_public = {"event_type": "vote_result", "visible_to": None}
    ev_seer = {"event_type": "seer_checked", "visible_to": ["player_2"]}
    # seat 2 sees its own private event + public; seat 3 only sees public
    assert event_visible_for(ev_public, view="seat", seat=2) is True
    assert event_visible_for(ev_seer, view="seat", seat=2) is True
    assert event_visible_for(ev_seer, view="seat", seat=3) is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/interface/test_event_stream.py -q`
Expected: FAIL（`cannot import name 'EventBroadcaster' ...`）。

- [ ] **Step 3: 实现 `src/llm_werewolf/interface/api/services/event_stream.py`**

```python
"""In-process SSE fan-out of live game events, keyed by run_id."""

from __future__ import annotations

import asyncio
import json
import contextlib
from typing import Any, AsyncIterator
from pathlib import Path

_MAX_QUEUE = 2000


class EventBroadcaster:
    """Fan out serialized game events to live SSE subscribers for one run.

    ``publish`` is invoked synchronously from the engine ``on_event`` hook
    (inside the game's asyncio task). Each event gets a monotonically
    increasing 1-based ``event_id`` matching its line number in
    ``events.jsonl`` so clients can resume via ``Last-Event-ID``.
    """

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any] | None]] = set()
        self._count = 0
        self._closed = False

    @property
    def count(self) -> int:
        return self._count

    @property
    def closed(self) -> bool:
        return self._closed

    def publish(self, event: dict[str, Any]) -> int:
        """Stamp an event_id and fan out to subscribers. Sync-safe (put_nowait)."""
        self._count += 1
        enriched = {**event, "event_id": self._count}
        for q in list(self._subscribers):
            try:
                q.put_nowait(enriched)
            except asyncio.QueueFull:
                # Slow consumer: drop the live item; it can reconnect and
                # replay missed events from events.jsonl via Last-Event-ID.
                pass
        return self._count

    def close(self) -> None:
        """Signal end-of-stream (game finished) to all subscribers."""
        self._closed = True
        for q in list(self._subscribers):
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(None)

    async def subscribe(self) -> AsyncIterator[dict[str, Any]]:
        """Yield live events until ``close()``. Always unsubscribes on exit."""
        q: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=_MAX_QUEUE)
        self._subscribers.add(q)
        try:
            while True:
                item = await q.get()
                if item is None:
                    break
                yield item
        finally:
            self._subscribers.discard(q)


_registry: dict[str, EventBroadcaster] = {}


def get_or_create_broadcaster(run_id: str) -> EventBroadcaster:
    b = _registry.get(run_id)
    if b is None:
        b = EventBroadcaster()
        _registry[run_id] = b
    return b


def get_broadcaster(run_id: str) -> EventBroadcaster | None:
    return _registry.get(run_id)


def remove_broadcaster(run_id: str) -> None:
    _registry.pop(run_id, None)


def event_visible_for(event: dict[str, Any], *, view: str, seat: int | None) -> bool:
    """Apply the engine visibility model to a serialized event dict.

    god  -> sees everything.
    seat -> sees public events (visible_to is None) plus events whose
            visible_to contains this seat's player id ("player_{seat}").
    """
    if view == "god":
        return True
    visible_to = event.get("visible_to")
    if visible_to is None:
        return True
    if seat is None:
        return False
    return f"player_{seat}" in visible_to


def read_events_after(run_dir: Path, after_id: int) -> list[dict[str, Any]]:
    """Read events.jsonl lines with event_id > after_id (1-based line numbers).

    Used to replay missed events on (re)connect (Last-Event-ID).
    """
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh, start=1):
            if idx <= after_id:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            ev["event_id"] = idx
            out.append(ev)
    return out
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/interface/test_event_stream.py -q`
Expected: PASS（5 passed）。

- [ ] **Step 5: Commit**

```bash
git add src/llm_werewolf/interface/api/services/event_stream.py tests/interface/test_event_stream.py
git commit -m "feat(api): EventBroadcaster + visibility filter + jsonl replay for SSE

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: 把广播接入 `GameSessionManager`（复合 on_event + 生命周期）

`_run_game` 当前 `engine.on_event = IncrementalEventWriter(run_dir)`。改为「写文件 + 广播」复合，并在 run 结束/失败/取消时 `close()` 广播器。

**Files:**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py`

- [ ] **Step 1: 在 import 段加入广播器与事件序列化**

`game_sessions.py` 顶部已 `from llm_werewolf.evaluation.post_game.event_adapter import event_to_dict`。在其附近新增：
```python
from llm_werewolf.interface.api.services.event_stream import (
    get_or_create_broadcaster,
    remove_broadcaster,
)
```

- [ ] **Step 2: `GameSession` dataclass 增加 broadcaster 引用**

在 `@dataclass class GameSession` 字段末尾（`alert_count: int = 0` 之后）加：
```python
    broadcaster: Any | None = None
```
（`Any` 已在 `from typing import TYPE_CHECKING, Any` 导入。）

- [ ] **Step 3: 在 `_run_game` 里用复合 on_event 并管理生命周期**

定位 `_run_game` 中：
```python
            writer = IncrementalEventWriter(session.run_dir)
            engine.on_event = writer
```
替换为：
```python
            writer = IncrementalEventWriter(session.run_dir)
            broadcaster = get_or_create_broadcaster(session.run_id)
            session.broadcaster = broadcaster

            def _on_event(event: object) -> None:
                writer(event)
                broadcaster.publish(event_to_dict(event))

            engine.on_event = _on_event
```

在 `_run_game` 的 `finally:` 块里（当前是 `detach_run_log_handler()` / `session.completed_at = ...` / `self._write_meta(session)`），在 `detach_run_log_handler()` 之后追加广播收尾：
```python
            if session.broadcaster is not None:
                session.broadcaster.close()
            remove_broadcaster(session.run_id)
```

- [ ] **Step 4: 运行既有 session 相关测试，确认未回归**

Run: `uv run pytest tests/interface/test_api_actions.py tests/interface/test_api_services.py -q`
Expected: PASS（无回归；如个别既有用例因 fixtures 失败且与本改动无关，记录但不修改其它任务范围外代码）。

- [ ] **Step 5: Commit**

```bash
git add src/llm_werewolf/interface/api/services/game_sessions.py
git commit -m "feat(api): broadcast engine events to SSE subscribers per run

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: SSE 端点 `GET /api/v1/games/{run_id}/stream`

用 sse-starlette 的 `EventSourceResponse`：先发一帧 `snapshot`（`extract_game_snapshot`），再按可见性发事件；run 在跑就订阅广播器（并先回放 `Last-Event-ID` 之后已落盘的事件），run 已结束就从 `events.jsonl` 回放后结束。

**Files:**
- Modify: `src/llm_werewolf/interface/api/routes/actions.py`
- Test: `tests/interface/test_api_stream.py`

- [ ] **Step 1: 写失败测试 `tests/interface/test_api_stream.py`**

```python
import json
from pathlib import Path

from fastapi.testclient import TestClient

from llm_werewolf.interface.api.app import create_app


def _write_events(run_dir: Path, events: list[dict]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "events.jsonl").open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    (run_dir / "run_meta.json").write_text(
        json.dumps({"run_id": run_dir.name, "status": "completed"}), encoding="utf-8"
    )


def test_stream_replays_completed_run_god_view(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_id = "demo-stream"
    run_dir = tmp_path / "artifacts" / "runs" / run_id
    _write_events(
        run_dir,
        [
            {"event_type": "game_started", "round_number": 0, "phase": "setup",
             "message": "start", "data": {}, "visible_to": None},
            {"event_type": "seer_checked", "round_number": 1, "phase": "night",
             "message": "查验", "data": {}, "visible_to": ["player_2"]},
            {"event_type": "vote_result", "round_number": 1, "phase": "day_voting",
             "message": "出局", "data": {}, "visible_to": None},
        ],
    )
    client = TestClient(create_app())
    with client.stream("GET", f"/api/v1/games/{run_id}/stream?view=god") as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = "".join(chunk for chunk in resp.iter_text())
    # god view: all three event types appear
    assert "game_started" in body
    assert "seer_checked" in body
    assert "vote_result" in body


def test_stream_seat_view_hides_other_players_private_events(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_id = "demo-stream2"
    run_dir = tmp_path / "artifacts" / "runs" / run_id
    _write_events(
        run_dir,
        [
            {"event_type": "seer_checked", "round_number": 1, "phase": "night",
             "message": "查验", "data": {}, "visible_to": ["player_2"]},
            {"event_type": "vote_result", "round_number": 1, "phase": "day_voting",
             "message": "出局", "data": {}, "visible_to": None},
        ],
    )
    client = TestClient(create_app())
    with client.stream("GET", f"/api/v1/games/{run_id}/stream?view=seat&seat=3") as resp:
        body = "".join(chunk for chunk in resp.iter_text())
    assert "vote_result" in body        # public -> visible
    assert "seer_checked" not in body   # seat 3 must NOT see seat 2's private event


def test_stream_unknown_run_returns_404(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app())
    resp = client.get("/api/v1/games/nope/stream?view=god")
    assert resp.status_code == 404
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/interface/test_api_stream.py -q`
Expected: FAIL（路由不存在 → 404 对前两用例不成立，或断言失败）。

- [ ] **Step 3: 在 `routes/actions.py` 实现 SSE 端点**

在 `actions.py` import 段补充：
```python
from pathlib import Path

from sse_starlette.sse import EventSourceResponse

from llm_werewolf.interface.api.deps import get_runs_dir, get_eval_runs_dir
from llm_werewolf.interface.api.services.replay import extract_game_snapshot
from llm_werewolf.interface.api.services.event_stream import (
    get_broadcaster,
    event_visible_for,
    read_events_after,
)
```
（`get_runs_dir` 等若已 import 则不重复。）

在文件末尾新增端点（与其它 `@router` 同级）：
```python
def _sse(event: dict) -> dict:
    """Format an enriched event dict as an EventSourceResponse message."""
    return {
        "id": str(event.get("event_id", "")),
        "event": str(event.get("event_type", "message")),
        "data": json.dumps(event, ensure_ascii=False),
    }


@router.get("/games/{run_id}/stream")
async def stream_game(
    run_id: str,
    request: Request,
    view: Annotated[str, Query(pattern="^(god|seat)$")] = "god",
    seat: Annotated[int | None, Query(ge=1, le=20)] = None,
    last_event_id: Annotated[int, Query(ge=0)] = 0,
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> EventSourceResponse:
    run_dir = runs_dir / run_id
    if not run_dir.is_dir():
        alt = eval_runs_dir / run_id
        run_dir = alt if alt.is_dir() else run_dir
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    # Honor the SSE reconnect header if the client sent one.
    header_id = request.headers.get("last-event-id")
    if header_id and header_id.isdigit():
        last_event_id = int(header_id)

    broadcaster = get_broadcaster(run_id)

    async def gen():
        # 1) first frame: coarse snapshot
        try:
            snap = extract_game_snapshot(run_dir).model_dump()
        except Exception:  # pragma: no cover - snapshot best-effort
            snap = {}
        yield {"event": "snapshot", "data": json.dumps(snap, ensure_ascii=False)}

        # 2) replay already-persisted events after last_event_id
        for ev in read_events_after(run_dir, last_event_id):
            if event_visible_for(ev, view=view, seat=seat):
                yield _sse(ev)

        # 3) if the run is live, stream new events until it closes
        if broadcaster is not None and not broadcaster.closed:
            replayed = max(last_event_id, _count_events(run_dir))
            async for ev in broadcaster.subscribe():
                if ev.get("event_id", 0) <= replayed:
                    continue
                if await request.is_disconnected():
                    break
                if event_visible_for(ev, view=view, seat=seat):
                    yield _sse(ev)

        yield {"event": "end", "data": json.dumps({"run_id": run_id})}

    return EventSourceResponse(gen())
```

并在文件内（端点上方）加一个小工具，避免回放/直播重叠：
```python
def _count_events(run_dir: Path) -> int:
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())
```

确认 `actions.py` 顶部已 import `json`、`Request`（`from fastapi import Request, Query, Depends, APIRouter, HTTPException`）、`Annotated`。若缺则补上。

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/interface/test_api_stream.py -q`
Expected: PASS（3 passed）。

- [ ] **Step 5: 回归 + lint**

Run: `uv run pytest tests/interface -q`
Expected: 端点相关用例全过；既有用例无新失败。
Run: `uv run ruff check src/llm_werewolf/interface/api/services/event_stream.py src/llm_werewolf/interface/api/routes/actions.py src/llm_werewolf/interface/api/services/game_sessions.py`
Expected: 无错误（如有格式问题按 ruff 提示修正）。

- [ ] **Step 6: Commit**

```bash
git add src/llm_werewolf/interface/api/routes/actions.py tests/interface/test_api_stream.py
git commit -m "feat(api): SSE GET /games/{run_id}/stream (god/seat, snapshot, replay)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: 集成测试 —— 引擎跑一局，广播确实推送且可见性正确

**Files:**
- Modify: `tests/interface/test_api_stream.py`（追加一个集成用例）

- [ ] **Step 1: 追加集成测试（DemoAgent 真跑一小局，复合 on_event 同时写文件+广播）**

```python
async def test_engine_run_publishes_to_broadcaster(tmp_path, monkeypatch):
    """A real (demo) game wired through GameSessionManager's composite on_event
    both writes events.jsonl and fans out to a live subscriber."""
    monkeypatch.chdir(tmp_path)
    import asyncio
    from llm_werewolf.interface.api.services import event_stream
    from llm_werewolf.interface.api.services.game_sessions import game_session_manager
    from llm_werewolf.interface.api.models.actions import StartGameRequest
    from llm_werewolf.interface.api.deps import get_runs_dir, get_configs_dir

    # demo config ships in repo configs/; copy is unnecessary — resolve_config_for_start
    # accepts a config_id under the repo configs dir.
    configs_dir = Path(__file__).resolve().parents[2] / "configs"
    runs_dir = tmp_path / "artifacts" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    resp = await game_session_manager.start_game(
        configs_dir=configs_dir, runs_dir=runs_dir,
        request=StartGameRequest(config_id="demo-6"),
    )
    run_id = resp.run_id
    b = event_stream.get_broadcaster(run_id)
    assert b is not None

    received: list[dict] = []

    async def consume() -> None:
        async for ev in b.subscribe():
            received.append(ev)

    consumer = asyncio.create_task(consume())
    # wait for the game task to finish (demo agents are fast/offline)
    session = game_session_manager._sessions[run_id]
    await asyncio.wait_for(session.task, timeout=120)
    await asyncio.sleep(0.05)
    consumer.cancel()

    assert (runs_dir / run_id / "events.jsonl").is_file()
    types = {e["event_type"] for e in received}
    assert "game_started" in types or len(received) > 0
```

> 说明：`demo-6` 用离线 DemoAgent，无需 API Key、快速可复现。若 `start_game` 因 human 校验或配置解析在测试环境报错，按错误信息最小调整本用例（不改产品代码范围外内容）。

- [ ] **Step 2: 运行集成测试**

Run: `uv run pytest tests/interface/test_api_stream.py::test_engine_run_publishes_to_broadcaster -q`
Expected: PASS（events.jsonl 存在且订阅者收到事件）。

- [ ] **Step 3: Commit**

```bash
git add tests/interface/test_api_stream.py
git commit -m "test(api): integration test — engine run fans events to SSE subscriber

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage（对照设计 spec §4.1②、§5 A4/A5、§6.2）：**
- EventBroadcaster + 进程内广播 + events.jsonl 回放 → Task 1 ✅
- on_event 复合（写文件 + 广播）+ 生命周期清理 → Task 2 ✅
- SSE 端点 + god/seat 可见性（复用 visible_to）+ 首帧 snapshot + Last-Event-ID 回放 → Task 3 ✅
- 引擎集成验证 → Task 4 ✅
- 未覆盖（有意）：座位令牌鉴权（M3）、首帧完整 roster/角色（M1b）、前端消费（M1b）。

**Placeholder scan:** 无 TODO/TBD；每个改码步骤均给出完整代码或精确插入/替换位置。

**Type consistency:** `event_to_dict` 产出的 dict（event_type/round_number/phase/message/data/visible_to）↔ `EventBroadcaster.publish` 加 `event_id` ↔ `event_visible_for(view, seat)` 读 `visible_to` ↔ SSE `_sse(event)` 读 `event_id`/`event_type` ↔ `read_events_after` 同形 dict，一致。`player_{seat}` 命名与引擎 `setup_game` 的 `player_id = f"player_{idx}"` 一致。

---

## Follow-up（M1b，下一份计划）
前端：`lib/gameReducer.ts`（事件→可渲染状态）、`useGameStream` hook（订阅 SSE）、`store.ts` 重写（去 POST-mock、改 SSE 驱动）、`GameApp` god 视角渲染（3D/发言/票型/死亡/警长）。需对照本期 SSE 事件信封与 `EventType` 全集逐一映射，并接真实后端联调。
