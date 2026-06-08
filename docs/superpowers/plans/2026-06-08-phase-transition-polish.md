# 阶段切换表现优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让狼人杀观战/对战界面的「白天 / 夜晚 / 候场」切换更明显——粗粒度电影感过场卡、常驻阶段徽章、切换泛光、脚本化建立镜头、以及席位锚定的「等待 LLM」候场光环。

**Architecture:** 纯前端、零后端改动。全部数据已在 `GameState`(`phase` / `dayNumber` / `victimId` / `liveCue.thinking` / `currentSpeakerId`)。可测试逻辑全部放进 `lib/phaseStage.ts` 纯函数(vitest，node 环境)；跨组件协调(过场卡 / 泛光 / 相机)通过 zustand store 的一个瞬时 `stageFx` nonce 字段同步;组件按本仓库既有惯例(见 belief-insight B1/B2 计划)作为薄壳，最后用 Chrome DevTools 真机验证。

**Tech Stack:** React 19 + TypeScript + Vite + Vitest + zustand 5 + motion(Framer v12，`motion/react`) + @react-three/fiber + three + lucide-react。

**约定(沿用本仓库既有模式):**
- 纯函数 → vitest 单测(`*.test.ts` 与源文件同目录，`npm test` 即 `vitest run`)。
- store 字段与 React/R3F 组件 → 真机验证(Task 9，Chrome DevTools)，因为测试环境是 node、无 jsdom。
- 全程古风仪式感文案，与现有「血色黎明 / 神圣审判厅」风格一致。

**关键时间常量(集中定义，全程复用):**
- `GRACE/MIN_GAP_MS = 1200`：两次阶段变化间隔小于此值视为「初始回放快进」，不弹过场(避免连接进行中对局时一连串闪卡)。
- `CARD_MS = 1800`：标题卡总时长(含淡入淡出)。
- `ESTABLISH_MS = 1100`：建立镜头(拉回圆桌全景)的持续时长。
- `DAY_DEATH_DELAY_MS = 500`：进入白天后延迟读取 `victimId`，以便把死讯并进同一张破晓卡。

---

## File Structure

**新增:**
- `frontend/src/lib/phaseStage.ts` — 纯函数:粗阶段派生、过场边界判定、卡片文案、徽章文案。**全部可单测。**
- `frontend/src/lib/phaseStage.test.ts` — 上述纯函数的 vitest 测试。
- `frontend/src/components/PhaseTransitionCard.tsx` — 过场标题卡 + 泛光层(单一探测器:检测粗阶段边界 → 写 `stageFx` → 渲染卡)。
- `frontend/src/components/PhaseBadge.tsx` — 左上角常驻阶段徽章。

**修改:**
- `frontend/src/store.ts` — 新增瞬时 `stageFx` 字段 + `fireStageFx` / `clearStageFx` 动作;在 `disconnectSpectate` 里复位。
- `frontend/src/components/ThreeCanvas.tsx` — `SpeakerSeat`/`ChessPiece` 加 `isThinking` 候场光环;`CameraTracker` 加 establishing 模式(读 `stageFx`)。
- `frontend/src/components/AlertOverlays.tsx` — 移除血色死讯卡分支(死讯已并入破晓卡),保留警长当选卡。
- `frontend/src/pages/GameApp.tsx` — 挂载 `PhaseTransitionCard` 与 `PhaseBadge`;把 booting 占位升级为「等待 LLM 入场」候场动画。

---

## Task 1: 纯函数 `lib/phaseStage.ts`(粗阶段 / 边界 / 文案)

**Files:**
- Create: `frontend/src/lib/phaseStage.ts`
- Test: `frontend/src/lib/phaseStage.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/phaseStage.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import {
  coarseStage,
  shouldShowCard,
  stageCardText,
  stageBadge,
  MIN_GAP_MS,
} from "./phaseStage";

describe("coarseStage", () => {
  it("maps fine phases to coarse buckets", () => {
    expect(coarseStage("START_SCREEN")).toBe("lobby");
    expect(coarseStage("ROLE_CHOICE")).toBe("lobby");
    expect(coarseStage("NIGHT_WOLF")).toBe("night");
    expect(coarseStage("NIGHT_SEER")).toBe("night");
    expect(coarseStage("NIGHT_WITCH")).toBe("night");
    expect(coarseStage("DAY_SHERIFF_RUN")).toBe("day");
    expect(coarseStage("DAY_ANNOUNCEMENT")).toBe("day");
    expect(coarseStage("DAY_DEBATE")).toBe("day");
    expect(coarseStage("DAY_VOTE")).toBe("day");
    expect(coarseStage("GAME_OVER")).toBe("over");
  });
});

describe("shouldShowCard", () => {
  it("fires only for night/day, on real change, after the burst gap", () => {
    expect(shouldShowCard("lobby", "night", 5000, MIN_GAP_MS)).toBe(true);
    expect(shouldShowCard("night", "day", 5000, MIN_GAP_MS)).toBe(true);
    expect(shouldShowCard("day", "night", 5000, MIN_GAP_MS)).toBe(true);
  });
  it("suppresses same-stage, lobby/over targets, and replay bursts", () => {
    expect(shouldShowCard("night", "night", 5000, MIN_GAP_MS)).toBe(false);
    expect(shouldShowCard("night", "lobby", 5000, MIN_GAP_MS)).toBe(false);
    expect(shouldShowCard("day", "over", 5000, MIN_GAP_MS)).toBe(false);
    expect(shouldShowCard("day", "night", 40, MIN_GAP_MS)).toBe(false);
  });
});

describe("stageCardText", () => {
  it("nightfall card", () => {
    expect(stageCardText("night", 2, null)).toEqual({
      kicker: "夜幕降临",
      title: "第 2 夜",
      sub: "屏息",
      death: false,
      victimSeat: null,
    });
  });
  it("peaceful daybreak card", () => {
    expect(stageCardText("day", 3, null)).toEqual({
      kicker: "曙光破晓",
      title: "第 3 日",
      sub: "黎明",
      death: false,
      victimSeat: null,
    });
  });
  it("daybreak merged with death", () => {
    expect(stageCardText("day", 3, 5)).toEqual({
      kicker: "曙光破晓",
      title: "第 3 日",
      sub: "5 号遇害",
      death: true,
      victimSeat: 5,
    });
  });
  it("returns null for non-card stages", () => {
    expect(stageCardText("lobby", 1, null)).toBeNull();
    expect(stageCardText("over", 1, null)).toBeNull();
  });
});

describe("stageBadge", () => {
  it("night badge", () => {
    expect(stageBadge("NIGHT_WOLF", 1)).toEqual({
      icon: "moon",
      dayText: "第 1 夜",
      phaseText: "狼人潜行屠杀",
    });
  });
  it("day badge falls back to a generic label", () => {
    expect(stageBadge("DAY_DEBATE", 2)).toEqual({
      icon: "sun",
      dayText: "第 2 日",
      phaseText: "圆形议事辩驳",
    });
  });
  it("lobby badge", () => {
    expect(stageBadge("START_SCREEN", 0)).toEqual({
      icon: "wait",
      dayText: "候场集结",
      phaseText: "等待入场",
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- phaseStage`
Expected: FAIL — `Failed to resolve import "./phaseStage"` / functions not defined.

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/lib/phaseStage.ts`:

```ts
import type { GameState } from "../types";

export type CoarseStage = "lobby" | "night" | "day" | "over";

/** Interval (ms) below which back-to-back stage changes are treated as an
 * initial replay burst (connecting to an in-progress run) and skip the card. */
export const MIN_GAP_MS = 1200;
export const CARD_MS = 1800;
export const ESTABLISH_MS = 1100;
export const DAY_DEATH_DELAY_MS = 500;

export function coarseStage(phase: GameState["phase"]): CoarseStage {
  if (phase === "START_SCREEN" || phase === "ROLE_CHOICE") return "lobby";
  if (phase === "NIGHT_WOLF" || phase === "NIGHT_SEER" || phase === "NIGHT_WITCH") return "night";
  if (phase === "GAME_OVER") return "over";
  return "day";
}

/** True when entering night/day is a genuine, non-burst boundary worth a card. */
export function shouldShowCard(
  prev: CoarseStage,
  next: CoarseStage,
  gapMs: number,
  minGapMs: number,
): boolean {
  if (next !== "night" && next !== "day") return false;
  if (prev === next) return false;
  if (gapMs < minGapMs) return false;
  return true;
}

export interface StageCard {
  kicker: string;
  title: string;
  sub: string;
  death: boolean;
  victimSeat: number | null;
}

export function stageCardText(
  stage: CoarseStage,
  dayNumber: number,
  victimSeat: number | null,
): StageCard | null {
  if (stage === "night") {
    return { kicker: "夜幕降临", title: `第 ${dayNumber} 夜`, sub: "屏息", death: false, victimSeat: null };
  }
  if (stage === "day") {
    if (victimSeat != null) {
      return { kicker: "曙光破晓", title: `第 ${dayNumber} 日`, sub: `${victimSeat} 号遇害`, death: true, victimSeat };
    }
    return { kicker: "曙光破晓", title: `第 ${dayNumber} 日`, sub: "黎明", death: false, victimSeat: null };
  }
  return null;
}

const PHASE_LABEL: Record<GameState["phase"], string> = {
  START_SCREEN: "等待入场",
  ROLE_CHOICE: "宿命契约抉择",
  NIGHT_WOLF: "狼人潜行屠杀",
  NIGHT_SEER: "神灵探秘查验",
  NIGHT_WITCH: "女巫配药抉择",
  DAY_SHERIFF_RUN: "警徽竞选演说",
  DAY_SHERIFF_VOTE: "警长封印公投",
  DAY_ANNOUNCEMENT: "审判布告死讯",
  DAY_DEBATE: "圆形议事辩驳",
  DAY_VOTE: "封印放逐公投",
  GAME_OVER: "审判宿命终结",
};

export interface StageBadge {
  icon: "moon" | "sun" | "wait";
  dayText: string;
  phaseText: string;
}

export function stageBadge(phase: GameState["phase"], dayNumber: number): StageBadge {
  const stage = coarseStage(phase);
  if (stage === "night") {
    return { icon: "moon", dayText: `第 ${dayNumber} 夜`, phaseText: PHASE_LABEL[phase] };
  }
  if (stage === "day") {
    return { icon: "sun", dayText: `第 ${dayNumber} 日`, phaseText: PHASE_LABEL[phase] };
  }
  if (stage === "over") {
    return { icon: "sun", dayText: "终局", phaseText: PHASE_LABEL[phase] };
  }
  return { icon: "wait", dayText: "候场集结", phaseText: "等待入场" };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- phaseStage`
Expected: PASS — all describe blocks green.

- [ ] **Step 5: Lint**

Run: `cd frontend && npm run lint`
Expected: no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/phaseStage.ts frontend/src/lib/phaseStage.test.ts
git commit -m "feat(fe): phaseStage pure helpers (coarseStage/shouldShowCard/stageCardText/stageBadge)"
```

---

## Task 2: store 瞬时 `stageFx` 同步字段

**Files:**
- Modify: `frontend/src/store.ts`

`stageFx` 是一个带单调递增 `nonce` 的瞬时信号:由过场卡的探测器写入(`fireStageFx`),被过场卡(渲染卡+泛光)和相机(建立镜头)读取。`nonce` 保证 `night→day→night` 这类重复 stage 也能每次重新触发。store 字段属薄改动,按本仓库惯例由 Task 9 真机验证。

- [ ] **Step 1: Add the type + state fields**

在 `frontend/src/store.ts` 顶部的 import 区(其它本地 import 旁)加入:

```ts
import type { CoarseStage } from "./lib/phaseStage";
```

在 store 的 state 接口/类型里(与 `insightSpeakerSeat` 等观战字段相邻处)加入字段声明:

```ts
  stageFx: { stage: CoarseStage; nonce: number } | null;
  fireStageFx: (stage: CoarseStage) => void;
  clearStageFx: () => void;
```

- [ ] **Step 2: Initialize + implement the actions**

在 `create<...>((set, get) => ({ ... }))` 的初始值区(`insightSpeakerSeat: null` 附近)加入初始值:

```ts
  stageFx: null,
```

在 actions 区(与 `connectSpectate` 等相邻)加入:

```ts
  fireStageFx: (stage) =>
    set((s) => ({ stageFx: { stage, nonce: (s.stageFx?.nonce ?? 0) + 1 } })),
  clearStageFx: () => set({ stageFx: null }),
```

- [ ] **Step 3: Reset on disconnect**

在 `disconnectSpectate` 动作体内(它已经会清理 `spectateSource` / insight 字段处)追加复位:

```ts
    set({ stageFx: null });
```
（与该动作里已有的 `set({...})` 合并到同一处即可，确保断开观战时不残留过场信号。）

- [ ] **Step 4: Lint**

Run: `cd frontend && npm run lint`
Expected: no TypeScript errors（`CoarseStage` 已从 `phaseStage` 正确导入）。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store.ts
git commit -m "feat(fe): store stageFx nonce signal for phase transitions"
```

---

## Task 3: `PhaseTransitionCard.tsx`(探测器 + 标题卡 + 泛光)

**Files:**
- Create: `frontend/src/components/PhaseTransitionCard.tsx`

单一探测器:用 `useEffect` 监听粗阶段变化，记录「上次变化时间戳」算出 `gap`，经 `shouldShowCard` 判定后调用 `fireStageFx`。进入白天时延迟 `DAY_DEATH_DELAY_MS` 再触发，以便把死讯并入破晓卡。渲染层读 `stageFx`，用 `AnimatePresence` 按 `nonce` 播放「泛光 + 暗角 + 居中文案」，`CARD_MS` 后自动 `clearStageFx`。`pointer-events-none`、`prefers-reduced-motion` 降级。

- [ ] **Step 1: Write the component**

Create `frontend/src/components/PhaseTransitionCard.tsx`:

```tsx
import { useEffect, useRef } from "react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { Moon, Sun, Skull } from "lucide-react";
import { useGameStore } from "../store";
import {
  coarseStage,
  shouldShowCard,
  stageCardText,
  MIN_GAP_MS,
  CARD_MS,
  DAY_DEATH_DELAY_MS,
  type CoarseStage,
} from "../lib/phaseStage";

export default function PhaseTransitionCard() {
  const phase = useGameStore((s) => s.state?.phase);
  const dayNumber = useGameStore((s) => s.state?.dayNumber ?? 0);
  const victimId = useGameStore((s) => s.state?.victimId ?? null);
  const stageFx = useGameStore((s) => s.stageFx);
  const fireStageFx = useGameStore((s) => s.fireStageFx);
  const clearStageFx = useGameStore((s) => s.clearStageFx);
  const reduce = useReducedMotion();

  // --- Detector: coarse-stage boundary -> fireStageFx -------------------
  const prevStageRef = useRef<CoarseStage | null>(null);
  const lastChangeTsRef = useRef<number>(performance.now());
  const dayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!phase) return;
    const next = coarseStage(phase);
    if (prevStageRef.current === null) {
      // First observation after mount: latch without firing.
      prevStageRef.current = next;
      lastChangeTsRef.current = performance.now();
      return;
    }
    const prev = prevStageRef.current;
    if (prev === next) return;
    const now = performance.now();
    const gap = now - lastChangeTsRef.current;
    prevStageRef.current = next;
    lastChangeTsRef.current = now;

    if (!shouldShowCard(prev, next, gap, MIN_GAP_MS)) return;

    if (next === "day") {
      // Delay so a same-tick player_died has been reduced -> merge into one card.
      if (dayTimerRef.current) clearTimeout(dayTimerRef.current);
      dayTimerRef.current = setTimeout(() => fireStageFx("day"), DAY_DEATH_DELAY_MS);
    } else {
      fireStageFx(next);
    }
  }, [phase, fireStageFx]);

  useEffect(() => () => { if (dayTimerRef.current) clearTimeout(dayTimerRef.current); }, []);

  // --- Auto-dismiss the card -------------------------------------------
  useEffect(() => {
    if (!stageFx) return;
    const t = setTimeout(() => clearStageFx(), CARD_MS);
    return () => clearTimeout(t);
  }, [stageFx?.nonce, clearStageFx]);

  const card = stageFx ? stageCardText(stageFx.stage, dayNumber, victimId) : null;
  const isNight = stageFx?.stage === "night";

  // Flash tint: warm bloom for dawn, deep darken for nightfall.
  const flashClass = isNight
    ? "bg-[radial-gradient(ellipse_at_center,_rgba(20,8,40,0.0),_rgba(8,2,18,0.85))]"
    : card?.death
      ? "bg-[radial-gradient(ellipse_at_center,_rgba(120,10,10,0.0),_rgba(80,6,6,0.7))]"
      : "bg-[radial-gradient(ellipse_at_center,_rgba(255,210,140,0.18),_rgba(120,60,8,0.0))]";

  return (
    <AnimatePresence>
      {stageFx && card && (
        <motion.div
          key={stageFx.nonce}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduce ? 0.15 : 0.35 }}
          className="fixed inset-0 z-[110] pointer-events-none flex items-center justify-center"
        >
          {/* one-shot flash / darken layer */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: reduce ? 0.5 : [0, 1, 0.55] }}
            transition={{ duration: reduce ? 0.2 : 0.9, times: reduce ? undefined : [0, 0.25, 1] }}
            className={`absolute inset-0 ${flashClass}`}
          />
          {/* centered woodcut title (light vignette, lets the camera move read through) */}
          <motion.div
            initial={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.92, y: 18 }}
            animate={reduce ? { opacity: 1 } : { opacity: 1, scale: 1, y: 0 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, scale: 1.04, y: -14 }}
            transition={{ type: "spring", stiffness: 260, damping: 26 }}
            className="relative flex flex-col items-center select-none px-10 py-6"
          >
            {isNight ? (
              <Moon className="w-12 h-12 text-violet-300 drop-shadow-[0_0_18px_rgba(168,85,247,0.8)] mb-2" />
            ) : card.death ? (
              <Skull className="w-12 h-12 text-red-400 drop-shadow-[0_0_18px_rgba(220,38,38,0.8)] mb-2 animate-pulse" />
            ) : (
              <Sun className="w-12 h-12 text-amber-300 drop-shadow-[0_0_18px_rgba(251,191,36,0.85)] mb-2" />
            )}
            <span
              className={`font-serif text-sm tracking-[0.6em] uppercase font-black mb-1 ${
                isNight ? "text-violet-300/90" : card.death ? "text-red-400/90" : "text-amber-300/90"
              }`}
            >
              {card.kicker}
            </span>
            <h1
              className={`font-sans font-black text-5xl tracking-widest ${
                isNight ? "text-violet-50" : "text-amber-50"
              } drop-shadow-[0_2px_24px_rgba(0,0,0,0.9)]`}
            >
              {card.title}
            </h1>
            <span
              className={`font-mono text-xs tracking-[0.4em] mt-2 ${
                card.death ? "text-red-300 font-black" : "text-zinc-300/80"
              }`}
            >
              · {card.sub} ·
            </span>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

- [ ] **Step 2: Lint**

Run: `cd frontend && npm run lint`
Expected: no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PhaseTransitionCard.tsx
git commit -m "feat(fe): PhaseTransitionCard cinematic stage card + flash (coarse night/day, merged death)"
```

---

## Task 4: `PhaseBadge.tsx`(左上角常驻阶段徽章)

**Files:**
- Create: `frontend/src/components/PhaseBadge.tsx`

读 `phase`/`dayNumber`，经 `stageBadge` 输出「图标 + 第 N 夜/日 + 阶段名」。固定左上角(TopHeader 下方)，避开 InsightDock(右)/胜负横幅(右上)/LiveCueAnchors(右下)。

- [ ] **Step 1: Write the component**

Create `frontend/src/components/PhaseBadge.tsx`:

```tsx
import { Moon, Sun, Hourglass } from "lucide-react";
import { useGameStore } from "../store";
import { stageBadge } from "../lib/phaseStage";

export default function PhaseBadge() {
  const phase = useGameStore((s) => s.state?.phase);
  const dayNumber = useGameStore((s) => s.state?.dayNumber ?? 0);
  if (!phase) return null;

  const badge = stageBadge(phase, dayNumber);
  const isNight = badge.icon === "moon";
  const isWait = badge.icon === "wait";

  const ring = isNight
    ? "border-violet-500/70 shadow-[0_0_16px_rgba(139,92,246,0.45)] text-violet-200"
    : isWait
      ? "border-zinc-600/70 shadow-[0_0_12px_rgba(82,82,91,0.4)] text-zinc-300"
      : "border-amber-500/70 shadow-[0_0_16px_rgba(245,158,11,0.45)] text-amber-100";

  return (
    <div className="absolute top-16 left-4 z-30 pointer-events-none select-none">
      <div
        className={`flex items-center gap-3 bg-black/55 backdrop-blur-md border rounded-lg px-3.5 py-2 ${ring}`}
      >
        <div className="w-9 h-9 rounded-full bg-black/60 border border-current/40 flex items-center justify-center shrink-0">
          {isNight ? (
            <Moon className="w-5 h-5 fill-current/30 animate-pulse" />
          ) : isWait ? (
            <Hourglass className="w-5 h-5 animate-spin" style={{ animationDuration: "3s" }} />
          ) : (
            <Sun className="w-5 h-5 animate-spin-slow" />
          )}
        </div>
        <div className="flex flex-col leading-tight">
          <span className="font-serif font-black text-sm tracking-wider">{badge.dayText}</span>
          <span className="font-mono text-[10px] uppercase tracking-widest text-current/80">
            {badge.phaseText}
          </span>
        </div>
      </div>
    </div>
  );
}
```

> 注:`animate-spin-slow` 已在 `TopHeader.tsx` 中使用，是项目内已存在的工具类，无需新增。

- [ ] **Step 2: Lint**

Run: `cd frontend && npm run lint`
Expected: no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PhaseBadge.tsx
git commit -m "feat(fe): PhaseBadge persistent top-left stage indicator"
```

---

## Task 5: GameApp 挂载过场卡 / 徽章，并升级候场 booting

**Files:**
- Modify: `frontend/src/pages/GameApp.tsx`

- [ ] **Step 1: Add imports**

在 `frontend/src/pages/GameApp.tsx` 顶部 import 区(`AlertOverlays` 等旁)加入:

```tsx
import PhaseTransitionCard from "../components/PhaseTransitionCard";
import PhaseBadge from "../components/PhaseBadge";
import { Moon } from "lucide-react";
```

- [ ] **Step 2: Upgrade the booting (候场) placeholder**

把现有 `spectateBooting` 分支(`GameApp.tsx:113-123`)整体替换为「等待 LLM 入场」候场动画:

```tsx
  if (spectateBooting) {
    return (
      <div className="min-h-screen bg-[#0d0907] flex flex-col items-center justify-center gap-5 text-zinc-400">
        <div className="relative w-20 h-20 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border border-violet-700/40 animate-ping" />
          <div className="absolute inset-2 rounded-full border border-amber-700/30 animate-ping [animation-delay:400ms]" />
          <Moon className="w-9 h-9 text-violet-300/90 animate-pulse" />
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="font-serif font-black text-sm tracking-[0.4em] text-zinc-200 uppercase">
            候场集结
          </span>
          <span className="font-mono text-[11px] tracking-widest text-zinc-500 uppercase">
            等待 LLM 入场…
          </span>
        </div>
        <span className="text-[10px] text-zinc-600 font-sans">{runId}</span>
      </div>
    );
  }
```

- [ ] **Step 3: Mount the badge + transition card in the live layout**

在 live 渲染分支里，把 `<PhaseBadge />` 加进覆盖层(在 `TopHeader` 之后、内容 `flex-grow` 行附近，即 `GameApp.tsx:157` 的 `absolute inset-0 ... z-10` 容器内顶部)；把 `<PhaseTransitionCard />` 与 `<AlertOverlays />` 并列挂载。具体:在现有 `<AlertOverlays />`(`GameApp.tsx:193`)那一行的上方插入:

```tsx
      <PhaseTransitionCard />
```

并在 `<TopHeader ... />` 所在的 `pointer-events-auto` 块之后、`flex-grow` 行之前插入徽章(它自身 `absolute`，定位不受 flex 影响):

```tsx
        <PhaseBadge />
```

- [ ] **Step 4: Lint**

Run: `cd frontend && npm run lint`
Expected: no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/GameApp.tsx
git commit -m "feat(fe): mount PhaseTransitionCard + PhaseBadge, upgrade booting to 候场 animation"
```

---

## Task 6: AlertOverlays 移除死讯卡(并入破晓卡)

**Files:**
- Modify: `frontend/src/components/AlertOverlays.tsx`

死讯现已并进 `PhaseTransitionCard` 的破晓卡(`stageCardText` 的 `death` 变体)。移除 AlertOverlays 里的血色死讯 `AnimatePresence` 块，避免双卡叠加；保留警长当选卡。

- [ ] **Step 1: Remove the murder-alert state + block**

删除 `isMurderAlert` 常量(`AlertOverlays.tsx:28`):

```tsx
  const isMurderAlert = phase === "DAY_ANNOUNCEMENT" && victimId !== null && victimId !== undefined;
```

并删除其下整段血色死讯 `<AnimatePresence>…</AnimatePresence>`(`AlertOverlays.tsx:32-73`，即包含 `isMurderAlert &&` 的第一个 AnimatePresence 块)。保留第二个(警长当选)`<AnimatePresence>` 块不动。

- [ ] **Step 2: Clean up now-unused references**

删除文件顶部不再使用的 import 与选择器:
- 移除 `import { Skull, Shield } from "lucide-react";` 中的 `Skull`，改为 `import { Shield } from "lucide-react";`
- 移除 `const phase = useGameStore((state) => state.state?.phase);` 与 `const victimId = useGameStore((state) => state.state?.victimId);`(若 `phase`/`victimId` 在保留块中已无引用)。

- [ ] **Step 3: Lint**

Run: `cd frontend && npm run lint`
Expected: no TypeScript errors / no unused-variable errors（`noUnusedLocals` 在 strict 下会报，必须清干净）。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/AlertOverlays.tsx
git commit -m "refactor(fe): drop AlertOverlays murder card (merged into daybreak card)"
```

---

## Task 7: ThreeCanvas 席位锚定「思考中」候场光环

**Files:**
- Modify: `frontend/src/components/ThreeCanvas.tsx`

正在等待 LLM 的那名玩家(`liveCue.thinking.seat`)的棋子加一个柔和脉动的青蓝色光环，区别于发言时的高亮。

- [ ] **Step 1: Extend SpeakerSeat props + render the ring**

在 `SpeakerPillarProps`(`ThreeCanvas.tsx:441`)接口中追加:

```tsx
  isThinking: boolean;
```

在 `SpeakerSeat` 解构(`ThreeCanvas.tsx:450`)中加入 `isThinking`:

```tsx
function SpeakerSeat({ id, name, isAlive, isUser, isSpeaking, isThinking, angle }: SpeakerPillarProps) {
```

在 `SpeakerSeat` 内、活人分支里发言光环 `{isSpeaking && (…ringGeometry…)}`(`ThreeCanvas.tsx:514-519`)之后，追加思考光环:

```tsx
            {isThinking && !isSpeaking && (
              <mesh position={[0, -0.05, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <ringGeometry args={[0.5, 0.62, 24]} />
                <meshBasicMaterial color="#22d3ee" transparent opacity={0.45} side={THREE.DoubleSide} />
              </mesh>
            )}
```

- [ ] **Step 2: Compute the thinking seat + pass it down**

在 `ThreeCanvas` 主体里(`previewPlayers` 之后、`ThreeCanvas.tsx:728` 附近)加入:

```tsx
  const thinkingSeat = gameState?.liveCue?.thinking?.seat ?? null;
```

在渲染玩家数组处(`ThreeCanvas.tsx:825-837` 的 `previewPlayers.map`)给 `<SpeakerSeat>` 增加 prop:

```tsx
                isThinking={thinkingSeat === p.id}
```

- [ ] **Step 3: Lint**

Run: `cd frontend && npm run lint`
Expected: no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ThreeCanvas.tsx
git commit -m "feat(fe): seat-anchored thinking halo for 候场 (waiting on LLM)"
```

---

## Task 8: CameraTracker 脚本化「建立镜头」

**Files:**
- Modify: `frontend/src/components/ThreeCanvas.tsx`

粗阶段切换时(读 `stageFx.nonce`)，相机在 `ESTABLISH_MS` 内被强制拉到圆桌俯瞰全景，盖过发言者跟随；结束后自动交还给现有 damp 逻辑。因为卡是「轻暗角」而非全屏黑幕，这段运镜能透出来被看到。

- [ ] **Step 1: Import the constant + read stageFx**

在 `ThreeCanvas.tsx` 顶部 import 区加入:

```tsx
import { ESTABLISH_MS } from "../lib/phaseStage";
```

在 `CameraTracker`(`ThreeCanvas.tsx:77`)函数体内、现有选择器旁加入:

```tsx
  const stageFx = useGameStore((state) => state.stageFx);
  const establishUntilRef = useRef<number>(0);
  const lastFxNonceRef = useRef<number>(0);
```

- [ ] **Step 2: Latch the establishing window on each new nonce**

在 `CameraTracker` 内新增一个 effect(放在已有的 `useEffect` 之后、`useFrame` 之前):

```tsx
  useEffect(() => {
    const nonce = stageFx?.nonce ?? 0;
    if (nonce && nonce !== lastFxNonceRef.current) {
      lastFxNonceRef.current = nonce;
      establishUntilRef.current = performance.now() + ESTABLISH_MS;
    }
  }, [stageFx?.nonce]);
```

- [ ] **Step 3: Override target to overview while establishing**

在 `CameraTracker` 的 `useFrame`(`ThreeCanvas.tsx:118`)内，**在** `if (phase === "START_SCREEN") { … }` 块之后、相机 damp 步进(`ThreeCanvas.tsx:155` 的 `camera.position.x = …`)**之前**，插入:

```tsx
    // Scripted establishing shot on phase transition: pull back to the round-table overview.
    if (performance.now() < establishUntilRef.current && phase !== "START_SCREEN") {
      const pCount = setupCount !== null ? setupCount : (players.length || 6);
      const radius = Math.max(5, pCount * 0.72);
      targetCamPos.current.set(0, radius * 1.85, radius * 2.6);
      targetLookAt.current.set(0, 0.4, 0);
    }
```

> 这样建立镜头期间每帧覆盖 `targetCamPos`/`targetLookAt` 为全景值，盖过 speaker-effect 设的目标；`performance.now()` 超过窗口后不再覆盖，相机自然 damp 回跟随发言者。

- [ ] **Step 4: Lint**

Run: `cd frontend && npm run lint`
Expected: no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ThreeCanvas.tsx
git commit -m "feat(fe): scripted establishing camera shot on phase transitions"
```

---

## Task 9: Chrome DevTools 真机验证

**Files:** 无(纯验证)。需要后端 API + 前端 dev server 同时运行。

> 组件 / store / 3D 这部分按本仓库惯例(belief-insight B1/B2 计划同款)用真机验证，因为测试环境是 node、无 jsdom。

- [ ] **Step 1: Start backend + frontend**

Run(仓库根目录):
```bash
DEEPSEEK_API_KEY=sk-xxxx OBS_READY_REQUIRE_LLM=0 uv run werewolf-api --port 8010
```
另一终端:
```bash
cd frontend && npm run dev
```
（无真 Key 时可用 demo 配置走 6 人离线机器人观战，仍能驱动 phase/thinking 事件。）

- [ ] **Step 2: 6 人局 — 过场卡 + 徽章 + 候场**

用 Chrome DevTools MCP 打开 Vite 地址 →「进入盘面」→ 起 6 人 god 观战。验证(逐一截图记录):
1. 开局停在「候场集结 / 等待 LLM 入场」动画(双 ping 环 + 月图标)，而非旧的纯 spinner。
2. 进入首夜:居中弹出「夜幕降临 / 第 1 夜 / · 屏息 ·」紫色标题卡，约 1.8s 自动消失；同时屏幕压暗一下。
3. 左上角常驻徽章显示「第 1 夜 + 狼人潜行屠杀」，月图标脉动。
4. 某玩家轮到发言前，其棋子出现青蓝色「思考」光环(区别于发言时的高亮)，发言开始即消失。
5. 进入白天:弹「曙光破晓 / 第 N 日」金色卡；**若昨夜有死亡**，同一张卡下方显示「X 号遇害」并带骷髅(确认**不再**出现旧的独立血色死讯卡)。
6. 切换瞬间相机先拉到圆桌全景、停留约 1s，再回到跟随发言者(运镜平滑、无硬跳)。

- [ ] **Step 3: 12 人局 — 不挤 / 不误触发**

起 12 人 god 观战。验证:
1. 徽章与过场卡在多人下排版正常、不与 InsightDock(右)冲突。
2. 连接一个已进行中的对局时，初始事件回放**不会**连闪多张过场卡(MIN_GAP_MS 抑制生效)，只在追上实时后正常弹卡。

- [ ] **Step 4: 座位视角 + reduced-motion**

1. 以座位视角(`view=seat`)进入一局，确认过场卡 / 徽章 / 候场光环同样工作，且不挡 HumanInputPanel 操作(卡为 `pointer-events-none`)。
2. 在 DevTools 命令面板执行 “Emulate CSS prefers-reduced-motion: reduce”，重进一局，确认标题卡降级为快速淡入淡出、无弹簧缩放、泛光减弱。

- [ ] **Step 5: 记录验证结果并提交(若有微调)**

把验证结论(含异常与修复)记录后，如有为通过验证而做的微调:
```bash
git add -A
git commit -m "test(fe): verify phase transition polish on 6p/12p/seat + reduced-motion"
```

---

## Self-Review

**1. Spec coverage**(对照共识规格逐条):
- ✅ 光线变化(白天更亮/夜晚更暗)+ 切换泛光闪 → Task 3 的 flash 层(保留稳态调色，仅切换时泛光/压暗)。
- ✅ 阶段符号/状态标识(一眼知道当前阶段) → Task 1 `stageBadge` + Task 4 `PhaseBadge`(左上角常驻)。
- ✅ 过场动画、不硬切 → Task 1 `stageCardText` + Task 3 `PhaseTransitionCard`(粗粒度、每轮、电影感、非阻塞)。
- ✅ 第一次进入各阶段镜头/UI 更顺滑 → Task 8 建立镜头 + Task 3 卡的淡入淡出。
- ✅ 候场(等待 LLM,含开局与对话间隙)→ Task 7 席位思考光环 + Task 5 booting 升级。
- ✅ 死讯并入破晓卡(不叠卡)→ Task 1 `death` 变体 + Task 6 移除旧死讯卡。
- ✅ 范围=实时局全部(god/座位/设置屏)，不含 Replay → 仅改 `GameApp`/`ThreeCanvas`，未碰 `ReplayPage`。
- ✅ 无音效 → 全程纯视觉。
- ✅ `prefers-reduced-motion` → Task 3 `useReducedMotion` 降级 + Task 9 验证。
- ✅ 抑制初始回放连闪 → Task 1 `shouldShowCard` 的 `MIN_GAP_MS` gap 判定。

**2. Placeholder scan:** 无 TBD/TODO；每个改动步骤都给了完整代码或精确锚点行号。

**3. Type consistency:** `CoarseStage` / `stageFx: { stage; nonce }` / `fireStageFx` / `clearStageFx` / `stageCardText` 的 `StageCard`(`kicker/title/sub/death/victimSeat`) / `stageBadge` 的 `StageBadge`(`icon: "moon"|"sun"|"wait"`) 在 Task 1/2/3/4/8 间命名一致；`ESTABLISH_MS`/`CARD_MS`/`MIN_GAP_MS`/`DAY_DEATH_DELAY_MS` 仅定义于 `phaseStage.ts` 并被各处复用。
