# M2 — 信念矩阵 / 投票意向 实时同步 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 观战时 `InsightDock` 的**信念矩阵 + 投票意向**随后端 SSE 实时刷新（替换 `useGameInsight` 的 mock）。后端 `belief_snapshot` / `vote_intention_snapshot` 事件（god 视角可见、seat 视角不可见）→ 前端映射 → store → `useGameInsight` → 面板。**并修复 M1b 的 snapshot 接线 bug**（roster→座位初始化当前不触发）。

**Architecture:** `belief_snapshot` 事件的 `data.snapshots[]` 已是 `BeliefSnapshot` 形状；`vote_intention_snapshot` 的 `data` 已是 `VoteIntentionSnapshot` 形状（仅缺 `influence_score`，前端补默认）。新增纯函数 `lib/insightMap.ts` 做轻量映射；`store.connectSpectate` 捕获这两类事件写入 `insightBeliefs/insightVote`，并把 god snapshot 的 `roster` 存入 `spectateRoster`；`useGameInsight` 改为读 store（live），`GameApp` 把观战 `runId` 传给 `InsightDock`。

**Tech Stack:** React + Zustand + Vitest（mapper 纯函数 TDD）。后端无需改动（事件已 god 可见；M1a 已验证 seat 不泄露）。

**关键事实（已核验）：** `track_vote_intentions` 默认 True → 真实 LLM 局会发这两类事件；demo 局不发言/不出意向，故只有 LLM 观战能看到 insight（符合用例）。`REPLAY_ONLY_TYPES` 使其 `visible_to=[]` → god 流可见、seat 流不可见。

**边界（M2 不做）：** 结算页 MVP/教练轮询（→ M2b）；replay 页 insight 面板接真载荷（→ M2b）；人类输入（M3）。

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `frontend/src/lib/insightMap.ts` | 纯函数：事件 data → BeliefSnapshot[]/VoteIntentionSnapshot/InsightPlayer[] | Create |
| `frontend/src/lib/insightMap.test.ts` | mapper 单测 | Create |
| `frontend/src/store.ts` | 加 `insightBeliefs/insightVote/spectateRoster`；修 snapshot 接线；捕获 insight 事件 | Modify |
| `frontend/src/hooks/useGameInsight.ts` | 改读 store（live），去 mock 加载 | Modify |
| `frontend/src/pages/GameApp.tsx` | `<InsightDock runId={runId} />`（传观战 runId） | Modify |

---

## Task 1: `lib/insightMap.ts` 纯映射（vitest TDD）

**Files:**
- Create: `frontend/src/lib/insightMap.ts`
- Test: `frontend/src/lib/insightMap.test.ts`

- [ ] **Step 1: 写失败测试 `frontend/src/lib/insightMap.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import { mapBeliefEvent, mapVoteEvent, rosterToInsightPlayers } from "./insightMap";

describe("insightMap", () => {
  it("mapBeliefEvent returns the snapshots array (already BeliefSnapshot-shaped)", () => {
    const data = {
      round: 2, phase: "day_discussion", anchor: "after_speech:player_2",
      snapshots: [
        { round: 2, phase: "day_discussion", anchor: "x", observer_id: "player_1", observer_seat: 1,
          vote_intention: { seat: 4, reason: "r" }, first_order: [{ target_seat: 2, wolf_probability: 0.5, reason: null, note: null }] },
      ],
    };
    const out = mapBeliefEvent(data);
    expect(out).toHaveLength(1);
    expect(out[0].observer_seat).toBe(1);
    expect(out[0].first_order[0].wolf_probability).toBe(0.5);
  });

  it("mapBeliefEvent tolerates missing snapshots", () => {
    expect(mapBeliefEvent({})).toEqual([]);
    expect(mapBeliefEvent(undefined)).toEqual([]);
  });

  it("mapVoteEvent defaults influence_score and swing_count", () => {
    const v = mapVoteEvent({
      round_number: 2, phase: "day_discussion", speaker_id: "player_2", speaker_name: "P2",
      public_speech: "推4", before: {}, after: {}, swings: [{ player_id: "player_1" }],
    });
    expect(v.swing_count).toBe(1);
    expect(typeof v.influence_score).toBe("number");
    expect(v.speaker_name).toBe("P2");
  });

  it("rosterToInsightPlayers merges live alive status over roster", () => {
    const roster = [
      { seat: 1, name: "P1", role: "Seer", camp: "villager", is_alive: true },
      { seat: 2, name: "P2", role: "Werewolf", camp: "werewolf", is_alive: true },
    ];
    const players = rosterToInsightPlayers(roster, { 2: false });
    expect(players[0]).toMatchObject({ seat: 1, id: "player_1", camp: "villager", alive: true });
    expect(players[1].alive).toBe(false); // live override
  });

  it("rosterToInsightPlayers tolerates null roster", () => {
    expect(rosterToInsightPlayers(null, {})).toEqual([]);
  });
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npx vitest run src/lib/insightMap.test.ts`
Expected: FAIL（模块不存在）。

- [ ] **Step 3: 实现 `frontend/src/lib/insightMap.ts`**

```ts
import type { BeliefSnapshot, VoteIntentionSnapshot } from "../api/insightTypes";

export interface RosterEntry {
  seat: number;
  name: string;
  role: string;
  camp?: string | null;
  is_alive?: boolean;
}

export interface InsightPlayer {
  seat: number;
  id: string;
  name: string;
  role: string;
  camp: string;
  alive: boolean;
}

/** belief_snapshot event.data.snapshots[] are already BeliefSnapshot-shaped records. */
export function mapBeliefEvent(data: any): BeliefSnapshot[] {
  const snaps = data?.snapshots;
  return Array.isArray(snaps) ? (snaps as BeliefSnapshot[]) : [];
}

/** vote_intention_snapshot event.data ~= VoteIntentionSnapshot; influence_score is not
 *  emitted by the backend record, so derive a default from swing_count. */
export function mapVoteEvent(data: any): VoteIntentionSnapshot {
  const swings = Array.isArray(data?.swings) ? data.swings : [];
  const swingCount = typeof data?.swing_count === "number" ? data.swing_count : swings.length;
  return {
    round_number: data?.round_number ?? 0,
    phase: data?.phase ?? "",
    speaker_id: data?.speaker_id ?? "",
    speaker_name: data?.speaker_name ?? "",
    public_speech: data?.public_speech ?? "",
    before: data?.before ?? {},
    after: data?.after ?? {},
    swings,
    swing_count: swingCount,
    influence_score: typeof data?.influence_score === "number" ? data.influence_score : swingCount * 10,
  };
}

/** Build insight players from the god roster (for camp/role) + live alive status (by seat). */
export function rosterToInsightPlayers(
  roster: RosterEntry[] | null,
  alive: Record<number, boolean>,
): InsightPlayer[] {
  if (!roster) return [];
  return roster.map((r) => ({
    seat: r.seat,
    id: `player_${r.seat}`,
    name: r.name,
    role: r.role,
    camp: r.camp ?? "unknown",
    alive: alive[r.seat] ?? r.is_alive !== false,
  }));
}
```

- [ ] **Step 4: 运行确认通过**

Run: `cd frontend && npx vitest run src/lib/insightMap.test.ts`
Expected: PASS（5 passed）。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/insightMap.ts frontend/src/lib/insightMap.test.ts
git commit -m "feat(frontend): insightMap — map SSE belief/vote events to insight types

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: store 捕获 insight + 修复 snapshot 接线

**Files:**
- Modify: `frontend/src/store.ts`

- [ ] **Step 1: `GameStore` interface 增加 insight 字段**

在 `interface GameStore` 里（与 `spectateSource` 同区）加：
```ts
  insightBeliefs: import("./api/insightTypes").BeliefSnapshot[] | null;
  insightVote: import("./api/insightTypes").VoteIntentionSnapshot | null;
  spectateRoster: import("./lib/insightMap").RosterEntry[] | null;
```

- [ ] **Step 2: 初始值**

在 `create<GameStore>` 的初始对象里（`spectateSource: null` 附近）加：
```ts
  insightBeliefs: null,
  insightVote: null,
  spectateRoster: null,
```

- [ ] **Step 3: 重写 `connectSpectate`（修 snapshot 接线 + 捕获 insight）**

把现有 `connectSpectate` 实现替换为：
```ts
  connectSpectate: (runId) => {
    get().disconnectSpectate();
    set({ insightBeliefs: null, insightVote: null, spectateRoster: null });
    Promise.all([import("./lib/gameReducer"), import("./api/sse"), import("./lib/insightMap")]).then(
      ([{ initialSpectateState, reduceEvent }, { streamUrl }, { mapBeliefEvent, mapVoteEvent }]) => {
        set({ state: initialSpectateState(), isLoading: false });
        const es = new EventSource(streamUrl(runId, "god"));

        // Named "snapshot" frame: inject event_type so the reducer's snapshot
        // case fires (roster -> seats), and stash the god roster for insight.
        es.addEventListener("snapshot", (e: MessageEvent) => {
          try {
            const snap = JSON.parse(e.data);
            const cur = get().state ?? initialSpectateState();
            set({
              state: reduceEvent(cur, { ...snap, event_type: "snapshot" }),
              spectateRoster: Array.isArray(snap.roster) ? snap.roster : null,
            });
          } catch (err) { console.error("bad snapshot frame", err); }
        });

        // Unnamed game/insight events (event_type lives inside data JSON).
        es.onmessage = (e: MessageEvent) => {
          try {
            const ev = JSON.parse(e.data);
            const cur = get().state ?? initialSpectateState();
            set({ state: reduceEvent(cur, ev) });
            if (ev.event_type === "belief_snapshot") set({ insightBeliefs: mapBeliefEvent(ev.data) });
            else if (ev.event_type === "vote_intention_snapshot") set({ insightVote: mapVoteEvent(ev.data) });
          } catch (err) { console.error("bad sse event", err); }
        };

        es.addEventListener("end", () => { get().disconnectSpectate(); });
        es.onerror = () => { /* EventSource auto-reconnects */ };
        set({ spectateSource: es });
      },
    );
  },
```
（`disconnectSpectate` 保持不变。）

- [ ] **Step 4: 类型检查 + 既有单测**

Run: `cd frontend && npm run lint && npm run test`
Expected: tsc 0；vitest 全绿（含 gameReducer/insightMap）。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store.ts
git commit -m "fix(frontend): init seats from snapshot frame + capture live belief/vote insight

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `useGameInsight` 改读 store（live）

**Files:**
- Modify: `frontend/src/hooks/useGameInsight.ts`

- [ ] **Step 1: 替换实现为读 store**

把 `useGameInsight.ts` 整体替换为：
```ts
import { useGameStore } from "../store";
import { rosterToInsightPlayers, type InsightPlayer } from "../lib/insightMap";
import type { BeliefSnapshot, VoteIntentionSnapshot } from "../api/insightTypes";

export interface GameInsight {
  beliefs: BeliefSnapshot[] | null;
  voteSnapshot: VoteIntentionSnapshot | null;
  players: InsightPlayer[];
}

/**
 * Live god-view insight, fed by the spectate SSE stream (store.connectSpectate).
 * runId is accepted for API compatibility; data comes from the active stream.
 */
export function useGameInsight(_runId: string | null): GameInsight {
  const beliefs = useGameStore((s) => s.insightBeliefs);
  const voteSnapshot = useGameStore((s) => s.insightVote);
  const roster = useGameStore((s) => s.spectateRoster);
  const statePlayers = useGameStore((s) => s.state?.players);

  const alive: Record<number, boolean> = {};
  (statePlayers ?? []).forEach((p) => { alive[p.id] = p.isAlive; });

  return { beliefs, voteSnapshot, players: rosterToInsightPlayers(roster, alive) };
}
```
> 若有其它文件 import `MOCK_PLAYERS`/`MOCK_BELIEFS` 自本文件，先 grep 确认；如仍被引用，保留一个最小 `export const MOCK_PLAYERS = []`（或改其引用方）。本任务范围内只要保证 `npm run lint`/`build` 不因缺失导出而失败。

- [ ] **Step 2: 确认无残留引用导致编译失败**

Run: `cd frontend && grep -rn "MOCK_PLAYERS\|MOCK_BELIEFS\|MOCK_VOTE_SNAPSHOT" src/ || echo "no mock refs"`
按结果：若有引用，最小保留导出或改引用；目标是下一步全绿。

- [ ] **Step 3: 类型检查 + 构建**

Run: `cd frontend && npm run lint && npm run build`
Expected: tsc 0；build 成功。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useGameInsight.ts
git commit -m "feat(frontend): useGameInsight reads live SSE insight from store (drop mock)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: `GameApp` 把观战 runId 传给 `InsightDock` + 收口

**Files:**
- Modify: `frontend/src/pages/GameApp.tsx`

- [ ] **Step 1: 传 runId**

`GameApp.tsx` 中（M1b 已有 `const runId = searchParams.get("run_id");`）把：
```tsx
          <InsightDock runId={null} />
```
改为：
```tsx
          <InsightDock runId={runId} />
```

- [ ] **Step 2: 全量收口（前端单测 + 类型 + 构建）**

Run: `cd frontend && npm run test && npm run lint && npm run build`
Expected: vitest 全绿（gameReducer + insightMap）；tsc 0；build 成功（确认 InsightDock/useGameInsight 接 store 后仍编译）。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/GameApp.tsx
git commit -m "feat(frontend): wire InsightDock to live spectate runId

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 联调验证（手动，留人工）

- [ ] 起 6_6 后端(8010, 带 DEEPSEEK_API_KEY)；`POST /games/start {config_id:"llm-6p-deepseek"}` 起一局**真 LLM 局**（demo 局不出意向，看不到 insight）。
- [ ] `cd frontend && VITE_API_PROXY=http://localhost:8010 npm run dev`，开 `http://localhost:5173/game?run_id=<id>`。
- [ ] 预期：座位带身份；白天发言后 `InsightDock` 的信念矩阵（观察者×目标 wolf_probability 热力）与投票意向（before→after 摆动）随发言实时刷新。可对一条 `belief_snapshot` 事件 curl god 流核对数据。

---

## Self-Review

**Spec coverage（对照用户明确要求“信念矩阵，投票意向必须要和后端一起同步刷新”）：**
- belief/vote 事件 → 前端映射 → store → 面板实时刷新 → Task 1/2/3/4 ✅
- 修复 M1b snapshot 接线（座位初始化）→ Task 2 ✅
- 未覆盖（有意）：结算 MVP/教练轮询、replay 面板接真载荷 → M2b。

**Placeholder scan:** 无 TODO/TBD；改码步骤均有完整代码或精确替换。

**Type consistency:** 后端 `belief_snapshot.data.snapshots[]`(BeliefSnapshotRecord.to_dict 含 vote_intention:{seat,reason}+first_order) ↔ 前端 `BeliefSnapshot`/`BeliefCell` ↔ `mapBeliefEvent` ↔ store `insightBeliefs` ↔ `useGameInsight.beliefs`；`vote_intention_snapshot.data`(round_number/before/after/swings/swing_count) ↔ `VoteIntentionSnapshot`(+influence_score 默认) ↔ `mapVoteEvent` ↔ `insightVote`。座位 `player_{N}`↔N 一致。

---

## Follow-up（M2b / M3）
- M2b：结算页（`GameOverPanel` 即时胜负已有 → 轮询 `/games/{id}/status` 的 `has_post_game`/`post_game_status`，就绪后拉 `/pages/replay` 显示 MVP/教练）；replay 页 `BeliefHeatmap/VoteSwing/MvpTab` 接真实 replay 载荷（去 mock）。
- M3：座位令牌 + `/games/{id}/input` + `WebHumanAgent` + 原始 key 注入 + 固定角色。
