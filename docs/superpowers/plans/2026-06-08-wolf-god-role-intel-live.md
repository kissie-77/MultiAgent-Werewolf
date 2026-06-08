# 狼·神职预测矩阵（实时 god 视角第二栏）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在观战读心（InsightDock）左侧滑出一个独立第二栏，god 视角实时展示每只存活狼对每个存活非狼目标的神职猜测矩阵（5 神职概率 + 威胁 + 处置），初始全 0、随后端 `wolf_camp_snapshot` 事件实时填充。

**Architecture:** 纯前端消费侧。新增 god-only SSE 事件 `wolf_camp_snapshot`（后端另立项 emit；本计划只做前端）。store 存 `insightWolfCampMinds: Record<狼座位, WolfCampMindV2>`，镜像现有 `belief_snapshot` 流（整批替换）。纯函数 `selectWolfMatrices(players, minds, round)` 从 god roster 派生「存活狼 × 存活非狼目标」全 0 骨架并覆盖真实数据。复用既有 `GodRoleIntelPanel` 逐狼渲染。第二栏作为主面板 `motion.div` 的内部绝对定位子元素（`right-full`），随主面板拖动/定位作为整体单元移动，仅 `canShowIdentities` 时出现。

**Tech Stack:** React 19 + TypeScript, Zustand (store.ts), framer-motion (motion/react), Tailwind 4, Vitest (`environment: node` — 纯函数单测；组件靠 Playwright/Chrome 真机验证), EventSource SSE。

---

## 前置与上下文（动工前必读）

- **分支**：当前在 `feature/god-role-intel-mock-demo`。开工前 **rebase 到最新 `main`**（main 已近修复 `frontend/src/utils/audio.ts` 的语法错误 `}() {`；以 main 的修复为准，**不要**自行改 audio.ts）。rebase 后跑一次 `cd frontend && npm run build` 确认 audio.ts 不再阻断构建。
- **复用既有产物**（上一轮 mock demo 留下的，本计划直接用）：
  - `frontend/src/lib/godRoleIntel.ts` —— 类型 `WolfCampMindV2` / `GodRoleBeliefV2` / `GodRoleRow`、`GOD_ROLES`、`GOD_ROLE_ZH`、`PRIORITY_LABEL`、`topRoleOf`、`selectGodRoleRows`。**保留**，本计划向其追加 `selectWolfMatrices`。
  - `frontend/src/lib/godRoleIntel.test.ts` —— 6 条单测。**保留**，向其追加 `selectWolfMatrices` 测试。
  - `frontend/src/components/GodRoleIntelPanel.tsx` —— 单狼矩阵薄壳（`{record, players?}`）。**保留**，直接复用。
- **本计划要删除**（兑现「丢掉 mock」）：`frontend/src/pages/GodRoleIntelDemoPage.tsx`（demo 页）与 `frontend/src/mocks/mockBeliefData.ts`（mock 夹具）。`AppRouter.tsx` 的 `/dev/god-role-intel` 路由已被移除，无需再动。生产代码与单测均不依赖 mock 文件（单测用内联夹具）。
- **跨端契约（后端必须满足，否则前端只显示全 0 骨架）**：god SSE 流新增事件 `wolf_camp_snapshot`，`data = { round: number, minds: WolfCampMindV2[] }`，每帧**完整**下发各狼当前 `god_role_intel`（非增量）；**必须 god-only**（座位流以 `visible_to=[]` 红线掉，否则泄漏狼队名单）。本计划不实现后端；后端未就绪时本功能稳定显示全 0（预期态）。
- **Problem 1 提示**：LLM 不稳定产 `god_role_intel` 时矩阵长期为 0，这是已知上游问题，与本前端计划解耦。

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `frontend/src/lib/godRoleIntel.ts` | 追加 `zeroBelief` + `selectWolfMatrices`（骨架+覆盖派生） | 改 |
| `frontend/src/lib/godRoleIntel.test.ts` | 追加 `selectWolfMatrices` 单测 | 改 |
| `frontend/src/lib/insightMap.ts` | 追加 `mapWolfCampEvent`（事件 data → `Record<seat, WolfCampMindV2>`） | 改 |
| `frontend/src/lib/insightMap.test.ts` | 新建：`mapWolfCampEvent` 单测 | 新建 |
| `frontend/src/store.ts` | 加 `insightWolfCampMinds` slice + `wolf_camp_snapshot` 分支 + connect 时清空 | 改 |
| `frontend/src/hooks/useGameInsight.ts` | 暴露 `wolfCampMinds` | 改 |
| `frontend/src/components/WolfGodRoleColumn.tsx` | 第二栏容器：拉手 tab、滑出、纵向堆叠、竖滚、固定宽 | 新建 |
| `frontend/src/components/InsightDock.tsx` | 桌面挂第二栏（单元联动 + 展开时隐藏 resize 细条）；移动端抽屉追加区块；gate `canShowIdentities` | 改 |
| `frontend/src/pages/GodRoleIntelDemoPage.tsx` | demo 页 | **删除** |
| `frontend/src/mocks/mockBeliefData.ts` | mock 夹具 | **删除** |

---

### Task 1: 纯函数 `selectWolfMatrices`（骨架 + 实时覆盖）

**Files:**
- Modify: `frontend/src/lib/godRoleIntel.ts`
- Test: `frontend/src/lib/godRoleIntel.test.ts`

- [ ] **Step 1: 追加失败测试**

在 `frontend/src/lib/godRoleIntel.test.ts` 末尾追加。先在文件顶部 import 里加入 `selectWolfMatrices` 与类型 `InsightPlayer`：

```ts
// 顶部 import 区追加：
import { selectWolfMatrices } from "./godRoleIntel";
import type { InsightPlayer } from "./insightMap";

// 文件末尾追加：
function ip(seat: number, camp: string, alive = true, role = "Villager"): InsightPlayer {
  return { seat, id: `player_${seat}`, name: `P${seat}`, role, camp, alive };
}

describe("selectWolfMatrices", () => {
  // P1女巫 P2预言家 P3狼 P4狼 P5村 P6村
  const players: InsightPlayer[] = [
    ip(1, "good", true, "Witch"),
    ip(2, "good", true, "Seer"),
    ip(3, "werewolf", true, "Werewolf"),
    ip(4, "werewolf", true, "Werewolf"),
    ip(5, "good", true, "Villager"),
    ip(6, "good", true, "Villager"),
  ];

  it("returns [] when no living wolves", () => {
    const noWolves = players.map((p) => (p.camp === "werewolf" ? { ...p, alive: false } : p));
    expect(selectWolfMatrices(noWolves, null, 1)).toEqual([]);
  });

  it("builds one matrix per living wolf, with an all-zero skeleton over living non-wolf targets", () => {
    const out = selectWolfMatrices(players, null, 2);
    expect(out.map((m) => m.owner_seat)).toEqual([3, 4]); // 狼按座位升序
    const m3 = out[0];
    // 目标 = 存活非狼 = 1,2,5,6（排除狼 3/4 与自身）
    expect(Object.keys(m3.god_role_intel).sort()).toEqual(["1", "2", "5", "6"]);
    const t2 = m3.god_role_intel["2"];
    expect(t2.threat_score).toBe(0);
    expect(t2.priority).toBe("low");
    expect(t2.role_distribution).toEqual({ Seer: 0, Witch: 0, Guard: 0, Hunter: 0, Villager: 0 });
    expect(t2.updated_round).toBe(2);
  });

  it("overlays real god_role_intel onto the skeleton, keeping un-predicted targets at 0", () => {
    const minds = {
      3: {
        schema: "wolf_camp_mind_v2" as const,
        owner_seat: 3,
        round: 2,
        contributor_seat: 3,
        god_role_intel: {
          "2": {
            target_seat: 2,
            role_distribution: { Seer: 0.9, Witch: 0.05, Guard: 0.02, Hunter: 0, Villager: 0.03 },
            threat_score: 0.92,
            priority: "kill_tonight" as const,
            evidence: ["2号跳预言家"],
            updated_round: 2,
            contributors: [3],
          },
        },
        exposure_radar: {},
      },
    };
    const out = selectWolfMatrices(players, minds, 2);
    const m3 = out.find((m) => m.owner_seat === 3)!;
    expect(m3.god_role_intel["2"].threat_score).toBeCloseTo(0.92); // 覆盖
    expect(m3.god_role_intel["2"].priority).toBe("kill_tonight");
    expect(m3.god_role_intel["5"].threat_score).toBe(0); // 未预测 → 0
    const m4 = out.find((m) => m.owner_seat === 4)!;
    expect(m4.god_role_intel["2"].threat_score).toBe(0); // P4 无数据 → 全 0
  });

  it("drops dead non-wolf targets from the skeleton", () => {
    const p = players.map((x) => (x.seat === 6 ? { ...x, alive: false } : x));
    const out = selectWolfMatrices(p, null, 1);
    expect(Object.keys(out[0].god_role_intel).sort()).toEqual(["1", "2", "5"]); // 无 6
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run src/lib/godRoleIntel.test.ts`
Expected: FAIL —— `selectWolfMatrices is not a function` / 类型导出缺失。

- [ ] **Step 3: 实现 `zeroBelief` + `selectWolfMatrices`**

在 `frontend/src/lib/godRoleIntel.ts` 末尾追加：

```ts
/** 单个目标的全 0 神职信念（初始骨架格）。 */
export function zeroBelief(targetSeat: number, round: number): GodRoleBeliefV2 {
  const role_distribution = {} as Record<GodRole, number>;
  for (const role of GOD_ROLES) role_distribution[role] = 0;
  return {
    target_seat: targetSeat,
    role_distribution,
    threat_score: 0,
    priority: "low",
    evidence: [],
    updated_round: round,
    contributors: [],
  };
}

/**
 * 从 roster 派生「每只存活狼 × 每个存活非狼目标」的神职矩阵骨架（全 0），
 * 并用 store 中各狼的真实 god_role_intel 覆盖已预测的目标行；未预测的目标保持 0。
 * 无存活狼 → []。
 */
export function selectWolfMatrices(
  players: { seat: number; camp: string; alive: boolean }[] | null | undefined,
  minds: Record<number, WolfCampMindV2> | null | undefined,
  round: number,
): WolfCampMindV2[] {
  if (!players || players.length === 0) return [];
  const wolves = players
    .filter((p) => p.camp === "werewolf" && p.alive)
    .sort((a, b) => a.seat - b.seat);
  if (wolves.length === 0) return [];
  const targets = players
    .filter((p) => p.camp !== "werewolf" && p.alive)
    .sort((a, b) => a.seat - b.seat);

  return wolves.map((wolf) => {
    const existing = minds?.[wolf.seat];
    const god_role_intel: Record<string, GodRoleBeliefV2> = {};
    for (const t of targets) {
      const key = String(t.seat);
      god_role_intel[key] = existing?.god_role_intel?.[key] ?? zeroBelief(t.seat, round);
    }
    return {
      schema: "wolf_camp_mind_v2",
      owner_seat: wolf.seat,
      round,
      contributor_seat: wolf.seat,
      god_role_intel,
      exposure_radar: existing?.exposure_radar ?? {},
    };
  });
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd frontend && npx vitest run src/lib/godRoleIntel.test.ts`
Expected: PASS（原 6 条 + 新 4 条 = 10 条全过）。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/lib/godRoleIntel.ts frontend/src/lib/godRoleIntel.test.ts
git commit -m "feat(fe): selectWolfMatrices — god-role matrix skeleton + live overlay"
```

---

### Task 2: 事件映射 `mapWolfCampEvent`

**Files:**
- Modify: `frontend/src/lib/insightMap.ts`
- Test: `frontend/src/lib/insightMap.test.ts`（新建）

- [ ] **Step 1: 写失败测试**

新建 `frontend/src/lib/insightMap.test.ts`：

```ts
import { describe, it, expect } from "vitest";
import { mapWolfCampEvent } from "./insightMap";

describe("mapWolfCampEvent", () => {
  it("keys per-wolf records by owner_seat", () => {
    const data = {
      round: 2,
      minds: [
        { schema: "wolf_camp_mind_v2", owner_seat: 3, round: 2, contributor_seat: 3, god_role_intel: {}, exposure_radar: {} },
        { schema: "wolf_camp_mind_v2", owner_seat: 4, round: 2, contributor_seat: 4, god_role_intel: {}, exposure_radar: {} },
      ],
    };
    const out = mapWolfCampEvent(data);
    expect(Object.keys(out).sort()).toEqual(["3", "4"]);
    expect(out[3].owner_seat).toBe(3);
  });

  it("returns {} for missing / malformed payloads", () => {
    expect(mapWolfCampEvent(null)).toEqual({});
    expect(mapWolfCampEvent({})).toEqual({});
    expect(mapWolfCampEvent({ minds: "nope" })).toEqual({});
    expect(mapWolfCampEvent({ minds: [{ god_role_intel: {} }] })).toEqual({}); // 无 owner_seat → 丢弃
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run src/lib/insightMap.test.ts`
Expected: FAIL —— `mapWolfCampEvent is not a function`。

- [ ] **Step 3: 实现 `mapWolfCampEvent`**

在 `frontend/src/lib/insightMap.ts` 顶部 import 区追加，并在文件末尾追加函数：

```ts
// 顶部 import 追加：
import type { WolfCampMindV2 } from "./godRoleIntel";

// 文件末尾追加：
/** wolf_camp_snapshot 事件 data.minds[] → 以 owner_seat 为键的字典（整批替换语义）。 */
export function mapWolfCampEvent(data: any): Record<number, WolfCampMindV2> {
  const minds = Array.isArray(data?.minds) ? data.minds : [];
  const out: Record<number, WolfCampMindV2> = {};
  for (const m of minds) {
    if (m && typeof m.owner_seat === "number") out[m.owner_seat] = m as WolfCampMindV2;
  }
  return out;
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd frontend && npx vitest run src/lib/insightMap.test.ts`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/lib/insightMap.ts frontend/src/lib/insightMap.test.ts
git commit -m "feat(fe): mapWolfCampEvent — wolf_camp_snapshot event -> per-wolf map"
```

---

### Task 3: store slice + SSE 事件分支 + 连接清空

**Files:**
- Modify: `frontend/src/store.ts`

（无单测：store 副作用靠 Task 7 真机验证。本任务只做接线，编译通过即可。）

- [ ] **Step 1: 在 import 区加入 `mapWolfCampEvent` 与类型**

把现有：

```ts
import { mapBeliefEvent, mapVoteEvent, mapSpeakerSeat } from "./lib/insightMap";
```

改为：

```ts
import { mapBeliefEvent, mapVoteEvent, mapSpeakerSeat, mapWolfCampEvent } from "./lib/insightMap";
import type { WolfCampMindV2 } from "./lib/godRoleIntel";
```

- [ ] **Step 2: 在 `GameStore` 接口加 slice 字段**

在接口中 `insightSpeakerSeat: number | null;` 一行下方追加：

```ts
  insightWolfCampMinds: Record<number, WolfCampMindV2> | null;
```

- [ ] **Step 3: 初始 state 加默认值**

在 store 初始对象里 `insightSpeakerSeat: null,` 一行下方追加：

```ts
  insightWolfCampMinds: null,
```

- [ ] **Step 4: `connectSpectate` 与 `connectSeat` 连接时清空**

在 `connectSpectate` 与 `connectSeat` 两处的初始 `set({ ... })` 块里（均含 `insightSpeakerSeat: null,`），各自在该行下方追加：

```ts
      insightWolfCampMinds: null,
```

- [ ] **Step 5: `connectSpectate` 的 `es.onmessage` 加事件分支**

把现有：

```ts
        if (ev.event_type === "belief_snapshot") {
          set({ insightBeliefs: mapBeliefEvent(ev.data), insightSpeakerSeat: mapSpeakerSeat(ev.data) });
        } else if (ev.event_type === "vote_intention_snapshot") {
          set({ insightVote: mapVoteEvent(ev.data) });
        }
```

改为：

```ts
        if (ev.event_type === "belief_snapshot") {
          set({ insightBeliefs: mapBeliefEvent(ev.data), insightSpeakerSeat: mapSpeakerSeat(ev.data) });
        } else if (ev.event_type === "vote_intention_snapshot") {
          set({ insightVote: mapVoteEvent(ev.data) });
        } else if (ev.event_type === "wolf_camp_snapshot") {
          set({ insightWolfCampMinds: mapWolfCampEvent(ev.data) });
        }
```

（注：`connectSeat` 的 onmessage 不解析 god-only 的 `wolf_camp_snapshot`——座位流本就不该收到它；无需在 seat 分支添加。）

- [ ] **Step 6: 类型检查通过**

Run: `cd frontend && npx tsc --noEmit`
Expected: 仅可能残留与本任务无关的既有错误；**不得**出现 store.ts / godRoleIntel.ts / insightMap.ts 相关错误。

- [ ] **Step 7: 提交**

```bash
git add frontend/src/store.ts
git commit -m "feat(fe): store insightWolfCampMinds slice + wolf_camp_snapshot SSE branch"
```

---

### Task 4: `useGameInsight` 暴露 `wolfCampMinds`

**Files:**
- Modify: `frontend/src/hooks/useGameInsight.ts`

- [ ] **Step 1: 扩展返回类型与实现**

把整个 `frontend/src/hooks/useGameInsight.ts` 改为：

```ts
import { useGameStore } from "../store";
import { rosterToInsightPlayers, type InsightPlayer } from "../lib/insightMap";
import type { BeliefSnapshot, VoteIntentionSnapshot } from "../api/insightTypes";
import type { WolfCampMindV2 } from "../lib/godRoleIntel";

export interface GameInsight {
  beliefs: BeliefSnapshot[] | null;
  voteSnapshot: VoteIntentionSnapshot | null;
  players: InsightPlayer[];
  speakerSeat: number | null;
  wolfCampMinds: Record<number, WolfCampMindV2> | null;
}

/**
 * Live god-view insight, fed by the spectate SSE stream (store.connectSpectate).
 * runId is accepted for API compatibility; data comes from the active stream.
 */
export function useGameInsight(_runId: string | null): GameInsight {
  const beliefs = useGameStore((s) => s.insightBeliefs);
  const voteSnapshot = useGameStore((s) => s.insightVote);
  const speakerSeat = useGameStore((s) => s.insightSpeakerSeat);
  const wolfCampMinds = useGameStore((s) => s.insightWolfCampMinds);
  const roster = useGameStore((s) => s.spectateRoster);
  const statePlayers = useGameStore((s) => s.state?.players);

  const alive: Record<number, boolean> = {};
  (statePlayers ?? []).forEach((p) => { alive[p.id] = p.isAlive; });

  return {
    beliefs,
    voteSnapshot,
    players: rosterToInsightPlayers(roster, alive),
    speakerSeat,
    wolfCampMinds,
  };
}
```

- [ ] **Step 2: 类型检查通过**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无 useGameInsight 相关错误。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/hooks/useGameInsight.ts
git commit -m "feat(fe): useGameInsight exposes wolfCampMinds"
```

---

### Task 5: 第二栏容器组件 `WolfGodRoleColumn`

**Files:**
- Create: `frontend/src/components/WolfGodRoleColumn.tsx`

（无单测：薄壳组件，靠 Task 7 真机验证。本任务编译通过即可。）

- [ ] **Step 1: 创建组件**

新建 `frontend/src/components/WolfGodRoleColumn.tsx`：

```tsx
import { AnimatePresence, motion } from "motion/react";
import type { InsightPlayer } from "../lib/insightMap";
import type { WolfCampMindV2 } from "../lib/godRoleIntel";
import GodRoleIntelPanel from "./GodRoleIntelPanel";

interface Props {
  matrices: WolfCampMindV2[];
  players: InsightPlayer[];
  round: number;
  isOpen: boolean;
  onToggle: () => void;
}

/**
 * god 视角第二栏：主面板左侧滑出，纵向堆叠每只狼的神职猜测矩阵。
 * 渲染在主面板 motion.div 内部（绝对定位 right-full），随主面板拖动作为整体单元移动。
 * 无存活狼（matrices 为空）→ 整体不渲染（连拉手都不出现）。
 */
export default function WolfGodRoleColumn({ matrices, players, round, isOpen, onToggle }: Props) {
  if (matrices.length === 0) return null;

  return (
    <div className="absolute right-full top-0 h-full flex items-stretch pointer-events-none">
      {/* 滑出的第二栏 */}
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 360, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="pointer-events-auto overflow-hidden mr-1 rounded-l-xl border border-r-0 border-rose-900/40 bg-[#0c0a09]/95 shadow-[0_4px_24px_rgba(0,0,0,0.8)]"
            style={{ maxHeight: "calc(100vh - 4rem)" }}
          >
            <div
              className="overflow-y-auto overflow-x-hidden p-3 custom-scrollbar flex flex-col gap-3"
              style={{ width: 360, maxHeight: "calc(100vh - 4rem)" }}
            >
              <div className="text-rose-400 font-serif font-black text-xs uppercase tracking-widest flex items-center gap-2">
                🔪 狼·神职预测 <span className="text-rose-500/60 text-[10px] font-sans">R{round}</span>
              </div>
              {matrices.map((m) => (
                <GodRoleIntelPanel key={m.owner_seat} record={m} players={players} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 拉手 tab：始终挂在第二栏外左缘（开/合都在） */}
      <button
        onClick={onToggle}
        title={isOpen ? "收起神职预测" : "展开神职预测"}
        className="pointer-events-auto self-center -ml-px w-5 py-3 rounded-l-md border border-r-0 border-rose-900/50 bg-[#0c0a09]/95 text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 transition-colors flex items-center justify-center cursor-pointer"
      >
        <span className="text-[10px] writing-vertical leading-none" style={{ writingMode: "vertical-rl" }}>
          🔪{isOpen ? "▶" : "◀"}
        </span>
      </button>
    </div>
  );
}
```

- [ ] **Step 2: 类型检查通过**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无 WolfGodRoleColumn 相关错误。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/WolfGodRoleColumn.tsx
git commit -m "feat(fe): WolfGodRoleColumn — left slide-out second column for god-role matrices"
```

---

### Task 6: 接入 InsightDock（桌面侧栏 + 移动抽屉区块）

**Files:**
- Modify: `frontend/src/components/InsightDock.tsx`

（无单测：靠 Task 7 真机验证。）

- [ ] **Step 1: import 与数据派生**

顶部追加 import：

```tsx
import WolfGodRoleColumn from "./WolfGodRoleColumn";
import { selectWolfMatrices } from "../lib/godRoleIntel";
```

把 `const { beliefs, voteSnapshot, players, speakerSeat } = useGameInsight(runId);` 改为：

```tsx
  const { beliefs, voteSnapshot, players, speakerSeat, wolfCampMinds } = useGameInsight(runId);
```

在 `const [showIdentities, setShowIdentities] = useState(true);` 一行下方追加展开态（默认收起、本会话记住）：

```tsx
  const [godRoleOpen, setGodRoleOpen] = useState(false);
```

- [ ] **Step 2: 在早返回之后、`return (` 之前派生矩阵与轮次**

在 `const canShowIdentities = isLLMOnly && showIdentities;` 一行下方追加：

```tsx
  const round = beliefs.length > 0 ? beliefs[0].round : 0;
  const wolfMatrices = selectWolfMatrices(players, wolfCampMinds, round);
```

- [ ] **Step 3: 桌面：挂第二栏 + 展开时隐藏 resize 细条**

在桌面 `motion.div`（`drag dragListener={false} ...`）内部，把现有 resize 细条的渲染条件从 `isExpanded` 改为同时要求未展开第二栏，避免中缝出现手柄：

把：

```tsx
        {isExpanded && (
          <div
            onPointerDown={onResizeDown}
```

改为：

```tsx
        {isExpanded && !(canShowIdentities && godRoleOpen) && (
          <div
            onPointerDown={onResizeDown}
```

然后在该 resize 细条 `</div>` 之后、`{/* Subtle gothic border styling inside */}` 之前，插入第二栏（仅 god + 显示身份 + 主面板展开时）：

```tsx
        {isExpanded && canShowIdentities && (
          <WolfGodRoleColumn
            matrices={wolfMatrices}
            players={players}
            round={round}
            isOpen={godRoleOpen}
            onToggle={() => setGodRoleOpen((v) => !v)}
          />
        )}
```

- [ ] **Step 4: 移动端抽屉追加区块**

在移动抽屉里 `{canShowIdentities && <WolfExposurePanel beliefs={beliefs} players={players} />}` 一行下方追加：

```tsx
              {canShowIdentities && wolfMatrices.length > 0 && (
                <div className="flex flex-col gap-3">
                  <div className="text-rose-400 font-serif font-black text-xs uppercase tracking-widest flex items-center gap-2">
                    🔪 狼·神职预测 <span className="text-rose-500/60 text-[10px] font-sans">R{round}</span>
                  </div>
                  {wolfMatrices.map((m) => (
                    <GodRoleIntelPanel key={m.owner_seat} record={m} players={players} />
                  ))}
                </div>
              )}
```

并在顶部 import 区追加：

```tsx
import GodRoleIntelPanel from "./GodRoleIntelPanel";
```

- [ ] **Step 5: 类型检查 + 构建**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: 通过（无新错误；audio.ts 已由 main 修复）。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/InsightDock.tsx
git commit -m "feat(fe): mount WolfGodRoleColumn in InsightDock (desktop column + mobile block), gated by canShowIdentities"
```

---

### Task 7: 真机验证（Playwright/Chrome，god LLM 局）

**Files:** 无（验证任务）。本仓库 vitest 为 `environment: node`，组件不做 jsdom 单测，按既有范式真机验证。

- [ ] **Step 1: 起后端 + 前端**

后端（含 DeepSeek key 的 gitignored `.env`）正常启动到 :8010；前端：

Run: `cd frontend && npm run dev -- --host 127.0.0.1 --port 5173`
Expected: `http://127.0.0.1:5173/` ready。

- [ ] **Step 2: 开一局 LLM god 局并进入观战**

启动一局 `llmOnly` 含多狼（如 6p 2 狼或 12p 4 狼），进入 god 观战页，等首个 `belief_snapshot` 到达（观战读心出现信念矩阵）。

- [ ] **Step 3: 验证骨架（全 0）路径**

- 确认主面板左缘出现 `🔪◀` 拉手；点开 → 左侧滑出第二栏。
- 断言：每只**存活狼**一个矩阵，行 = 全部**存活非狼**座位，所有 5 神职列与威胁均为 `0%`、处置 `💤 低危`。
- 关闭「显示身份」(EyeOff) → 第二栏与拉手**整体消失**；重开 → 恢复。
- 用 `mcp__playwright__browser_console_messages level=error` 断言 **0 报错**。
- 截图存档。

- [ ] **Step 4: 验证实时覆盖路径（合成事件注入）**

后端 `wolf_camp_snapshot` 可能未就绪/数据为空，用 `mcp__playwright__browser_evaluate` 注入一帧合成事件态，验证覆盖渲染（座位号按你实际局调整；下例假设 P3 是狼、P2 是预言家）：

```js
() => {
  const store = window.__zustand_game ?? null; // 若未暴露则用下方兜底
  const set = (s) => (window.useGameStore ? window.useGameStore.setState(s) : null);
  const mind = {
    3: { schema: "wolf_camp_mind_v2", owner_seat: 3, round: 1, contributor_seat: 3,
      god_role_intel: { "2": { target_seat: 2,
        role_distribution: { Seer: 0.9, Witch: 0.05, Guard: 0.02, Hunter: 0, Villager: 0.03 },
        threat_score: 0.92, priority: "kill_tonight", evidence: ["2号跳预言家"], updated_round: 1, contributors: [3] } },
      exposure_radar: {} } };
  // 首选：通过已暴露的 store；兜底见下一步
  if (window.useGameStore) { window.useGameStore.setState({ insightWolfCampMinds: mind }); return "ok via useGameStore"; }
  return "no store handle";
}
```

若 `window.useGameStore` 未暴露：在 `frontend/src/store.ts` 末尾**临时**加 `if (typeof window !== "undefined") (window as any).useGameStore = useGameStore;`（验证后回滚，不提交），重跑 dev 再注入。

- 断言：P3 狼矩阵中 **P2 行**变为 预言家 `90%`（高亮）、威胁 `92%`、处置 `🔪 今夜刀`，并因威胁最高**排到首行**；其余目标仍 `0%`；P4 狼矩阵保持全 0。
- 截图存档。

- [ ] **Step 5: 验证两栏单元联动 + 宽度不越界**

- 拖动主面板表头移动 → 第二栏紧贴左侧**一起移动**，无脱节。
- 窄视口（如 1280→1024）下，两栏总宽不超出屏幕左边界；单狼矩阵 5 列超宽时其内部出现横向滚动条。
- 多狼（12p 4 狼）时第二栏整体可竖向滚动看全。

- [ ] **Step 6: 回滚临时调试代码并最终核验**

- 若 Step 4 加过 `window.useGameStore` 暴露行，删除它。
- Run: `cd frontend && npm run test && npx tsc --noEmit && npm run build`
- Expected: 全部通过（含 Task 1/2 新单测）。

- [ ] **Step 7: 提交验证记录**

```bash
git add docs/superpowers/plans/2026-06-08-wolf-god-role-intel-live.md
git commit -m "docs(plan): record wolf god-role-intel live verification (Playwright)"
```

---

### Task 8: 清理（兑现「丢掉 mock」）

**Files:**
- Delete: `frontend/src/pages/GodRoleIntelDemoPage.tsx`
- Delete: `frontend/src/mocks/mockBeliefData.ts`

- [ ] **Step 1: 确认无生产引用**

Run: `cd frontend && grep -rn "mockBeliefData\|GodRoleIntelDemoPage" src/ || echo "no refs"`
Expected: `no refs`（`AppRouter.tsx` 的 `/dev/god-role-intel` 路由先前已被移除；若仍有残留引用，先删除引用）。

- [ ] **Step 2: 删除文件**

```bash
git rm frontend/src/pages/GodRoleIntelDemoPage.tsx
git rm frontend/src/mocks/mockBeliefData.ts
```

- [ ] **Step 3: 构建 + 测试确认无回归**

Run: `cd frontend && npx tsc --noEmit && npm run build && npm run test`
Expected: 全过。

- [ ] **Step 4: 提交**

```bash
git commit -m "chore(fe): drop god-role mock demo page + fixture (live feature supersedes it)"
```

---

## Self-Review

**1. Spec coverage（对照 12 项锁定决策）：**
- Q1 数据通道（god-only SSE `wolf_camp_snapshot` → `insightWolfCampMinds`）→ Task 2/3 ✓
- Q2 初始全 0 骨架 + 覆盖 → Task 1 `selectWolfMatrices`/`zeroBelief` ✓
- Q3 仅存活非狼目标 → Task 1（filter camp≠werewolf && alive；死目标剔除测试）✓
- Q4 左侧滑出独立第二栏 + 拉手 tab → Task 5 ✓
- Q5 多狼纵向堆叠 + 整栏竖滚 → Task 5（flex-col gap + overflow-y-auto）✓
- Q6 完整 5 列 + 威胁 + 处置（复用 GodRoleIntelPanel）→ Task 5/6 ✓
- Q7 仅 canShowIdentities → Task 6 gate ✓
- Q8 每只狼整份替换 → Task 2/3（mapWolfCampEvent 整批 + store set 替换）✓
- Q9 固定 360px + 内部横滚 + 不越界 → Task 5（width 360 + GodRoleIntelPanel overflow-x-auto）；越界 clamp 在 Task 7 Step 5 真机核验 ✓
- Q10 两栏单元联动 + 展开隐藏 resize 细条 → Task 5（渲染于主 motion.div 内 right-full）+ Task 6 Step 3 ✓
- Q11 默认收起 + 本会话记住 → Task 6（`useState(false)`，挂在 InsightDock 生命周期内）✓
- Q12 移动端抽屉区块 → Task 6 Step 4 ✓
- 小默认：死狼移除（Task 1 filter）/ 无存活狼整体不渲染（Task 5 `matrices.length===0 → null`）/ 夜晚沿用最后一帧（store 仅在新事件时替换，天然 sticky）/ 标题与 P{n}号狼（Task 5 + 复用 GodRoleIntelPanel header）✓

**2. Placeholder scan：** 无 TBD/TODO；每个改动步骤均含完整代码与确切命令、预期输出。✓

**3. Type consistency：** `WolfCampMindV2` / `GodRoleBeliefV2` / `GOD_ROLES` 全部来自既有 `lib/godRoleIntel.ts`；新增 `zeroBelief`、`selectWolfMatrices`、`mapWolfCampEvent` 命名在 Task 1/2 定义后于 Task 3/4/5/6 一致引用；store 字段 `insightWolfCampMinds` 在 Task 3 定义、Task 4 读取一致；`GodRoleIntelPanel` props `{record, players?}` 与既有实现一致。✓

**4. 跨端依赖（非本计划实现，需后端配合）：** `wolf_camp_snapshot` 事件（god-only、每帧完整、`data={round, minds: WolfCampMindV2[]}`）。后端未就绪时本功能稳定显示全 0 骨架，不报错、不白屏。
