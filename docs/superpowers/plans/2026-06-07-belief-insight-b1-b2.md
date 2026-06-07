# 观战读心·信念矩阵增强（B1 + B2）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实时观战的信念矩阵：修发言行高亮、按人数自动缩放、概率改百分比，并新增跟随发言人的 B2「被怀疑雷达」。

**Architecture:** 纯前端、零后端改动。所有可测逻辑抽到 `lib/*.ts` 纯函数（node 环境 vitest 单测）；组件做薄壳，靠 Chrome DevTools 真机验证。新增 `speakerSeat` 经 `store → useGameInsight → InsightDock → 组件` 透传。

**Tech Stack:** React 19 + TypeScript + Zustand + Vite + Vitest（`environment: node`，无 jsdom/testing-library）。

**关联 spec：** `docs/superpowers/specs/2026-06-07-belief-insight-b1-b2-design.md`

**测试命令：** 工作目录 `frontend/`。单测 `npm test`（vitest run）；类型检查 `npm run lint`（`tsc --noEmit`）；构建 `npm run build`。

---

## 文件结构

| 文件 | 责任 | 类型 |
|------|------|------|
| `frontend/src/lib/beliefFormat.ts` | 纯函数：`matrixScale`、`formatWolfProb`、`heatColor` | 新建 |
| `frontend/src/lib/beliefFormat.test.ts` | 上述纯函数单测 | 新建 |
| `frontend/src/api/insightTypes.ts` | 给 `BeliefSnapshot` 补 `second_order?`、新增 `SecondOrderCell` | 改 |
| `frontend/src/lib/insightMap.ts` | 新增 `mapSpeakerSeat`、`selectExposureRow`、`ExposureCell` | 改 |
| `frontend/src/lib/insightMap.test.ts` | 补 `mapSpeakerSeat`、`selectExposureRow` 单测 | 改 |
| `frontend/src/store.ts` | 新增 `insightSpeakerSeat` 状态 + connectSpectate 接线 | 改 |
| `frontend/src/hooks/useGameInsight.ts` | 返回值加 `speakerSeat` | 改 |
| `frontend/src/components/BeliefMatrixPanel.tsx` | 用 `currentSpeakerSeat`/`matrixScale`/`formatWolfProb`/`heatColor` | 改 |
| `frontend/src/components/ExposureRadarStrip.tsx` | B2 单行雷达薄壳组件 | 新建 |
| `frontend/src/components/InsightDock.tsx` | 透传 `speakerSeat` + 挂 `ExposureRadarStrip` | 改 |

---

## Task 1: `lib/beliefFormat.ts` — 缩放/百分比/热力色纯函数

**Files:**
- Create: `frontend/src/lib/beliefFormat.ts`
- Test: `frontend/src/lib/beliefFormat.test.ts`

- [ ] **Step 1: 写失败测试**

`frontend/src/lib/beliefFormat.test.ts`：
```ts
import { describe, it, expect } from "vitest";
import { matrixScale, formatWolfProb, heatColor } from "./beliefFormat";

describe("matrixScale", () => {
  it("scales cell/font down by player count tiers", () => {
    expect(matrixScale(6)).toEqual({ cell: 34, font: 10 });
    expect(matrixScale(7)).toEqual({ cell: 28, font: 9 });
    expect(matrixScale(9)).toEqual({ cell: 28, font: 9 });
    expect(matrixScale(10)).toEqual({ cell: 22, font: 8 });
    expect(matrixScale(12)).toEqual({ cell: 22, font: 8 });
    expect(matrixScale(13)).toEqual({ cell: 17, font: 7 });
    expect(matrixScale(16)).toEqual({ cell: 17, font: 7 });
  });
});

describe("formatWolfProb", () => {
  it("renders rounded integer percent", () => {
    expect(formatWolfProb(0)).toBe("0%");
    expect(formatWolfProb(0.05)).toBe("5%");
    expect(formatWolfProb(0.333)).toBe("33%");
    expect(formatWolfProb(0.25)).toBe("25%");
    expect(formatWolfProb(1)).toBe("100%");
  });
});

describe("heatColor", () => {
  it("interpolates blue->amber->crimson", () => {
    expect(heatColor(0)).toBe("rgb(15,50,100)");
    expect(heatColor(0.5)).toBe("rgb(217,119,6)");
    expect(heatColor(1)).toBe("rgb(153,27,27)");
  });
});
```

- [ ] **Step 2: 运行确认失败**

Run: `npm test -- beliefFormat`
Expected: FAIL（模块/导出不存在）

- [ ] **Step 3: 实现**

`frontend/src/lib/beliefFormat.ts`：
```ts
export interface MatrixScale {
  cell: number;
  font: number;
}

/** n = 总座位数（players.length）。分档缩小;最小格宽 17px,超限由调用方允许横滚。 */
export function matrixScale(n: number): MatrixScale {
  if (n <= 6) return { cell: 34, font: 10 };
  if (n <= 9) return { cell: 28, font: 9 };
  if (n <= 12) return { cell: 22, font: 8 };
  return { cell: 17, font: 7 };
}

/** 0.25 -> "25%"; 0.05 -> "5%"; 1 -> "100%"; 0.333 -> "33%" */
export function formatWolfProb(p: number): string {
  return `${Math.round(p * 100)}%`;
}

/** 连续热力色。p<=0.5: 深蓝->琥珀;p>0.5: 琥珀->暗红。从 BeliefMatrixPanel 抽出共用。 */
export function heatColor(p: number): string {
  if (p <= 0.5) {
    const ratio = p * 2;
    const r = Math.round(15 + ratio * (217 - 15));
    const g = Math.round(50 + ratio * (119 - 50));
    const b = Math.round(100 + ratio * (6 - 100));
    return `rgb(${r},${g},${b})`;
  }
  const ratio = (p - 0.5) * 2;
  const r = Math.round(217 + ratio * (153 - 217));
  const g = Math.round(119 + ratio * (27 - 119));
  const b = Math.round(6 + ratio * (27 - 6));
  return `rgb(${r},${g},${b})`;
}
```

- [ ] **Step 4: 运行确认通过**

Run: `npm test -- beliefFormat`
Expected: PASS（3 个 describe 全绿）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/lib/beliefFormat.ts frontend/src/lib/beliefFormat.test.ts
git commit -m "feat(fe): beliefFormat pure helpers (matrixScale/formatWolfProb/heatColor)"
```

---

## Task 2: 类型补全 + `mapSpeakerSeat` + `selectExposureRow`

**Files:**
- Modify: `frontend/src/api/insightTypes.ts`（加 `SecondOrderCell` + `BeliefSnapshot.second_order?`）
- Modify: `frontend/src/lib/insightMap.ts`（加 `ExposureCell`、`mapSpeakerSeat`、`selectExposureRow`）
- Test: `frontend/src/lib/insightMap.test.ts`（补用例）

- [ ] **Step 1: 加类型字段**

`frontend/src/api/insightTypes.ts`，在 `BeliefCell` 下方新增，并给 `BeliefSnapshot` 增 `second_order?`：
```ts
export interface SecondOrderCell {
  observer_seat: number;
  suspects_me_as_wolf: number;
  reason: string | null;
  note: string | null;
}
```
在 `BeliefSnapshot` 接口内 `first_order: BeliefCell[];` 之后加一行：
```ts
  second_order?: SecondOrderCell[];
```

- [ ] **Step 2: 写失败测试**

在 `frontend/src/lib/insightMap.test.ts` 末尾追加（保留文件顶部已有 import，并把 `mapSpeakerSeat, selectExposureRow` 加进从 `"./insightMap"` 的具名导入）：
```ts
describe("mapSpeakerSeat", () => {
  const snaps = [
    { observer_id: "player_1", observer_seat: 1, first_order: [] },
    { observer_id: "player_3", observer_seat: 3, first_order: [] },
  ];
  it("returns the speaker's seat on after_speech", () => {
    expect(mapSpeakerSeat({ speaker_id: "player_3", snapshots: snaps })).toBe(3);
  });
  it("returns null when speaker_id is empty (initial anchor)", () => {
    expect(mapSpeakerSeat({ speaker_id: "", snapshots: snaps })).toBeNull();
  });
  it("returns null when speaker not among snapshots, or data missing", () => {
    expect(mapSpeakerSeat({ speaker_id: "player_9", snapshots: snaps })).toBeNull();
    expect(mapSpeakerSeat({})).toBeNull();
    expect(mapSpeakerSeat(undefined)).toBeNull();
  });
});

describe("selectExposureRow", () => {
  const beliefs = [
    {
      observer_seat: 3,
      second_order: [
        { observer_seat: 2, suspects_me_as_wolf: 0.3, reason: "b", note: null },
        { observer_seat: 5, suspects_me_as_wolf: 0.7, reason: "a", note: null },
      ],
    },
  ] as any;
  it("returns the speaker's B2 sorted by suspicion desc", () => {
    expect(selectExposureRow(beliefs, 3)).toEqual([
      { observer_seat: 5, suspicion: 0.7, reason: "a" },
      { observer_seat: 2, suspicion: 0.3, reason: "b" },
    ]);
  });
  it("returns [] for null speaker / missing observer / null beliefs", () => {
    expect(selectExposureRow(beliefs, null)).toEqual([]);
    expect(selectExposureRow(beliefs, 9)).toEqual([]);
    expect(selectExposureRow(null, 3)).toEqual([]);
  });
});
```

- [ ] **Step 3: 运行确认失败**

Run: `npm test -- insightMap`
Expected: FAIL（`mapSpeakerSeat`/`selectExposureRow` 未定义）

- [ ] **Step 4: 实现**

`frontend/src/lib/insightMap.ts`：顶部 import 改为 `import type { BeliefSnapshot, VoteIntentionSnapshot } from "../api/insightTypes";`（已有），文件末尾追加：
```ts
export interface ExposureCell {
  observer_seat: number;
  suspicion: number;
  reason: string | null;
}

/** after_speech -> 发言人的 observer_seat;initial/空 speaker_id/找不到 -> null。 */
export function mapSpeakerSeat(data: any): number | null {
  const sid = data?.speaker_id;
  if (!sid) return null;
  const snaps = Array.isArray(data?.snapshots) ? data.snapshots : [];
  const self = snaps.find((s: any) => s?.observer_id === sid);
  return typeof self?.observer_seat === "number" ? self.observer_seat : null;
}

/** 取发言人那条 snapshot 的 second_order,按 suspicion 降序;无发言人/无 B2 -> []。 */
export function selectExposureRow(
  beliefs: BeliefSnapshot[] | null,
  speakerSeat: number | null,
): ExposureCell[] {
  if (!beliefs || speakerSeat == null) return [];
  const me = beliefs.find((b) => b.observer_seat === speakerSeat);
  const rows = me?.second_order ?? [];
  return [...rows]
    .map((r) => ({ observer_seat: r.observer_seat, suspicion: r.suspects_me_as_wolf, reason: r.reason }))
    .sort((a, b) => b.suspicion - a.suspicion);
}
```

- [ ] **Step 5: 运行确认通过 + 类型检查**

Run: `npm test -- insightMap && npm run lint`
Expected: 单测 PASS；tsc 无错误

- [ ] **Step 6: 提交**

```bash
git add frontend/src/api/insightTypes.ts frontend/src/lib/insightMap.ts frontend/src/lib/insightMap.test.ts
git commit -m "feat(fe): mapSpeakerSeat + selectExposureRow + B2 types"
```

---

## Task 3: `store.ts` — 新增 `insightSpeakerSeat` 接线

**Files:**
- Modify: `frontend/src/store.ts`

> 接线胶水（EventSource，无 node 单测）。逻辑已在 Task 2 单测覆盖；本任务靠 `tsc`/build 把关。
> **动 `connectSpectate` 前**：`gitnexus_impact({target: "connectSpectate", direction: "upstream"})` 报告影响面（索引 stale，仅参考）。

- [ ] **Step 1: 加 import**

`store.ts` 顶部已 `import { getCustomApiKey } from "./lib/config";`。无需新增 import（`mapSpeakerSeat` 在 connectSpectate 内的动态 import 块里取）。

- [ ] **Step 2: 接口加字段**

在 `GameStore` 接口的 `// Live spectate (SSE god-view)` 区块，`insightVote` 行附近加：
```ts
  insightSpeakerSeat: number | null;
```

- [ ] **Step 3: 初值 + 连接重置**

在 `useGameStore` 的 store 对象里，`insightVote: null,` 附近加初值：
```ts
  insightSpeakerSeat: null,
```
`connectSpectate` 开头的 `set({ insightBeliefs: null, insightVote: null, spectateRoster: null });` 改为：
```ts
    set({ insightBeliefs: null, insightVote: null, spectateRoster: null, insightSpeakerSeat: null });
```

- [ ] **Step 4: 动态 import + onmessage 接线**

`connectSpectate` 里 `Promise.all([import("./lib/gameReducer"), import("./api/sse"), import("./lib/insightMap")]).then(` 的解构，把 `mapBeliefEvent, mapVoteEvent` 改为 `mapBeliefEvent, mapVoteEvent, mapSpeakerSeat`：
```ts
      ([{ initialSpectateState, reduceEvent }, { streamUrl }, { mapBeliefEvent, mapVoteEvent, mapSpeakerSeat }]) => {
```
该 `es.onmessage` 内现有：
```ts
            if (ev.event_type === "belief_snapshot") set({ insightBeliefs: mapBeliefEvent(ev.data) });
```
改为：
```ts
            if (ev.event_type === "belief_snapshot") set({ insightBeliefs: mapBeliefEvent(ev.data), insightSpeakerSeat: mapSpeakerSeat(ev.data) });
```

- [ ] **Step 5: 类型检查 + 既有测试不回归**

Run: `npm run lint && npm test`
Expected: tsc 无错误；既有测试全绿

- [ ] **Step 6: 提交**

```bash
git add frontend/src/store.ts
git commit -m "feat(fe): store captures insightSpeakerSeat from belief_snapshot"
```

---

## Task 4: `useGameInsight.ts` — 返回 `speakerSeat`

**Files:**
- Modify: `frontend/src/hooks/useGameInsight.ts`

> 一行透传胶水，无单测；由 InsightDock 真机覆盖。

- [ ] **Step 1: 改 interface + 读取 + 返回**

`GameInsight` 接口加：
```ts
  speakerSeat: number | null;
```
函数体内加读取（与其它 `useGameStore` 选择器并列）：
```ts
  const speakerSeat = useGameStore((s) => s.insightSpeakerSeat);
```
返回语句改为：
```ts
  return { beliefs, voteSnapshot, players: rosterToInsightPlayers(roster, alive), speakerSeat };
```

- [ ] **Step 2: 类型检查**

Run: `npm run lint`
Expected: tsc 无错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/hooks/useGameInsight.ts
git commit -m "feat(fe): useGameInsight exposes speakerSeat"
```

---

## Task 5: `BeliefMatrixPanel.tsx` — 真发言高亮 + 缩放 + 百分比

**Files:**
- Modify: `frontend/src/components/BeliefMatrixPanel.tsx`

> **动该组件前**：`gitnexus_impact({target: "BeliefMatrixPanel", direction: "upstream"})`（仅 `InsightDock` 消费，影响面小；索引 stale 仅参考）。无单测（薄壳），靠 `tsc`/build + Task 8 真机。

- [ ] **Step 1: import 纯函数**

顶部 import 区加：
```ts
import { matrixScale, formatWolfProb, heatColor } from "../lib/beliefFormat";
```

- [ ] **Step 2: props 加 `currentSpeakerSeat`**

`BeliefMatrixPanelProps` 接口加：
```ts
  currentSpeakerSeat?: number | null;
```
函数签名解构加 `currentSpeakerSeat = null`：
```ts
export default function BeliefMatrixPanel({ beliefs, players, roundLabel, scope, showIdentities = false, currentSpeakerSeat = null }: BeliefMatrixPanelProps) {
```

- [ ] **Step 3: 删除本地 `getHeatColor` 与 `isLatestSpeaker`**

删掉整段 `const getHeatColor = (p: number) => { ... };`（已抽到 beliefFormat 的 `heatColor`）。
删掉整段 `const isLatestSpeaker = (seat: number) => { ... return seat === 2; };`。

- [ ] **Step 4: 计算缩放**

在 `const observers = sortedPlayers.filter(p => p.alive);` 之后加：
```ts
  const { cell, font } = matrixScale(sortedPlayers.length);
  const rowH = font + 14;
```

- [ ] **Step 5: 替换所有 `isLatestSpeaker(x)` 与配色/格式/尺寸引用**

逐处替换（共 4 处 isLatestSpeaker）：
- 顶部目标头行：`isLatestSpeaker(p.seat)` → `(p.seat === currentSpeakerSeat)`
- 观察者行：`const isSpeaker = isLatestSpeaker(obs.seat);` → `const isSpeaker = obs.seat === currentSpeakerSeat;`
- 单元格 ring：`isSpeaker || isLatestSpeaker(target.seat)` → `isSpeaker || target.seat === currentSpeakerSeat`

配色：`bgCol = getHeatColor(p);` → `bgCol = heatColor(p);`

格内文本（删掉 `content = p.toFixed(2).replace('0.', '.'); if (p === 1 || p === 0) content = p.toFixed(0);` 两行，替换为）：
```ts
                    content = formatWolfProb(p);
```

网格列模板：`gridTemplateColumns: \`auto repeat(${sortedPlayers.length}, minmax(32px, 1fr))\`` → `gridTemplateColumns: \`auto repeat(${sortedPlayers.length}, ${cell}px)\``

格高与字号（把死格 `h-6` 与 `text-[9px]` 改成内联尺寸）：
- 死者格 `<div className="w-full h-6 ...` 与活格 `className={\`w-full h-6 ...\`}`：去掉 `h-6`，在该 div 的 `style` 里加 `height: rowH`（活格已有 `style={{ backgroundColor: bgCol, ... }}`，并入 `height: rowH`；死者格新增 `style={{ height: rowH }}`）。
- 格内文本 `<span className={\`text-[9px] ${cls}\`}>` → `<span className={cls} style={{ fontSize: font }}>`

- [ ] **Step 6: 类型检查 + 构建 + 既有测试**

Run: `npm run lint && npm test && npm run build`
Expected: tsc 无错误；既有测试全绿；build 成功

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/BeliefMatrixPanel.tsx
git commit -m "feat(fe): belief matrix tracks real speaker, auto-scales, shows percent"
```

---

## Task 6: `ExposureRadarStrip.tsx`（新，B2 薄壳）

**Files:**
- Create: `frontend/src/components/ExposureRadarStrip.tsx`

> 薄壳组件，无单测；逻辑在 `selectExposureRow`（Task 2 已测）。

- [ ] **Step 1: 实现组件**

`frontend/src/components/ExposureRadarStrip.tsx`：
```tsx
import { BeliefSnapshot } from "../api/insightTypes";
import { selectExposureRow } from "../lib/insightMap";
import { heatColor, formatWolfProb } from "../lib/beliefFormat";

interface Props {
  beliefs: BeliefSnapshot[];
  speakerSeat: number | null;
}

export default function ExposureRadarStrip({ beliefs, speakerSeat }: Props) {
  const cells = selectExposureRow(beliefs, speakerSeat);
  const title = speakerSeat == null ? "被怀疑雷达" : `被怀疑雷达 · P${speakerSeat}视角`;

  return (
    <div className="mt-2 border border-amber-900/30 bg-[#0a0808]/90 rounded-md overflow-hidden text-amber-100 text-[10px]">
      <div className="flex justify-between items-center px-3 py-1.5 border-b border-amber-900/40 bg-zinc-950/80">
        <span className="font-serif font-black tracking-widest text-[#d4af37]">{title}</span>
        <span className="text-amber-500/70 text-[9px]">谁在怀疑“我”</span>
      </div>
      <div className="p-2 flex flex-wrap gap-1">
        {speakerSeat == null ? (
          <span className="text-amber-700/70 px-1 py-1">等待发言…</span>
        ) : cells.length === 0 ? (
          <span className="text-amber-700/70 px-1 py-1">{`P${speakerSeat} 暂未记录被谁怀疑`}</span>
        ) : (
          cells.map((c) => (
            <div
              key={c.observer_seat}
              className="group relative flex items-center gap-1 px-1.5 py-0.5 rounded-sm border border-amber-900/30 cursor-crosshair"
              style={{ backgroundColor: heatColor(c.suspicion) }}
            >
              <span className="font-serif font-bold text-white drop-shadow-[0_1px_1.5px_rgba(0,0,0,0.9)]">P{c.observer_seat}</span>
              <span className="font-mono text-white drop-shadow-[0_1px_1.5px_rgba(0,0,0,0.9)]">{formatWolfProb(c.suspicion)}</span>
              {c.reason && (
                <div className="absolute opacity-0 group-hover:opacity-100 transition-opacity z-50 bg-[#0f0a05] border border-amber-900/60 text-amber-100 px-2 py-1.5 rounded-sm bottom-full mb-1 left-0 shadow-[0_5px_15px_rgba(0,0,0,0.8)] pointer-events-none w-max max-w-[200px] whitespace-normal break-words">
                  {c.reason}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 类型检查 + 构建**

Run: `npm run lint && npm run build`
Expected: tsc 无错误；build 成功

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/ExposureRadarStrip.tsx
git commit -m "feat(fe): ExposureRadarStrip (B2 follow-speaker radar)"
```

---

## Task 7: `InsightDock.tsx` — 透传 speakerSeat + 挂 B2 strip

**Files:**
- Modify: `frontend/src/components/InsightDock.tsx`

> **动该组件前**：`gitnexus_impact({target: "InsightDock", direction: "upstream"})`（仅 GameApp 消费）。

- [ ] **Step 1: import + 解构 speakerSeat**

顶部加：
```ts
import ExposureRadarStrip from "./ExposureRadarStrip";
```
`const { beliefs, voteSnapshot, players } = useGameInsight(runId);` 改为：
```ts
  const { beliefs, voteSnapshot, players, speakerSeat } = useGameInsight(runId);
```

- [ ] **Step 2: 桌面布局：传 prop + 挂 strip**

桌面那处 `<BeliefMatrixPanel ... showIdentities={canShowIdentities} />` 加 `currentSpeakerSeat={speakerSeat}`，并在其后、`<VoteIntentionPanel ...>` 之前插入：
```tsx
          <ExposureRadarStrip beliefs={beliefs} speakerSeat={speakerSeat} />
```

- [ ] **Step 3: 移动布局：同样处理**

移动抽屉里的第二个 `<BeliefMatrixPanel ... />` 同样加 `currentSpeakerSeat={speakerSeat}`，并在其后、移动版 `<VoteIntentionPanel ...>` 之前插入同一行 `<ExposureRadarStrip beliefs={beliefs} speakerSeat={speakerSeat} />`。

- [ ] **Step 4: 类型检查 + 构建 + 既有测试**

Run: `npm run lint && npm test && npm run build`
Expected: tsc 无错误；既有测试全绿；build 成功

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/InsightDock.tsx
git commit -m "feat(fe): InsightDock wires speaker highlight + B2 radar strip"
```

---

## Task 8: Chrome DevTools 真机验证

**Files:** 无（验证 only）

> 环境已在跑：后端 8010 + vite 5183。观战 URL：`http://127.0.0.1:5183/?run_id=<run_id>`。

- [ ] **Step 1: 起一局 6 人真实局**

```bash
curl -s -X POST http://localhost:8010/api/v1/games/start -H 'Content-Type: application/json' -d '{"config_id":"llm-6p-deepseek","run_label":"b1b2-verify6"}'
```
记下返回的 `run_id`。

- [ ] **Step 2: 打开观战页，等讨论阶段（belief_snapshot 出现）**

`mcp__chrome-devtools__navigate_page` 到 `http://127.0.0.1:5183/?run_id=<run_id>`；轮询 `artifacts/runs/<run_id>/events.jsonl` 直到 `belief_snapshot` ≥ 2。

- [ ] **Step 3: 断言（evaluate_script + screenshot）**

确认：
- 矩阵格内文本是 `NN%` 形式（不再是 `.NN`）。
- 发言行高亮**随当前发言人移动**（不再恒定 P2）：对比两个不同 after_speech 锚点，高亮行 seat 改变。
- B2「被怀疑雷达」strip 出现在矩阵下方：有 second_order 时按降序显示 `P{n} NN%`；无则显示空态文案。
- 0 个 console error。

- [ ] **Step 4: 起一局 12 人局验证自动缩放**

```bash
curl -s -X POST http://localhost:8010/api/v1/games/start -H 'Content-Type: application/json' -d '{"config_id":"llm-12p-deepseek","run_label":"b1b2-verify12"}'
```
打开观战页，确认矩阵自动缩小（格 ~22px）、12 列基本铺满面板、可读。

- [ ] **Step 5: 记录结果**

把验证结论（PASS/问题）追加到本计划末尾或回报给用户。

---

## Self-Review

- **Spec 覆盖**：§5.1→Task1；§5.2/5.4→Task2；§5.3→Task3；§5.5→Task4；§5.6→Task5；§5.7→Task2(纯函数)+Task6(壳)；§5.8→Task7；§7→Task1/2 单测 + Task8 真机；§6 防作弊（座位流无 belief → strip 不渲染）由现有 `if (!beliefs||!voteSnapshot) return null` 保证，无需新增。✅
- **占位符**：无 TBD/TODO；所有代码步给出完整代码。✅
- **类型一致**：`matrixScale`/`formatWolfProb`/`heatColor`（beliefFormat）；`mapSpeakerSeat`/`selectExposureRow`/`ExposureCell`/`SecondOrderCell`（insightMap+insightTypes）；`insightSpeakerSeat`（store）；`speakerSeat`（useGameInsight/InsightDock）；`currentSpeakerSeat`（BeliefMatrixPanel prop）——跨任务命名一致。✅
