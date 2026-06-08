# 狼队·暴露雷达（④）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** god 观战视角下，从现有信念矩阵数据派生并实时渲染「狼队·暴露雷达」——每只存活狼的暴露度、最疑者、建议姿态。

**Architecture:** 纯前端、零后端改动。可测逻辑抽到 `lib/wolfExposure.ts` 纯函数（node 环境 vitest 单测）；`WolfExposurePanel.tsx` 做薄壳；挂进 `InsightDock`，受 `canShowIdentities` 门控，置于投票意向之后。数据全部已在 `useGameInsight`（`beliefs` + `players`），无需改 store/hook。

**Tech Stack:** React 19 + TypeScript + Zustand + Vite + Vitest（`environment: node`，无 jsdom/testing-library）。

**关联 spec：** `docs/superpowers/specs/2026-06-08-wolf-exposure-radar-design.md`

**测试命令：** 工作目录 `frontend/`。单测 `npm test`（vitest run）；类型检查 `npm run lint`（`tsc --noEmit`）；构建 `npm run build`。

---

## 文件结构

| 文件 | 责任 | 类型 |
|------|------|------|
| `frontend/src/lib/wolfExposure.ts` | 纯函数：`stanceFromExposure`、`selectWolfExposure` + 类型 | 新建 |
| `frontend/src/lib/wolfExposure.test.ts` | 上述纯函数单测 | 新建 |
| `frontend/src/components/WolfExposurePanel.tsx` | god 视角狼队暴露雷达薄壳组件 | 新建 |
| `frontend/src/components/InsightDock.tsx` | 桌面+移动两处，`canShowIdentities` 时挂在 VoteIntentionPanel 之后 | 改 |

依赖关系：Task 1（纯函数 + 单测）→ Task 2（组件薄壳，用 Task 1 的函数）→ Task 3（接进 InsightDock）→ Task 4（真机验证）。

类型契约（贯穿全计划，命名须一致）：
- `WolfStance = "sacrifice" | "bus" | "counter" | "hide" | "push"`
- `WolfSuspector = { seat: number; prob: number }`
- `WolfExposureRow = { wolfSeat: number; role: string; exposure: number; topSuspectors: WolfSuspector[]; stance: WolfStance }`
- `stanceFromExposure(p: number): WolfStance`
- `selectWolfExposure(beliefs: BeliefSnapshot[] | null, players: InsightPlayer[]): WolfExposureRow[]`

参考现有类型（勿改）：
- `BeliefSnapshot`（`frontend/src/api/insightTypes.ts`）：`{ observer_seat: number; first_order: BeliefCell[]; ... }`，`BeliefCell = { target_seat: number; wolf_probability: number; reason: string | null; note: string | null }`。
- `InsightPlayer`（`frontend/src/lib/insightMap.ts`）：`{ seat: number; id: string; name: string; role: string; camp: string; alive: boolean }`。
- `useGameInsight()` 返回 `{ beliefs, voteSnapshot, players, speakerSeat }`。
- `lib/beliefFormat.ts` 导出 `heatColor(p)`、`formatWolfProb(p)`。
- `lib/roleCatalog.ts` 导出 `roleDisplayName`（见 Task 2 用法）。

---

## Task 1: `lib/wolfExposure.ts` — 派生纯函数

**Files:**
- Create: `frontend/src/lib/wolfExposure.ts`
- Test: `frontend/src/lib/wolfExposure.test.ts`

- [ ] **Step 1: 写失败测试**

`frontend/src/lib/wolfExposure.test.ts`：
```ts
import { describe, it, expect } from "vitest";
import { stanceFromExposure, selectWolfExposure } from "./wolfExposure";
import type { BeliefSnapshot } from "../api/insightTypes";
import type { InsightPlayer } from "./insightMap";

function player(seat: number, camp: string, alive = true, role = "Werewolf"): InsightPlayer {
  return { seat, id: `player_${seat}`, name: `P${seat}`, role, camp, alive };
}

// 一条观察者快照：observer 对每个 target 的狼概率由 probs[target_seat] 给出
function snap(observerSeat: number, probs: Record<number, number>): BeliefSnapshot {
  return {
    round: 1,
    phase: "day_discussion",
    anchor: "after_speech",
    observer_id: `player_${observerSeat}`,
    observer_seat: observerSeat,
    vote_intention: { seat: 0, reason: "" },
    first_order: Object.entries(probs).map(([t, p]) => ({
      target_seat: Number(t),
      wolf_probability: p,
      reason: null,
      note: null,
    })),
  };
}

describe("stanceFromExposure", () => {
  it("maps exposure to stance buckets at backend thresholds", () => {
    expect(stanceFromExposure(0)).toBe("push");
    expect(stanceFromExposure(0.24)).toBe("push");
    expect(stanceFromExposure(0.25)).toBe("hide");
    expect(stanceFromExposure(0.45)).toBe("counter");
    expect(stanceFromExposure(0.6)).toBe("bus");
    expect(stanceFromExposure(0.85)).toBe("sacrifice");
    expect(stanceFromExposure(1)).toBe("sacrifice");
  });
});

describe("selectWolfExposure", () => {
  // 4 玩家：P1 狼、P2 狼(队友)、P3 村、P4 村
  const players = [
    player(1, "werewolf"),
    player(2, "werewolf"),
    player(3, "villager"),
    player(4, "villager"),
  ];

  it("exposure = max of non-wolf observers' wolf_probability toward the wolf", () => {
    // 对 P1 的狼概率：P2(队友,排除)=1.0, P3=0.3, P4=0.7 → max(非狼)=0.7
    const beliefs = [
      snap(2, { 1: 1.0 }),
      snap(3, { 1: 0.3 }),
      snap(4, { 1: 0.7 }),
    ];
    const rows = selectWolfExposure(beliefs, players);
    const p1 = rows.find((r) => r.wolfSeat === 1)!;
    expect(p1.exposure).toBeCloseTo(0.7);
    expect(p1.stance).toBe("bus"); // 0.7 → ≥0.6
  });

  it("excludes fellow wolves and the wolf itself from the column", () => {
    // 仅队友 P2 给 P1 标 1.0，无村民数据 → 非狼列为空 → exposure 0
    const beliefs = [snap(2, { 1: 1.0 }), snap(1, { 1: 0 })];
    const rows = selectWolfExposure(beliefs, players);
    const p1 = rows.find((r) => r.wolfSeat === 1)!;
    expect(p1.exposure).toBe(0);
    expect(p1.topSuspectors).toEqual([]);
    expect(p1.stance).toBe("push");
  });

  it("topSuspectors: co-leaders within 0.15 of the top, capped at 2", () => {
    // P1: P3=0.62, P4=0.50 (相差0.12≤0.15→并列), 另设 P2 队友排除
    const beliefs = [snap(3, { 1: 0.62 }), snap(4, { 1: 0.5 })];
    const rows = selectWolfExposure(beliefs, players);
    const p1 = rows.find((r) => r.wolfSeat === 1)!;
    expect(p1.exposure).toBeCloseTo(0.62);
    expect(p1.topSuspectors.map((s) => s.seat)).toEqual([3, 4]);
  });

  it("topSuspectors: drops the second when gap > 0.15", () => {
    const beliefs = [snap(3, { 1: 0.62 }), snap(4, { 1: 0.4 })];
    const rows = selectWolfExposure(beliefs, players);
    const p1 = rows.find((r) => r.wolfSeat === 1)!;
    expect(p1.topSuspectors.map((s) => s.seat)).toEqual([3]);
  });

  it("rows sorted by exposure desc, alive wolves only", () => {
    // P1 狼 exposure 0.3，P2 狼 exposure 0.8 → 期望顺序 [2,1]
    const beliefs = [
      snap(3, { 1: 0.3, 2: 0.8 }),
      snap(4, { 1: 0.2, 2: 0.1 }),
    ];
    const rows = selectWolfExposure(beliefs, players);
    expect(rows.map((r) => r.wolfSeat)).toEqual([2, 1]);
  });

  it("returns [] when no living wolves or beliefs missing", () => {
    const deadWolves = [player(1, "werewolf", false), player(3, "villager")];
    expect(selectWolfExposure([snap(3, { 1: 0.9 })], deadWolves)).toEqual([]);
    expect(selectWolfExposure(null, players)).toEqual([]);
    expect(selectWolfExposure([], players)).toEqual([]);
  });
});
```

- [ ] **Step 2: 运行确认失败**

工作目录 `frontend/`。Run: `npm test -- wolfExposure`
Expected: FAIL（模块/导出不存在）

- [ ] **Step 3: 实现**

`frontend/src/lib/wolfExposure.ts`：
```ts
import type { BeliefSnapshot } from "../api/insightTypes";
import type { InsightPlayer } from "./insightMap";

export type WolfStance = "sacrifice" | "bus" | "counter" | "hide" | "push";

export interface WolfSuspector {
  seat: number;
  prob: number;
}

export interface WolfExposureRow {
  wolfSeat: number;
  role: string;
  exposure: number;
  topSuspectors: WolfSuspector[];
  stance: WolfStance;
}

const SUSPECTOR_CO_LEADER_DELTA = 0.15;

/** 阈值镜像后端 strategy/wolf/camp_mind.py `_stance_from_exposure`。 */
export function stanceFromExposure(p: number): WolfStance {
  if (p >= 0.85) return "sacrifice";
  if (p >= 0.6) return "bus";
  if (p >= 0.45) return "counter";
  if (p >= 0.25) return "hide";
  return "push";
}

/**
 * 从当前帧信念矩阵派生每只存活狼的暴露雷达。
 * 暴露列 = 非狼存活观察者对该狼的 wolf_probability（排除狼队友与自身）。
 */
export function selectWolfExposure(
  beliefs: BeliefSnapshot[] | null,
  players: InsightPlayer[],
): WolfExposureRow[] {
  if (!beliefs || beliefs.length === 0 || !players || players.length === 0) return [];

  const wolves = players.filter((p) => p.camp === "werewolf" && p.alive);
  if (wolves.length === 0) return [];

  const playerBySeat = new Map<number, InsightPlayer>();
  for (const p of players) playerBySeat.set(p.seat, p);

  const rows: WolfExposureRow[] = wolves.map((wolf) => {
    const column: WolfSuspector[] = [];
    for (const snap of beliefs) {
      const obs = snap.observer_seat;
      if (obs === wolf.seat) continue; // 自身
      if (playerBySeat.get(obs)?.camp === "werewolf") continue; // 狼队友
      const cell = snap.first_order.find((f) => f.target_seat === wolf.seat);
      if (cell) column.push({ seat: obs, prob: cell.wolf_probability });
    }

    const exposure = column.length
      ? column.reduce((m, c) => (c.prob > m ? c.prob : m), 0)
      : 0;

    const sorted = [...column].sort((a, b) => b.prob - a.prob || a.seat - b.seat);
    const topSuspectors: WolfSuspector[] = [];
    if (sorted[0] && sorted[0].prob > 0) {
      topSuspectors.push(sorted[0]);
      const second = sorted[1];
      if (second && second.prob > 0 && second.prob >= sorted[0].prob - SUSPECTOR_CO_LEADER_DELTA) {
        topSuspectors.push(second);
      }
    }

    return {
      wolfSeat: wolf.seat,
      role: wolf.role,
      exposure,
      topSuspectors,
      stance: stanceFromExposure(exposure),
    };
  });

  return rows.sort((a, b) => b.exposure - a.exposure || a.wolfSeat - b.wolfSeat);
}
```

- [ ] **Step 4: 运行确认通过 + 类型检查**

Run: `npm test -- wolfExposure && npm run lint`
Expected: 单测全绿；tsc 无错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/lib/wolfExposure.ts frontend/src/lib/wolfExposure.test.ts
git commit -m "feat(fe): wolfExposure pure helpers (selectWolfExposure/stanceFromExposure)"
```

---

## Task 2: `components/WolfExposurePanel.tsx` — god 视角薄壳组件

**Files:**
- Create: `frontend/src/components/WolfExposurePanel.tsx`

> 薄壳组件，无单测（逻辑在 Task 1 已测）；靠 `tsc`/build + Task 4 真机验证。

- [ ] **Step 1: 确认角色本地化 API**

打开 `frontend/src/lib/roleCatalog.ts`，确认导出 `roleDisplayName`。其签名形如
`roleDisplayName(roles: PlayableRoleOption[], key: string): string` 或 `roleDisplayName(key: string): string`。
- 若是 `(roles, key)` 形式：本组件改用 `ROLE_CATALOG`/`FALLBACK_PLAYABLE_ROLES` 之一作为 roles 入参（见文件内导出）。
- 为避免耦合不确定的签名，本组件内置一个**仅狼系**的轻量 zh 映射作为主路径（roster 角色名带空格，先去空格再查），未命中回退「狼」：

```ts
const WOLF_ROLE_ZH: Record<string, string> = {
  Werewolf: "狼人",
  AlphaWolf: "狼王",
  WhiteWolf: "白狼",
  WolfBeauty: "狼美人",
  GuardianWolf: "守卫狼",
  HiddenWolf: "隐狼",
  BloodMoonApostle: "血月使徒",
  NightmareWolf: "梦魇狼",
};
function wolfRoleZh(role: string): string {
  return WOLF_ROLE_ZH[role.replace(/\s+/g, "")] ?? "狼";
}
```

- [ ] **Step 2: 实现组件**

`frontend/src/components/WolfExposurePanel.tsx`：
```tsx
import type { BeliefSnapshot } from "../api/insightTypes";
import type { InsightPlayer } from "../lib/insightMap";
import { selectWolfExposure, type WolfStance } from "../lib/wolfExposure";
import { heatColor, formatWolfProb } from "../lib/beliefFormat";

interface Props {
  beliefs: BeliefSnapshot[];
  players: InsightPlayer[];
}

const STANCE_LABEL: Record<WolfStance, string> = {
  sacrifice: "🩸 弃车",
  bus: "🚌 卖队友",
  counter: "⚔️ 对抗悍跳",
  hide: "🙈 隐藏",
  push: "😎 带节奏",
};

const WOLF_ROLE_ZH: Record<string, string> = {
  Werewolf: "狼人",
  AlphaWolf: "狼王",
  WhiteWolf: "白狼",
  WolfBeauty: "狼美人",
  GuardianWolf: "守卫狼",
  HiddenWolf: "隐狼",
  BloodMoonApostle: "血月使徒",
  NightmareWolf: "梦魇狼",
};
function wolfRoleZh(role: string): string {
  return WOLF_ROLE_ZH[role.replace(/\s+/g, "")] ?? "狼";
}

export default function WolfExposurePanel({ beliefs, players }: Props) {
  const rows = selectWolfExposure(beliefs, players);
  if (rows.length === 0) return null;

  return (
    <div className="mt-2 border border-rose-900/40 bg-[#0a0808]/90 rounded-md overflow-hidden text-rose-100 text-[10px]">
      <div className="flex justify-between items-center px-3 py-1.5 border-b border-rose-900/50 bg-zinc-950/80">
        <span className="font-serif font-black tracking-widest text-rose-400">🐺 狼队·暴露雷达</span>
        <span className="text-rose-500/70 text-[9px]">谁快暴露了</span>
      </div>
      <div className="p-2 flex flex-col gap-1.5">
        {rows.map((r) => (
          <div key={r.wolfSeat} className="flex items-center gap-2">
            <span className="font-serif font-bold text-rose-200 w-16 shrink-0">
              P{r.wolfSeat} {wolfRoleZh(r.role)}
            </span>
            <div className="flex-1 h-2.5 rounded-sm bg-black/50 overflow-hidden border border-rose-900/30">
              <div
                className="h-full rounded-sm transition-[width] duration-500"
                style={{ width: `${Math.round(r.exposure * 100)}%`, backgroundColor: heatColor(r.exposure) }}
              />
            </div>
            <span className="font-mono text-rose-100 w-9 text-right shrink-0">{formatWolfProb(r.exposure)}</span>
            <span className="text-rose-300/80 w-20 shrink-0 truncate">
              最疑 {r.topSuspectors.length ? r.topSuspectors.map((s) => `P${s.seat}`).join(",") : "—"}
            </span>
            <span className="shrink-0 font-sans text-rose-200">{STANCE_LABEL[r.stance]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 类型检查 + 构建**

Run: `npm run lint && npm run build`
Expected: tsc 无错误；build 成功

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/WolfExposurePanel.tsx
git commit -m "feat(fe): WolfExposurePanel (god-view wolf-team exposure radar)"
```

---

## Task 3: `InsightDock.tsx` — 接线（god + 身份开关门控，置于投票意向之后）

**Files:**
- Modify: `frontend/src/components/InsightDock.tsx`

> 接线胶水，无单测；靠 `tsc`/build + Task 4 真机。当前 `InsightDock` 已解构 `players`；`canShowIdentities` 已在文件内计算（`const canShowIdentities = isLLMOnly && showIdentities;`）。桌面与移动各有一处 `<VoteIntentionPanel ...>`。

- [ ] **Step 1: import 组件**

顶部 import 区，`import VoteIntentionPanel from "./VoteIntentionPanel";` 之后加：
```ts
import WolfExposurePanel from "./WolfExposurePanel";
```

- [ ] **Step 2: 桌面布局：投票意向之后挂面板**

桌面那处（缩进 10 空格的 `<VoteIntentionPanel`）是：
```tsx
          <VoteIntentionPanel
            snapshot={voteSnapshot}
            players={players}
            showIdentities={canShowIdentities}
          />
```
在其 `/>` 之后、闭合该滚动容器 `</div>` 之前插入：
```tsx

          {canShowIdentities && <WolfExposurePanel beliefs={beliefs} players={players} />}
```

- [ ] **Step 3: 移动布局：同样处理**

移动抽屉里（缩进 14 空格的 `<VoteIntentionPanel`）是：
```tsx
              <VoteIntentionPanel
                snapshot={voteSnapshot}
                players={players}
                showIdentities={canShowIdentities}
              />
```
在其 `/>` 之后、闭合该容器 `</div>` 之前插入：
```tsx

              {canShowIdentities && <WolfExposurePanel beliefs={beliefs} players={players} />}
```

- [ ] **Step 4: 类型检查 + 构建 + 既有测试不回归**

Run: `npm run lint && npm test && npm run build`
Expected: tsc 无错误；既有测试无新增失败（既有的 `utils/roles.test.ts` 角色素材缺失为预存在失败，与本特性无关）；build 成功

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/InsightDock.tsx
git commit -m "feat(fe): InsightDock mounts WolfExposurePanel (god, identity-gated)"
```

---

## Task 4: Chrome DevTools / Playwright 真机验证

**Files:** 无（验证 only）

> 需后端(8010)+vite 起着。后端需 LLM key（DeepSeek，写入仓库根 `.env` 的 `DEEPSEEK_API_KEY`，`.env` 已被 gitignore；key 见用户提供的 `apikey.txt` 中 `deepseek:` 行）。vite 须绑 IPv4：`npm run dev -- --host 127.0.0.1`（否则 Chrome 走 IPv4 连不上 IPv6-only 的 vite）。

- [ ] **Step 1: 起后端 + 前端**

仓库根：
```bash
# .env 含 DEEPSEEK_API_KEY=... 与 OBS_READY_REQUIRE_LLM=0
uv run werewolf-api --port 8010        # 后台
cd frontend && npm run dev -- --host 127.0.0.1   # 后台，IPv4
```
确认 `curl -s http://127.0.0.1:8010/health` → `{"status":"ok"}`；`curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5173/` → `200`。

- [ ] **Step 2: 起一局 12 人局（4 狼，便于看多行）**

```bash
curl -s -X POST http://127.0.0.1:8010/api/v1/games/start -H 'Content-Type: application/json' \
  -d '{"config_id":"llm-12p-deepseek","run_label":"wolfexp-verify12","track_vote_intentions":true}'
```
记下 `run_id`。轮询 `artifacts/runs/<run_id>/events.jsonl` 直到出现 ≥1 个 `belief_snapshot` 且 ≥1 个 `vote_intention_snapshot`（进入 day_discussion 后）。

- [ ] **Step 3: 打开 god 观战页并断言**

用 chrome-devtools MCP `new_page` 到 `http://127.0.0.1:5173/game?run_id=<run_id>&source=runs`，`wait_for` 文本 `["信念矩阵"]`。
- 默认「显示身份」开 → InsightDock 顶部身份开关按钮存在（`isLLMOnly`）。
- `evaluate_script` 断言：存在标题含「狼队·暴露雷达」的面板；面板行数 = 当前存活狼数；每行有 `NN%`、`最疑 P..`（或「—」）、姿态徽标（🩸/🚌/⚔️/🙈/😎 之一）；行按 exposure 文本降序。
- `list_console_messages` 过滤 error：应为 0（THREE.js 的 deprecation 警告为既有，无视）。
- `take_screenshot` 存 `.tmp/wolfexp-verify-12p.png`。

- [ ] **Step 4: 切换「显示身份」开关，验证门控**

`click` InsightDock 头部的身份开关（标题 `隐藏身份 (Hide Identities)` / `显示身份`）。`evaluate_script` 断言：关闭后「狼队·暴露雷达」面板从 DOM 消失；信念矩阵的角色 emoji 也同步隐藏。再次点击恢复。

- [ ] **Step 5: 记录结果 + 收尾**

把验证结论（PASS/问题 + 截图路径）追加到本计划末尾或回报用户。取消对局（`POST /api/v1/games/<run_id>/cancel`）、停掉后端/vite、删除临时 `.env`（key 仍在 `apikey.txt`）、还原对局运行期产生的无关产物（skill `.md` / `uv.lock` / `package-lock.json`）。

---

## Self-Review

- **Spec 覆盖**：§3 派生→Task1（含排除队友/自身、max、共领头、降序、空态全部单测）；§4 组件→Task2（条/最疑/姿态/角色本地化）；§5 可见性+位置+空态→Task3（`canShowIdentities` 门控 + VoteIntention 之后）+Task2（空→null）；§6 刷新→随 `beliefs` 自动重算（Task1 输入即当前帧）；§8 测试→Task1 单测 + Task4 真机。✅
- **占位符**：无 TBD/TODO；每个代码步给出完整代码。✅
- **类型一致**：`WolfStance`/`WolfSuspector`/`WolfExposureRow`/`stanceFromExposure`/`selectWolfExposure`（lib）；组件 props `{beliefs, players}`；`InsightDock` 透传 `beliefs`/`players`（均为其已有变量）；`STANCE_LABEL` 键与 `WolfStance` 全集一致。✅
- **门控一致**：Task3 用 `canShowIdentities`（文件内已存在）包裹两处挂载，与 spec §5 一致；座位视角 InsightDock 整体不渲染（`GameApp.tsx:183`），无需额外处理。✅

---

## 验证结果（2026-06-08）

单测：`wolfExposure.test.ts` 7/7 绿（stance 5 档边界、max、排除队友/自身、共领头±0.15、降序、空态）；`tsc`/`build` 通过；全套件无新增回归（唯一失败 `utils/roles.test.ts` 为预存在角色素材缺失）。

真机（Playwright，DeepSeek `llm-12p-deepseek` god 局 `wolfexp-verify12`，4 狼）：
- 面板「🐺 狼队·暴露雷达」渲染，4 行 = 4 只存活狼，角色中文正确：P2 狼王 / P5 白狼 / P8 狼人 / P10 狼人（验证 role-zh 映射 + 去空格归一对 "Alpha Wolf"/"White Wolf" 生效）。
- 每行有暴露条（宽=%）、`NN%`、`最疑 Px,Py`、姿态徽标；行按暴露降序。
- 早期帧全员 17%（1/6 基线先验）→ 全部 `😎 带节奏`（push），符合 <0.25 阈值。
- **身份门控**：关闭「显示身份」→ 面板从 DOM 消失（`wolfPanelAfterOff=false`）；重新开启 → 面板恢复。
- 全程 0 console error（仅 THREE.js deprecation 警告，既有无关）。截图 `.tmp/wolfexp-verify-12p.png`。

附：本特性纯前端、零后端改动；与并行 `feature/phase-transition-polish` 完全隔离（本分支仅含 ④ 相关 5 个提交，基于 main）。
