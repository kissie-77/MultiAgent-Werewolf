# M1b — 前端实时观战（SSE → 画面） Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 M1a 建好的 SSE 事件流接到画面：浏览器打开 `/game?run_id=<id>` 即以**上帝视角实时观战**一局纯 LLM 对局 —— 座位/角色、昼夜阶段、发言流、死亡/出局、警长，随后端事件实时刷新。复用现有 3D/发言/卡牌 UI（把事件流 reduce 成现有 `GameState` 形状）。

**Architecture:** 前端用浏览器原生 `EventSource` 订阅 `/api/v1/games/{run_id}/stream?view=god`（自带重连 + `Last-Event-ID`）。新增纯函数 `gameReducer(state, sseEvent)` 把后端 `Event`（`event_type/round_number/phase/message/data/visible_to`）折叠成现有 `GameState`（`players/phase/currentSpeakerId/speechLogs/winner/...`）。`store.ts` 增加 `connectSpectate(runId)`（订阅+reduce），`GameApp` 在 URL 带 `run_id` 时进入观战模式。后端补一个 **god 视角 roster**（座位→角色/阵营），M1a 的 snapshot 首帧在 `view=god` 时带上它，前端据此渲染带身份的座位。

**Tech Stack:** React + Zustand + 浏览器 `EventSource`；Vitest（reducer 纯函数 TDD）；后端 FastAPI + pytest（roster 持久化 + snapshot 富化）。

**边界（M1b 不做）：** 人类输入/座位视角（M3）；信念矩阵/投票意向实时面板接真数据（M2）；每个 EventType 的精细动画/音效（先保证核心可见，迭代细化）。

---

## 设计要点：后端事件 → 前端 GameState 映射

| 后端 `event_type` | 前端 reduce 效果 |
|---|---|
| `snapshot`(首帧, view=god 带 roster) | 初始化 `players[]`（seat→name/role/isAlive），`phase`，`dayNumber`，`sheriffId` |
| `phase_changed` / 任意事件的 `phase` | `phase`：`night→NIGHT_WOLF`、`day_discussion→DAY_DEBATE`、`day_voting→DAY_VOTE`、`sheriff_election→DAY_SHERIFF_RUN`、`ended→GAME_OVER`；`round_number→dayNumber` |
| `player_speech` / `player_discussion` | push `speechLogs`（playerId/name/role/content/reasoning/day/isNight），`currentSpeakerId=data.player_id` |
| `player_died` / `player_eliminated` | 对应 seat `isAlive=false`；`victimId`/`executionId` |
| `werewolf_killed` / `seer_checked` / `witch_*` / `guard_protected`（god 可见） | god 注解：`narration` 追加，必要时 `seerVerifiedTarget` 等 |
| `sheriff_elected` | `sheriffId=data.player_id` |
| `vote_result` | `narration` 追加票型摘要 |
| `game_ended` | `phase=GAME_OVER`，`winner=WOLVES/VILLAGERS`（由 `data.winner_camp` 映射） |
| `end`(流结束帧) | 标记 `isLoading=false`（流已结束/已完结） |

座位 id 用后端 `player_{N}` 的 `N`（1-based，与现有 `Player.id:number` 对齐）。

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `src/llm_werewolf/interface/api/services/game_sessions.py` | `_run_game` 在 setup 后写 `god_roster.json`(seat→name/role/camp/alive) | Modify |
| `src/llm_werewolf/interface/api/routes/actions.py` | `view=god` 时 snapshot 首帧并入 roster | Modify |
| `tests/interface/test_api_stream.py` | god snapshot 含 roster 的断言 | Modify |
| `frontend/src/api/sse.ts` | `streamUrl(runId, view, seat?)` + `API_BASE`（VITE_API_BASE） | Create |
| `frontend/src/lib/gameReducer.ts` | 纯函数：SSE 事件 → GameState | Create |
| `frontend/src/lib/gameReducer.test.ts` | reducer 单测 | Create |
| `frontend/src/store.ts` | 加 `connectSpectate/disconnect`（EventSource + reduce） | Modify |
| `frontend/src/pages/GameApp.tsx` | URL 带 `run_id` → 观战模式 | Modify |
| `frontend/vite.config.ts` | proxy target 可配（默认 8000，可被 env 覆盖） | Modify |

---

## Task 1（后端）: 持久化 god roster + snapshot 首帧富化

**Files:**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py`
- Modify: `src/llm_werewolf/interface/api/routes/actions.py`
- Test: `tests/interface/test_api_stream.py`

- [ ] **Step 1: 写失败测试（god 流首帧 snapshot 含 roster）**

在 `tests/interface/test_api_stream.py` 追加：
```python
def test_god_snapshot_includes_roster_when_present(tmp_path, monkeypatch):
    import json
    from fastapi.testclient import TestClient
    from llm_werewolf.interface.api.app import create_app

    monkeypatch.chdir(tmp_path)
    run_id = "demo-roster"
    run_dir = tmp_path / "artifacts" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    (run_dir / "run_meta.json").write_text(json.dumps({"run_id": run_id, "status": "completed"}), encoding="utf-8")
    (run_dir / "god_roster.json").write_text(
        json.dumps([{"seat": 1, "name": "Player1", "role": "Seer", "camp": "villager", "is_alive": True}]),
        encoding="utf-8",
    )
    client = TestClient(create_app())
    with client.stream("GET", f"/api/v1/games/{run_id}/stream?view=god") as resp:
        body = "".join(chunk for chunk in resp.iter_text())
    assert '"roster"' in body
    assert "Seer" in body

    # seat view must NOT leak the roster
    with client.stream("GET", f"/api/v1/games/{run_id}/stream?view=seat&seat=1") as resp:
        body2 = "".join(chunk for chunk in resp.iter_text())
    assert "Seer" not in body2
```

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest tests/interface/test_api_stream.py::test_god_snapshot_includes_roster_when_present -q --no-cov`
Expected: FAIL（roster 未并入 snapshot）。

- [ ] **Step 3: 在 `game_sessions._run_game` setup 后写 `god_roster.json`**

定位 `_run_game` 中 `engine.setup_game(players=players, roles=roles)` 之后、`wire_agentscope_after_setup(...)` 附近，插入：
```python
            _write_god_roster(session.run_dir, engine)
```
并在模块内（如 `_read_alert_count` 附近）新增：
```python
def _write_god_roster(run_dir: Path, engine: object) -> None:
    """Persist the god-view roster (seat -> role/camp/alive) for spectate.

    Best-effort: never let roster I/O break a game run.
    """
    try:
        players = list(getattr(getattr(engine, "game_state", None), "players", []) or [])
        roster = []
        for idx, p in enumerate(players, start=1):
            role = getattr(p, "role", None)
            cfg = role.get_config() if role is not None and hasattr(role, "get_config") else None
            roster.append({
                "seat": idx,
                "name": getattr(p, "name", f"Player{idx}"),
                "role": getattr(cfg, "name", None) or getattr(role, "name", None) or "Unknown",
                "camp": getattr(getattr(cfg, "camp", None), "value", None),
                "is_alive": bool(getattr(p, "is_alive", True)),
            })
        (run_dir / "god_roster.json").write_text(
            json.dumps(roster, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("Failed to write god_roster for %s: %s", run_dir.name, exc)
```
> 注：`engine.game_state.players` 的真实属性名（`players` / `is_alive` / `role.get_config().name` / `camp`）以 `game_runtime/state/game_state.py`、`state/player.py`、`roles/base.py` 为准；如属性名不同，按实际取值，保持产出的 dict 字段不变。

- [ ] **Step 4: SSE 端点在 `view=god` 时把 roster 并进 snapshot 首帧**

在 `routes/actions.py` 的流生成器里，定位发出 snapshot 首帧处：
```python
        snap = extract_game_snapshot(run_dir).model_dump()
        yield {"event": "snapshot", "data": json.dumps(snap, ensure_ascii=False)}
```
改为：
```python
        snap = extract_game_snapshot(run_dir).model_dump()
        if view == "god":
            roster_path = run_dir / "god_roster.json"
            if roster_path.is_file():
                try:
                    snap["roster"] = json.loads(roster_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    pass
        yield {"event": "snapshot", "data": json.dumps(snap, ensure_ascii=False)}
```
（若该逻辑在已抽出的 `_stream_events(...)` 模块级生成器内，则在那里改；保持 `view` 已是其参数。）

- [ ] **Step 5: 运行确认通过 + 回归 + ruff**

Run: `uv run pytest tests/interface/test_api_stream.py -q --no-cov`
Expected: PASS（含新用例）。
Run: `uv run pytest tests/interface -q --no-cov`
Expected: 无新失败。
Run: `uv run ruff check src/llm_werewolf/interface/api/services/game_sessions.py src/llm_werewolf/interface/api/routes/actions.py`
Expected: 无新增错误（既有 B008/ANN001 Depends 模式除外）。

- [ ] **Step 6: Commit**

```bash
git add src/llm_werewolf/interface/api/services/game_sessions.py src/llm_werewolf/interface/api/routes/actions.py tests/interface/test_api_stream.py
git commit -m "feat(api): persist god roster + include it in god SSE snapshot

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2（前端）: SSE URL/base 助手 + 可配 proxy

**Files:**
- Create: `frontend/src/api/sse.ts`
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: 创建 `frontend/src/api/sse.ts`**

```ts
const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/+$/, "");

export type StreamView = "god" | "seat";

/** Build the SSE stream URL for a run. Relative by default (Vite proxy / nginx). */
export function streamUrl(runId: string, view: StreamView = "god", seat?: number): string {
  const params = new URLSearchParams({ view });
  if (view === "seat" && seat != null) params.set("seat", String(seat));
  return `${API_BASE}/api/v1/games/${encodeURIComponent(runId)}/stream?${params.toString()}`;
}
```

- [ ] **Step 2: `vite.config.ts` 的 proxy target 改为可配（默认 8000）**

把 Task M0 加的 proxy 块改为读 env：
```ts
      proxy: {
        '/api': { target: process.env.VITE_API_PROXY ?? 'http://localhost:8000', changeOrigin: true },
        '/ready': { target: process.env.VITE_API_PROXY ?? 'http://localhost:8000', changeOrigin: true },
      },
```
> 这样浏览器 E2E 想指到 6_6 的 8010：`VITE_API_PROXY=http://localhost:8010 npm run dev`，不必动用户的 6_5(8000) 服务。

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npm run lint`
Expected: 退出码 0。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/sse.ts frontend/vite.config.ts
git commit -m "feat(frontend): SSE stream URL helper + configurable dev proxy target

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3（前端）: `gameReducer` 纯函数（事件 → GameState）

**Files:**
- Create: `frontend/src/lib/gameReducer.ts`
- Test: `frontend/src/lib/gameReducer.test.ts`

- [ ] **Step 1: 写失败测试 `frontend/src/lib/gameReducer.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import { initialSpectateState, reduceEvent } from "./gameReducer";

const snapshot = {
  event_type: "snapshot",
  phase: "night",
  round_number: 1,
  roster: [
    { seat: 1, name: "P1", role: "Seer", camp: "villager", is_alive: true },
    { seat: 2, name: "P2", role: "Werewolf", camp: "werewolf", is_alive: true },
  ],
};

describe("gameReducer", () => {
  it("builds players + phase from a god snapshot", () => {
    const s = reduceEvent(initialSpectateState(), snapshot as any);
    expect(s.players.map((p) => p.id)).toEqual([1, 2]);
    expect(s.players[0].role).toBe("Seer");
    expect(s.phase).toBe("NIGHT_WOLF");
    expect(s.dayNumber).toBe(1);
  });

  it("appends speech and sets current speaker", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "player_speech", round_number: 2, phase: "day_discussion",
      message: "我是预言家", data: { player_id: "player_1", reasoning: "因为..." },
    } as any);
    expect(s.phase).toBe("DAY_DEBATE");
    expect(s.currentSpeakerId).toBe(1);
    expect(s.speechLogs.at(-1)).toMatchObject({ playerId: 1, content: "我是预言家" });
  });

  it("marks a player dead on player_died", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "player_died", round_number: 2, phase: "night",
      message: "P2 倒下", data: { player_id: "player_2" },
    } as any);
    expect(s.players.find((p) => p.id === 2)!.isAlive).toBe(false);
  });

  it("ends the game on game_ended", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "game_ended", round_number: 3, phase: "ended",
      message: "狼人胜", data: { winner_camp: "werewolf" },
    } as any);
    expect(s.phase).toBe("GAME_OVER");
    expect(s.winner).toBe("WOLVES");
  });
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npx vitest run src/lib/gameReducer.test.ts`
Expected: FAIL（模块不存在）。

- [ ] **Step 3: 实现 `frontend/src/lib/gameReducer.ts`**

```ts
import type { GameState, Player } from "../types";

export interface SseEvent {
  event_type: string;
  round_number?: number;
  phase?: string;
  message?: string;
  data?: Record<string, any>;
  roster?: { seat: number; name: string; role: string; camp?: string | null; is_alive?: boolean }[];
  event_id?: number;
}

const PHASE_MAP: Record<string, GameState["phase"]> = {
  setup: "START_SCREEN",
  night: "NIGHT_WOLF",
  sheriff_election: "DAY_SHERIFF_RUN",
  day_discussion: "DAY_DEBATE",
  day_voting: "DAY_VOTE",
  ended: "GAME_OVER",
};

function seatOf(data: Record<string, any> | undefined): number | null {
  const pid = data?.player_id;
  if (typeof pid === "string") {
    const m = pid.match(/(\d+)$/);
    if (m) return Number(m[1]);
  }
  if (typeof data?.seat === "number") return data.seat;
  return null;
}

export function initialSpectateState(): GameState {
  return {
    players: [], dayNumber: 0, phase: "START_SCREEN", currentSpeakerId: null,
    countdown: 0, speechLogs: [], narration: "", winner: null,
    wolfKilledTarget: null, witchSaved: false, witchPoisonedTarget: null,
    seerVerifiedTarget: null, seerVerificationResult: null, victimId: null,
    discussionIndex: 0, executionId: null, gameMode: "llmOnly",
  };
}

export function reduceEvent(prev: GameState, ev: SseEvent): GameState {
  const s: GameState = { ...prev, players: prev.players.map((p) => ({ ...p })), speechLogs: [...prev.speechLogs] };

  // any event carries a phase/round -> keep phase + dayNumber fresh
  if (ev.phase && PHASE_MAP[ev.phase]) s.phase = PHASE_MAP[ev.phase];
  if (typeof ev.round_number === "number" && ev.round_number > 0) s.dayNumber = ev.round_number;

  switch (ev.event_type) {
    case "snapshot": {
      if (ev.roster?.length) {
        s.players = ev.roster.map<Player>((r) => ({
          id: r.seat, name: r.name, role: r.role, isUser: false,
          isAlive: r.is_alive !== false, avatarSeed: r.name, lastSpeech: "",
          statusNotes: "",
        }));
      }
      break;
    }
    case "player_speech":
    case "player_discussion": {
      const seat = seatOf(ev.data);
      if (seat != null) {
        s.currentSpeakerId = seat;
        const p = s.players.find((x) => x.id === seat);
        if (p) p.lastSpeech = ev.message ?? "";
        s.speechLogs.push({
          playerId: seat, playerName: p?.name ?? `P${seat}`, role: p?.role ?? "",
          content: ev.message ?? "", reasoning: ev.data?.reasoning,
          day: ev.round_number ?? s.dayNumber, isNight: ev.phase === "night",
        });
      }
      break;
    }
    case "player_died":
    case "player_eliminated": {
      const seat = seatOf(ev.data);
      if (seat != null) {
        const p = s.players.find((x) => x.id === seat);
        if (p) p.isAlive = false;
        if (ev.event_type === "player_eliminated") s.executionId = seat;
        else s.victimId = seat;
      }
      break;
    }
    case "sheriff_elected": {
      s.sheriffId = seatOf(ev.data);
      break;
    }
    case "game_ended": {
      s.phase = "GAME_OVER";
      const camp = ev.data?.winner_camp;
      s.winner = camp === "werewolf" ? "WOLVES" : camp === "villager" ? "VILLAGERS" : s.winner;
      break;
    }
    default: {
      if (ev.message) s.narration = ev.message;
    }
  }
  return s;
}
```

- [ ] **Step 4: 运行确认通过**

Run: `cd frontend && npx vitest run src/lib/gameReducer.test.ts`
Expected: PASS（4 passed）。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/gameReducer.ts frontend/src/lib/gameReducer.test.ts
git commit -m "feat(frontend): gameReducer — fold SSE events into GameState

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4（前端）: store `connectSpectate` + GameApp 观战模式

**Files:**
- Modify: `frontend/src/store.ts`
- Modify: `frontend/src/pages/GameApp.tsx`

- [ ] **Step 1: store 增加 spectate 订阅（EventSource + reduce）**

在 `GameStore` interface 增加：
```ts
  spectateSource: EventSource | null;
  connectSpectate: (runId: string) => void;
  disconnectSpectate: () => void;
```
在 `create<GameStore>` 实现里（与其它 action 同级）加：
```ts
  spectateSource: null,
  connectSpectate: (runId) => {
    get().disconnectSpectate();
    // lazy import to avoid circular deps at module load
    import("./lib/gameReducer").then(({ initialSpectateState, reduceEvent }) => {
      import("./api/sse").then(({ streamUrl }) => {
        set({ state: initialSpectateState(), isLoading: false });
        const es = new EventSource(streamUrl(runId, "god"));
        const onMsg = (e: MessageEvent) => {
          try {
            const ev = JSON.parse(e.data);
            const cur = get().state ?? initialSpectateState();
            set({ state: reduceEvent(cur, ev) });
          } catch (err) { console.error("bad sse event", err); }
        };
        es.addEventListener("snapshot", onMsg);
        es.onmessage = onMsg; // default (named events: event_type)
        es.addEventListener("end", () => { get().disconnectSpectate(); });
        es.onerror = () => { /* EventSource auto-reconnects; nothing to do */ };
        set({ spectateSource: es });
      });
    });
  },
  disconnectSpectate: () => {
    const es = get().spectateSource;
    if (es) es.close();
    set({ spectateSource: null });
  },
```
> 说明：后端 SSE 把每个事件的 `event:` 设为其 `event_type`（如 `player_speech`），所以默认 `onmessage` 不一定触发；为稳妥，对所有事件统一处理：除 `snapshot`/`end` 外，用一个通配监听。由于浏览器 `EventSource` 不支持通配 `event` 监听，**实现时**给后端 SSE 同时不设具名 `event`（即只发 `data:`，让 `onmessage` 收全部），或在前端显式 `addEventListener` 一组已知 `event_type`。**首选**：改 M1a 的 `_sse()` 不再设 `"event"` 字段（只 `id`+`data`），让前端 `onmessage` 收到所有事件（`snapshot`/`end` 仍具名）。这是本任务的一个明确实现决定，需同步微调 `routes/actions.py` 的 `_sse()` 并更新其测试断言（仍能在 body 里看到 `event_type` 字符串，因为它在 `data` JSON 里）。

- [ ] **Step 2: 调整 M1a `_sse()` 只发 `id`+`data`（去掉具名 event），保证前端 onmessage 收全**

`routes/actions.py` 的 `_sse(event)`：
```python
def _sse(event: dict) -> dict:
    return {"id": str(event.get("event_id", "")), "data": json.dumps(event, ensure_ascii=False)}
```
（`snapshot`/`end` 仍保留各自具名 `event`。）`tests/interface/test_api_stream.py` 既有断言查的是 body 里的 `event_type` 字符串（在 data JSON 内），仍成立；运行确认未回归。

Run: `uv run pytest tests/interface/test_api_stream.py -q --no-cov`
Expected: PASS。

- [ ] **Step 3: GameApp 进入观战模式（URL 带 run_id）**

`GameApp.tsx` 顶部 import：
```tsx
import { useSearchParams } from "react-router-dom";
```
把现有挂载副作用：
```tsx
  useEffect(() => {
    fetchState();
  }, [fetchState]);
```
改为：
```tsx
  const [searchParams] = useSearchParams();
  const runId = searchParams.get("run_id");
  const connectSpectate = useGameStore((s) => s.connectSpectate);
  const disconnectSpectate = useGameStore((s) => s.disconnectSpectate);
  useEffect(() => {
    if (runId) {
      connectSpectate(runId);
      return () => disconnectSpectate();
    }
    fetchState();
  }, [runId, connectSpectate, disconnectSpectate, fetchState]);
```

- [ ] **Step 4: 构建 + 类型检查 + 单测**

Run: `cd frontend && npm run lint && npm run test && npm run build`
Expected: tsc 0；vitest 全绿；build 成功。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store.ts frontend/src/pages/GameApp.tsx src/llm_werewolf/interface/api/routes/actions.py
git commit -m "feat(frontend): live god-view spectate via SSE (connectSpectate + GameApp)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 端到端联调验证（手动）

**Files:** 无（验证）

- [ ] **Step 1: 起 6_6 后端（8010，避开用户 6_5 的 8000）**

Run: `OBS_READY_REQUIRE_LLM=0 make api` 或 `uv run werewolf-api --port 8010`
（带真实对局需 `DEEPSEEK_API_KEY=...`；纯看回放可用已有 demo run）

- [ ] **Step 2: 生成/选一局**

Run: `PYTHONUTF8=1 make demo`（离线）或用 Key 起一局 LLM 对局，记下 `run_id`。

- [ ] **Step 3: 起前端 dev，指到 6_6**

Run: `cd frontend && VITE_API_PROXY=http://localhost:8010 npm run dev`
打开 `http://localhost:5173/game?run_id=<run_id>`。
Expected: 进入观战；座位带身份（god）；发言流实时滚动；阶段昼夜切换；死亡座位变灰；终局显示胜负。Network 里 `/api/v1/games/<run_id>/stream` 为 `text/event-stream`、持续接收。

- [ ] **Step 4: 收口**

Run: `cd frontend && npm run test && npm run lint` 全绿；`uv run pytest tests/interface -q --no-cov` 无新失败。

---

## Self-Review

**Spec coverage（对照设计 spec §7 C3/C4/C8、§4.2 直播段）：**
- 事件 reducer（事件→GameState）→ Task 3 ✅
- store SSE 驱动（去 POST-mock 的观战路径）+ GameApp 观战模式 → Task 4 ✅
- god 视角（roster + 全事件可见）→ Task 1 + Task 4 ✅
- 可配 base/proxy → Task 2 ✅
- 未覆盖（有意）：信念矩阵/票型实时面板接真数据（M2）、人类输入/座位视角（M3）、每事件精细动画。

**Placeholder scan:** 无 TODO/TBD；改码步骤均有完整代码或精确替换位置。Task 4 Step 1/2 含一个明确实现决定（SSE 去具名 event 让 onmessage 收全）并给出对应后端微调与测试影响。

**Type consistency:** `SseEvent`(event_type/round_number/phase/message/data/roster) ↔ 后端 `event_to_dict` + snapshot.roster ↔ `reduceEvent` 产出 `GameState`(types.ts) ↔ store `connectSpectate` 用 `initialSpectateState/reduceEvent` ↔ GameApp 读 `state`。座位 `player_{N}`→`N` 一致。

---

## Follow-up
- M2：`useGameInsight`/InsightDock/VoteIntentionPanel 接 SSE 的 `belief_snapshot`/`vote_intention_snapshot` 事件；结算页 MVP/教练轮询。
- M3：座位令牌 + 人类输入（`/games/{id}/input`）+ `WebHumanAgent` + 原始 key 注入 + 固定角色。
- 细化：更多 `event_type` 的可视化（女巫/守卫/警徽流/猎人枪/情侣）与音效。
