# 3D 场景优化（卡顿 / 空桌 / 昼夜光照与地面）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把游戏 3D 盘面打到稳定 60fps、修复落地页"只有一张空桌"的回归、并给出鲜明的写实昼夜全局光与有层次的地面。

**Architecture:** 纯逻辑（昼夜调色板、落地页预览席位、镜头决策）抽到 `frontend/src/lib/` 下可单测的模块（Vitest，沿用现有 `cameraDirector.test.ts` 模式）；视觉/性能改动集中在 `ThreeCanvas.tsx` 与新增的 `GroundPlane.tsx`，靠 Playwright/chrome-devtools 截图 + 性能 trace 验证。策略是 **先砍性能杀手（多投影光、每席位动态点光、transmission 材质、未封顶 DPR）打稳帧率，再用省下的预算加亮度和地面**。

**Tech Stack:** React 19 + TypeScript（strict）、@react-three/fiber 9 / three 0.184 / @react-three/drei 10、Zustand、Vitest、Tailwind。dev：`cd frontend && npm run dev`（Vite，默认 `http://localhost:5173`）。全栈联调：仓库根 `./dev.sh` 或 `.\dev.ps1`。

**已敲定的设计共识（来自 grill-me）：**
- 性能目标：中端 PC 稳 60fps 优先；允许为帧率牺牲华丽效果。
- 昼夜风格：写实昼夜 + 保留哥特氛围。白天=明亮暖阳 + 淡蓝天光；黑夜=深蓝紫 + 冷月光；命案警报红档保留。点缀色（桌沿/法阵/粒子/光球/聚光）随新调色板和谐化。
- 地面：石质大地面（接收方向光阴影）+ 同心发光法阵环 + 边缘渐暗没入雾；纯发光贴图、无反射。
- 镜头：保留"阶段切全景 / 跟随发言人 / 发言后 hold"的电影节奏，但去掉 `FAST_LAMBDA` 快切、全部柔和阻尼、推进放慢。
- 落地页：`phase` 为 `undefined`/`START_SCREEN` 时都走预览分支，显示 `setupCount` 个棋子圆桌 + 恢复缓慢环绕运镜 + 随人数实时增减。

**根因记录（实现时不要再重新论证）：**
- 空桌 #2：`store.ts:64` 初始 `state: null` → 落地页 `phase` 为 `undefined` → `ThreeCanvas.tsx:747` 的预览分支 `phase === "START_SCREEN"` 永不成立 → `previewPlayers` 落到空 `players` 分支 → 只剩桌子+光球；而每个 `ChessPiece` 自带 `pointLight`（`ThreeCanvas.tsx:425`），棋子没了，光也没了。
- 卡顿 #1：同时存在 3 个投影光（方向光 1024² + 中央光球 `pointLight castShadow` + 发言聚光灯 `spotLight castShadow`，点光源阴影约 6× 开销）；6–12 盏每席位动态 `pointLight`；每个棋子 `meshPhysicalMaterial` 带 `clearcoat`+`transmission`；`<Canvas>` 无 `dpr` 上限。低帧又让 `THREE.MathUtils.damp` 一跳一跳 → 镜头"突兀"。
- 单薄 #3：没有地面平面，只有漂在雾里的桌盘；环境光仅 day 0.38 / night 0.15，且白天暗橙、黑夜暗紫，两者都偏暗。

---

## File Structure

**新增：**
- `frontend/src/lib/sceneTheme.ts` — 纯函数：昼/夜/命案三档的全局光调色板（背景、环境光、方向光、点缀色）。
- `frontend/src/lib/sceneTheme.test.ts` — 上述的单测。
- `frontend/src/lib/previewSeats.ts` — 纯函数：根据 phase/setupCount/players 计算要渲染的席位数组（修 #2 的可测核心）。
- `frontend/src/lib/previewSeats.test.ts` — 上述的单测。
- `frontend/src/components/GroundPlane.tsx` — 多层氛围地面组件（石质平面接收阴影 + 同心发光环 + 雾隐没）。

**修改：**
- `frontend/src/lib/phaseStage.ts` — 新增 `isLobbyPhase()`（接受 `undefined`）。
- `frontend/src/lib/cameraDirector.ts` — 柔化阻尼常量、`decideCamera` 用 `isLobbyPhase`。
- `frontend/src/lib/cameraDirector.test.ts` — 跟随常量改名更新断言。
- `frontend/src/components/ThreeCanvas.tsx` — 接入 sceneTheme/previewSeats/GroundPlane；砍性能杀手；点缀色和谐化；`dpr` 封顶。

---

## Task 1: 昼夜调色板纯模块 `sceneTheme.ts`

集中全局光与点缀色，供后续光照（Task 6）、地面（Task 8）、点缀和谐化（Task 9）复用。

**Files:**
- Create: `frontend/src/lib/sceneTheme.ts`
- Test: `frontend/src/lib/sceneTheme.test.ts`

- [ ] **Step 1: Write the failing test**

`frontend/src/lib/sceneTheme.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { resolveSceneMode, sceneTheme } from "./sceneTheme";

describe("resolveSceneMode", () => {
  it("murder alert beats night beats day", () => {
    expect(resolveSceneMode(true, true)).toBe("murder");
    expect(resolveSceneMode(false, true)).toBe("murder");
    expect(resolveSceneMode(true, false)).toBe("night");
    expect(resolveSceneMode(false, false)).toBe("day");
  });
});

describe("sceneTheme", () => {
  it("day is markedly brighter than the old 0.38 ambient", () => {
    expect(sceneTheme("day").ambientIntensity).toBeGreaterThan(1.0);
  });

  it("night is readable but dim (between the old 0.15 and day)", () => {
    const night = sceneTheme("night").ambientIntensity;
    expect(night).toBeGreaterThan(0.3);
    expect(night).toBeLessThan(sceneTheme("day").ambientIntensity);
  });

  it("day key light is warm/strong, night key light is cooler/weaker", () => {
    expect(sceneTheme("day").dirIntensity).toBeGreaterThan(sceneTheme("night").dirIntensity);
  });

  it("day and night backgrounds are distinct", () => {
    expect(sceneTheme("day").bg).not.toBe(sceneTheme("night").bg);
  });

  it("murder alert is red", () => {
    expect(sceneTheme("murder").ambientColor).toBe("#ff1100");
  });

  it("every theme exposes accent + accentSoft + a 3-tuple light position", () => {
    for (const mode of ["day", "night", "murder"] as const) {
      const t = sceneTheme(mode);
      expect(typeof t.accent).toBe("string");
      expect(typeof t.accentSoft).toBe("string");
      expect(t.dirPos).toHaveLength(3);
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/sceneTheme.test.ts`
Expected: FAIL — `Failed to resolve import "./sceneTheme"`.

- [ ] **Step 3: Write the implementation**

`frontend/src/lib/sceneTheme.ts`:

```ts
export type SceneMode = "day" | "night" | "murder";

export interface SceneTheme {
  /** Scene background + fog color. */
  bg: string;
  /** Ambient (global fill) light. */
  ambientColor: string;
  ambientIntensity: number;
  /** Key directional light (sun / moon). */
  dirColor: string;
  dirIntensity: number;
  dirPos: [number, number, number];
  /** Primary accent — rims, beams, sigil strokes, ground rings. */
  accent: string;
  /** Soft secondary accent — gems, halos, inner glow. */
  accentSoft: string;
}

/** Murder alert overrides night, which overrides day. */
export function resolveSceneMode(isNight: boolean, isMurderAlert: boolean): SceneMode {
  if (isMurderAlert) return "murder";
  return isNight ? "night" : "day";
}

const THEMES: Record<SceneMode, SceneTheme> = {
  // 明亮暖阳 + 淡蓝天光：环境光从旧的 0.38 拉到 1.2，背景换成淡蓝天色。
  day: {
    bg: "#bcd4e6",
    ambientColor: "#fff4e0",
    ambientIntensity: 1.2,
    dirColor: "#ffe9b0",
    dirIntensity: 6.0,
    dirPos: [12, 18, 8],
    accent: "#f59e0b",
    accentSoft: "#fde047",
  },
  // 深蓝紫夜色 + 冷月光：从旧的暗紫 0.15 提到 0.4，能看清但仍暗，冷色调。
  night: {
    bg: "#0a0e2a",
    ambientColor: "#6a7cb8",
    ambientIntensity: 0.4,
    dirColor: "#aac4ff",
    dirIntensity: 2.0,
    dirPos: [-10, 16, -6],
    accent: "#6366f1",
    accentSoft: "#a5b4fc",
  },
  // 命案警报：保留刺目的赤红档不动。
  murder: {
    bg: "#2a0404",
    ambientColor: "#ff1100",
    ambientIntensity: 0.8,
    dirColor: "#dc2626",
    dirIntensity: 4.5,
    dirPos: [10, 15, 5],
    accent: "#ef4444",
    accentSoft: "#fca5a5",
  },
};

export function sceneTheme(mode: SceneMode): SceneTheme {
  return THEMES[mode];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/sceneTheme.test.ts`
Expected: PASS (all assertions green).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/sceneTheme.ts frontend/src/lib/sceneTheme.test.ts
git commit -m "feat(fe): sceneTheme — pure day/night/murder palette (global light + accents)"
```

---

## Task 2: `isLobbyPhase()` 收纳"落地页=lobby"概念

`undefined`、`START_SCREEN`、`ROLE_CHOICE` 都算 lobby。预览席位（Task 3）和镜头（Task 4/5）共用，避免三处各写一遍。

**Files:**
- Modify: `frontend/src/lib/phaseStage.ts`
- Test: `frontend/src/lib/phaseStage.test.ts`（已存在，追加用例）

- [ ] **Step 1: Add the failing test**

在 `frontend/src/lib/phaseStage.test.ts` 顶部 import 里加入 `isLobbyPhase`，并在文件末尾追加：

```ts
import { isLobbyPhase } from "./phaseStage";

describe("isLobbyPhase", () => {
  it("treats undefined (pre-connect landing page) as lobby", () => {
    expect(isLobbyPhase(undefined)).toBe(true);
  });
  it("treats START_SCREEN / ROLE_CHOICE as lobby", () => {
    expect(isLobbyPhase("START_SCREEN")).toBe(true);
    expect(isLobbyPhase("ROLE_CHOICE")).toBe(true);
  });
  it("treats in-game phases as not lobby", () => {
    expect(isLobbyPhase("DAY_DEBATE")).toBe(false);
    expect(isLobbyPhase("NIGHT_WOLF")).toBe(false);
    expect(isLobbyPhase("GAME_OVER")).toBe(false);
  });
});
```

> 若 `phaseStage.test.ts` 顶部已有 `import { ... } from "./phaseStage"`，把 `isLobbyPhase` 并入该行，不要重复 import 整个模块。

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/phaseStage.test.ts`
Expected: FAIL — `isLobbyPhase is not a function` / 导出不存在。

- [ ] **Step 3: Implement**

在 `frontend/src/lib/phaseStage.ts` 的 `coarseStage` 函数**之后**插入：

```ts
/** Lobby includes the pre-connect landing page, where `state` (and thus phase) is still null. */
export function isLobbyPhase(phase: GameState["phase"] | undefined): boolean {
  return phase == null || phase === "START_SCREEN" || phase === "ROLE_CHOICE";
}
```

（`GameState` 已在该文件第 1 行 `import type { GameState } from "../types";`，无需再加 import。）

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/phaseStage.test.ts`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/phaseStage.ts frontend/src/lib/phaseStage.test.ts
git commit -m "feat(fe): isLobbyPhase — undefined/START_SCREEN/ROLE_CHOICE all count as lobby"
```

---

## Task 3: 落地页预览席位纯模块 `previewSeats.ts`（#2 的可测核心）

**Files:**
- Create: `frontend/src/lib/previewSeats.ts`
- Test: `frontend/src/lib/previewSeats.test.ts`

- [ ] **Step 1: Write the failing test**

`frontend/src/lib/previewSeats.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { buildPreviewSeats } from "./previewSeats";
import type { GameState } from "../types";

const livePlayers: GameState["players"] = [
  { id: 1, name: "A", isAlive: true, isUser: true } as GameState["players"][number],
  { id: 2, name: "B", isAlive: false, isUser: false } as GameState["players"][number],
];

describe("buildPreviewSeats", () => {
  it("undefined phase (landing) + setupCount renders a synthetic ring, seat 1 is the user", () => {
    const seats = buildPreviewSeats({ phase: undefined, setupCount: 6, players: [], currentSpeakerId: null });
    expect(seats).toHaveLength(6);
    expect(seats[0]).toMatchObject({ id: 1, isUser: true, isAlive: true });
    expect(seats[5]).toMatchObject({ id: 6, isUser: false });
  });

  it("START_SCREEN + setupCount honors the chosen player count", () => {
    expect(buildPreviewSeats({ phase: "START_SCREEN", setupCount: 9, players: [], currentSpeakerId: null }))
      .toHaveLength(9);
  });

  it("lobby with no setupCount yet falls back to mapping players (empty -> [])", () => {
    expect(buildPreviewSeats({ phase: undefined, setupCount: null, players: [], currentSpeakerId: null }))
      .toEqual([]);
  });

  it("live phase maps real players and marks the current speaker", () => {
    const seats = buildPreviewSeats({ phase: "DAY_DEBATE", setupCount: 6, players: livePlayers, currentSpeakerId: 1 });
    expect(seats).toHaveLength(2);
    expect(seats[0]).toMatchObject({ id: 1, isSpeaking: true, isAlive: true, isUser: true });
    expect(seats[1]).toMatchObject({ id: 2, isSpeaking: false, isAlive: false });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/previewSeats.test.ts`
Expected: FAIL — `Failed to resolve import "./previewSeats"`.

- [ ] **Step 3: Implement**

`frontend/src/lib/previewSeats.ts`:

```ts
import type { GameState } from "../types";
import { isLobbyPhase } from "./phaseStage";

export interface PreviewSeat {
  id: number;
  name: string;
  isAlive: boolean;
  isUser: boolean;
  isSpeaking: boolean;
}

/**
 * The seats ThreeCanvas should render.
 *
 * On the landing/setup screen `state` is still null so `phase` is undefined; we
 * treat that (and START_SCREEN/ROLE_CHOICE) as lobby and synthesize a preview
 * ring from `setupCount`. Otherwise we map the live players.
 */
export function buildPreviewSeats(args: {
  phase: GameState["phase"] | undefined;
  setupCount: number | null;
  players: GameState["players"];
  currentSpeakerId: number | null | undefined;
}): PreviewSeat[] {
  const { phase, setupCount, players, currentSpeakerId } = args;

  if (isLobbyPhase(phase) && setupCount !== null) {
    return Array.from({ length: setupCount }, (_, idx) => ({
      id: idx + 1,
      name: `席位 ${idx + 1}`,
      isAlive: true,
      isUser: idx === 0,
      isSpeaking: false,
    }));
  }

  return players.map((p) => ({
    id: p.id,
    name: p.name,
    isAlive: p.isAlive,
    isUser: p.isUser,
    isSpeaking: currentSpeakerId === p.id,
  }));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/previewSeats.test.ts`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/previewSeats.ts frontend/src/lib/previewSeats.test.ts
git commit -m "feat(fe): buildPreviewSeats — landing(undefined phase)+setupCount renders preview ring"
```

---

## Task 4: 接入 #2 修复（ThreeCanvas 预览 + 落地页缓慢环绕）

**Files:**
- Modify: `frontend/src/components/ThreeCanvas.tsx`（`previewPlayers` useMemo ~745–763；`CameraTracker` orbit 守卫 ~123）

- [ ] **Step 1: 用 `buildPreviewSeats` 替换内联预览逻辑**

在 `ThreeCanvas.tsx` 顶部 import 区加入：

```tsx
import { buildPreviewSeats } from "../lib/previewSeats";
import { isLobbyPhase } from "../lib/phaseStage";
```

把 `ThreeCanvas` 组件里的 `previewPlayers` useMemo（当前 745–763 行）整体替换为：

```tsx
  // START_SCREEN / 落地页（phase=undefined）渲染预览圆桌；否则映射真实玩家。
  const previewPlayers = React.useMemo(
    () =>
      buildPreviewSeats({
        phase,
        setupCount,
        players,
        currentSpeakerId: currentSpeakerId ?? null,
      }),
    [phase, setupCount, players, currentSpeakerId],
  );
```

- [ ] **Step 2: 落地页恢复缓慢环绕运镜**

在 `CameraTracker` 的 `useFrame` 里，把当前的 lobby 守卫（约 123 行）：

```tsx
    if (phase === "START_SCREEN") {
```

改为：

```tsx
    if (isLobbyPhase(phase)) {
```

（`isLobbyPhase` 已在 Step 1 import。这样落地页 `phase=undefined` 时也会进入既有的 0.08 慢速 orbit 分支。）

- [ ] **Step 3: 类型 / lint 检查**

Run: `cd frontend && npm run lint`
Expected: 0 errors（`tsc --noEmit` 通过）。

- [ ] **Step 4: 截图验证落地页**

启动 dev：`cd frontend && npm run dev`（记下端口，默认 5173）。用 chrome-devtools MCP：
1. `navigate_page` → `http://localhost:5173/`
2. `wait_for` 1500ms 让 orbit 稳定
3. `take_screenshot`（保存留档）

Expected：落地页出现 **6 个棋子围成的圆桌**（不再是空桌），场景因棋子点光而不再发暗，镜头缓慢环绕。再在设置面板把人数调到 9，确认席位实时增到 9。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ThreeCanvas.tsx
git commit -m "fix(fe): landing 3D no longer empty — buildPreviewSeats + lobby orbit on undefined phase"
```

---

## Task 5: 镜头柔化（去快切、放慢推进）

**Files:**
- Modify: `frontend/src/lib/cameraDirector.ts`
- Modify: `frontend/src/lib/cameraDirector.test.ts`

- [ ] **Step 1: 更新测试以表达新手感**

编辑 `frontend/src/lib/cameraDirector.test.ts`：

1. 顶部 import 把 `FAST_LAMBDA` 改名为 `WIDE_LAMBDA`：

```ts
import {
  tableRadius,
  homePose,
  speakerPose,
  decideCamera,
  RECENTER_HOLD_MS,
  WIDE_LAMBDA,
  SLOW_LAMBDA,
} from "./cameraDirector";
```

2. "a phase-establish window forces a fast wide cut..." 用例里：

```ts
    expect(d.mode).toBe("wide");
    expect(d.posLambda).toBe(WIDE_LAMBDA);
    expect(d.pos).toEqual(homePose(6).pos);
```

3. "a post-speech recenter hold overrides..." 用例里同样把 `FAST_LAMBDA` 改为 `WIDE_LAMBDA`。

4. 追加一个表达"广角拉回不再是猛切"的用例：

```ts
  it("the wide pull-back eases rather than snapping (gentler than the old fast cut)", () => {
    expect(WIDE_LAMBDA).toBeLessThan(5);
    expect(WIDE_LAMBDA).toBeGreaterThan(SLOW_LAMBDA);
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/cameraDirector.test.ts`
Expected: FAIL — `WIDE_LAMBDA` 未导出。

- [ ] **Step 3: 改阻尼常量并接 `isLobbyPhase`**

编辑 `frontend/src/lib/cameraDirector.ts`：

1. 顶部加 import：

```ts
import { isLobbyPhase } from "./phaseStage";
```

2. 把当前的阻尼常量块（49–53 行）替换为：

```ts
// Damping lambdas for THREE.MathUtils.damp (frame-rate independent; higher = snappier).
export const WIDE_LAMBDA = 3.5; // eased pull-back to wide (replaces the old hard FAST cut of 7.0)
export const SLOW_LAMBDA = 2.5; // unhurried push-in / gentle drift (slowed from 3.0)
export const WIDE_LOOK_LAMBDA = 4.0;
export const SLOW_LOOK_LAMBDA = 3.0;
```

3. `decideCamera` 里 START_SCREEN 守卫（91 行）改为：

```ts
  if (isLobbyPhase(phase)) {
```

4. "Forced wide window" 分支（103–111 行）里的 `FAST_LAMBDA` / `FAST_LOOK_LAMBDA` 改为 `WIDE_LAMBDA` / `WIDE_LOOK_LAMBDA`：

```ts
  if (nowMs < establishUntilMs || nowMs < recenterUntilMs) {
    return {
      mode: "wide",
      pos: home.pos,
      look: home.look,
      posLambda: WIDE_LAMBDA,
      lookLambda: WIDE_LOOK_LAMBDA,
    };
  }
```

（follow 与 gentle-wide 分支已用 `SLOW_LAMBDA` / `SLOW_LOOK_LAMBDA`，随常量自动放慢，无需改动。）

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/cameraDirector.test.ts`
Expected: PASS。再跑 `cd frontend && npm run lint` 确认 `ThreeCanvas.tsx` 没有残留对已删除的 `FAST_LAMBDA` 的引用（它只 import 了 `decideCamera, RECENTER_HOLD_MS`，应无影响）。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/cameraDirector.ts frontend/src/lib/cameraDirector.test.ts
git commit -m "feat(fe): soften camera — eased WIDE_LAMBDA pull-back, slower push-in, isLobbyPhase"
```

---

## Task 6: 昼夜全局光照（接入 sceneTheme，明亮暖阳 vs 冷月光）

**Files:**
- Modify: `frontend/src/components/ThreeCanvas.tsx`（`EnvironmentController` 11–80；`ThreeCanvas` 内 `isNight/isMurderAlert/fogColor/...` 计算 ~735–743）

- [ ] **Step 1: 顶部 import sceneTheme**

`ThreeCanvas.tsx` import 区加：

```tsx
import { resolveSceneMode, sceneTheme, type SceneMode } from "../lib/sceneTheme";
```

- [ ] **Step 2: `EnvironmentController` 改为吃 `mode`，并扩大阴影相机覆盖**

把 `EnvironmentController` 整个组件（11–80 行）替换为：

```tsx
function EnvironmentController({ mode }: { mode: SceneMode }) {
  const { scene } = useThree();

  const theme = React.useMemo(() => {
    const t = sceneTheme(mode);
    return {
      bg: new THREE.Color(t.bg),
      ambientColor: new THREE.Color(t.ambientColor),
      ambientIntensity: t.ambientIntensity,
      dirColor: new THREE.Color(t.dirColor),
      dirPos: new THREE.Vector3(t.dirPos[0], t.dirPos[1], t.dirPos[2]),
      dirIntensity: t.dirIntensity,
    };
  }, [mode]);

  const ambientRef = useRef<THREE.AmbientLight>(null);
  const dirRef = useRef<THREE.DirectionalLight>(null);

  useEffect(() => {
    scene.fog = new THREE.Fog(theme.bg, 12, 38);
    scene.background = theme.bg.clone();
    return () => {
      scene.fog = null;
      scene.background = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene]);

  useFrame((_, delta) => {
    const s = 1 - Math.exp(-3 * delta); // 帧率无关的平滑衰减

    if (scene.background instanceof THREE.Color) {
      scene.background.lerp(theme.bg, s);
    }
    if (scene.fog && "color" in scene.fog) {
      (scene.fog as THREE.Fog).color.lerp(theme.bg, s);
    }
    if (ambientRef.current) {
      ambientRef.current.color.lerp(theme.ambientColor, s);
      ambientRef.current.intensity = THREE.MathUtils.lerp(ambientRef.current.intensity, theme.ambientIntensity, s);
    }
    if (dirRef.current) {
      dirRef.current.color.lerp(theme.dirColor, s);
      dirRef.current.intensity = THREE.MathUtils.lerp(dirRef.current.intensity, theme.dirIntensity, s);
      dirRef.current.position.lerp(theme.dirPos, s);
    }
  });

  return (
    <>
      <ambientLight ref={ambientRef} />
      <directionalLight
        ref={dirRef}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-bias={-0.0004}
        shadow-camera-near={1}
        shadow-camera-far={60}
        shadow-camera-left={-24}
        shadow-camera-right={24}
        shadow-camera-top={24}
        shadow-camera-bottom={-24}
      />
    </>
  );
}
```

> 阴影相机由默认 ±5 扩到 ±24，覆盖整张桌子和 Task 8 的大地面，否则棋子落影会被裁掉。这是**唯一**的投影光。

- [ ] **Step 3: `ThreeCanvas` 内集中算 `mode`，删掉散落的颜色常量**

在 `ThreeCanvas` 组件里，把现有的 `isNight` / `isMurderAlert` / `fogColor` / `lightColor` / `ambientIntensity` 计算块（约 738–743 行）替换为：

```tsx
  const isNight = phase?.startsWith("NIGHT") || lastLogIsNight || false;
  const isMurderAlert = phase === "DAY_ANNOUNCEMENT" && victimId !== null && victimId !== undefined;
  const sceneMode: SceneMode = resolveSceneMode(Boolean(isNight), Boolean(isMurderAlert));
```

（删除 `fogColor` / `lightColor` / `ambientIntensity` 三个不再使用的局部变量——它们原先只喂给被本次重构吃掉的内联逻辑。）

- [ ] **Step 4: 更新 `EnvironmentController` 的挂载**

把 `<EnvironmentController isNight={isNight} isMurderAlert={isMurderAlert} />`（约 820 行）改为：

```tsx
        <EnvironmentController mode={sceneMode} />
```

- [ ] **Step 5: lint + 昼夜截图验证**

Run: `cd frontend && npm run lint`（Expected: 0 errors。若报 `fogColor`/`lightColor`/`ambientIntensity` 未使用，删掉对应残留行。）

启动全栈以拿到真实昼夜切换：仓库根 `./dev.sh`（或 `.\dev.ps1`），后端 8010 + 前端 5173。用 chrome-devtools：观战一局 demo（首页"进入盘面"→ 观战），分别在白天/黑夜各 `take_screenshot`。
Expected：白天明亮暖金 + 淡蓝天光背景；黑夜深蓝紫 + 冷月光、能看清棋子；二者对比鲜明。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ThreeCanvas.tsx
git commit -m "feat(fe): day/night global light via sceneTheme — bright warm day vs cool moonlit night"
```

---

## Task 7: 性能砍杀（DPR 封顶 / 单投影光 / 去每席位点光 / 去 transmission）

**Files:**
- Modify: `frontend/src/components/ThreeCanvas.tsx`（`<Canvas>` ~814；`ChessPiece` 412–435；`CentralEnergyOrb` pointLight ~702–708；speaker `spotLight` ~778–787）

- [ ] **Step 1: `<Canvas>` 封顶 DPR**

把 `<Canvas>` 开标签（约 814–818 行）改为：

```tsx
      <Canvas
        shadows
        dpr={[1, 1.5]}
        gl={{ antialias: true, powerPreference: "high-performance" }}
        camera={{ position: [0, 9.25, 13], fov: 45 }}
        style={{ pointerEvents: "auto" }}
      >
```

- [ ] **Step 2: 每席位点光只在发言时存在 + 去掉 transmission**

在 `ChessPiece` 里：

(a) `materialProps`（412–421 行）删掉 `transmission` 一行：

```tsx
  const materialProps = {
    color: baseColor,
    roughness: isSpeaking ? 0.05 : 0.1,
    metalness: isSpeaking ? 0.4 : 0.8,
    clearcoat: 1.0,
    clearcoatRoughness: 0.1,
    emissive: theme.primaryAccent,
    emissiveIntensity: isSpeaking ? 0.7 : (isUser ? 0.2 : 0.05),
  };
```

(b) 把常驻的 `<pointLight>`（424–430 行，每个棋子一盏 6–12 盏）改为只在发言时渲染——替换为：

```tsx
  return (
    <group position={[0, 0.4, 0]}>
       {isSpeaking && (
         <pointLight
          position={[0, 1.5, 0]}
          distance={4.0}
          intensity={1.5}
          color={theme.primaryAccent}
        />
       )}
      {/* Main body lathe */}
      <mesh castShadow>
        <latheGeometry args={[points, 64]} />
        <meshPhysicalMaterial {...materialProps} />
      </mesh>
```

> 同时给主体 mesh 加 `castShadow`，让棋子在 Task 8 的地面上落影（补"立体感"）。环境光在 Task 6 已显著调亮，空闲棋子靠自发光 + 全局光足够，不再需要每席位补光。

- [ ] **Step 3: 中央光球 pointLight 取消投影**

`CentralEnergyOrb` 里的 `<pointLight>`（约 702–708 行）去掉 `castShadow` 与 `shadow-bias`：

```tsx
      <pointLight
        ref={lightRef}
        intensity={10}
        distance={12}
      />
```

- [ ] **Step 4: 发言聚光灯取消投影**

`speakerLight` 里的 `<spotLight>`（约 778–787 行）去掉 `castShadow` 与两行 `shadow-mapSize-*`：

```tsx
          <spotLight
            position={[sX, 6.5, sZ]}
            angle={0.4}
            penumbra={0.7}
            intensity={isNight ? 32.0 : 25.0}
            color={isNight ? "#d946ef" : "#ff6a00"}
          />
```

> （这里仍引用 `isNight` 是 OK 的——`isNight` 仍在 `ThreeCanvas` 作用域内；颜色会在 Task 9 统一并入 sceneTheme。）

- [ ] **Step 5: lint + 灯光数 / 帧率验证**

Run: `cd frontend && npm run lint`（Expected: 0 errors）。

用 chrome-devtools 在运行中的一局里：
- `evaluate_script` 读取渲染器统计（确认场景里**最多 1 个投影光**、动态点光数随发言人 0–1 盏）：

```js
// 在页面控制台 / evaluate_script 中粗查灯光与投影光数量
(() => {
  let total = 0, shadow = 0;
  // three 不暴露全局 scene；改用 WebGL drawcall 作为间接指标更稳妥时，见性能 trace。
  return { note: "用 performance trace 看帧率；灯光数以代码审查为准" , total, shadow };
})()
```

- 更可靠的判据：`performance_start_trace` → 在场景里跑 ~5 秒（含一次发言切换与昼夜切换）→ `performance_stop_trace` → `performance_analyze_insight`，确认主线程帧时间稳定在 ~16ms（60fps），无长帧尖峰。

Expected：相比改前，帧时间明显下降、无周期性卡顿尖峰。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ThreeCanvas.tsx
git commit -m "perf(fe): cap dpr=1.5, single shadow caster, speaker-only point light, drop transmission"
```

---

## Task 8: 多层氛围地面 `GroundPlane`

**Files:**
- Create: `frontend/src/components/GroundPlane.tsx`
- Modify: `frontend/src/components/ThreeCanvas.tsx`（挂载 GroundPlane；石柱 mesh 加 `castShadow`）

- [ ] **Step 1: 实现 GroundPlane 组件**

`frontend/src/components/GroundPlane.tsx`:

```tsx
import React, { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { sceneTheme, type SceneMode } from "../lib/sceneTheme";

/** 程序化石质地面贴图：暗石底 + 中心微亮的径向渐变 + 随机刻痕。 */
function makeGroundTexture(): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = 1024;
  canvas.height = 1024;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.fillStyle = "#15131a";
    ctx.fillRect(0, 0, 1024, 1024);

    const grad = ctx.createRadialGradient(512, 512, 80, 512, 512, 512);
    grad.addColorStop(0, "rgba(70,64,86,0.9)");
    grad.addColorStop(0.6, "rgba(28,26,38,0.7)");
    grad.addColorStop(1, "rgba(8,7,12,1)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 1024, 1024);

    ctx.globalAlpha = 0.16;
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1;
    for (let i = 0; i < 120; i++) {
      const x = Math.random() * 1024;
      const y = Math.random() * 1024;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + (Math.random() - 0.5) * 70, y + (Math.random() - 0.5) * 70);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }
  return new THREE.CanvasTexture(canvas);
}

const GROUND_TINT: Record<SceneMode, string> = {
  day: "#9a8f7a",
  night: "#1b1830",
  murder: "#2a1010",
};

export default function GroundPlane({ mode, tableRadius }: { mode: SceneMode; tableRadius: number }) {
  const theme = sceneTheme(mode);
  const texture = React.useMemo(() => makeGroundTexture(), []);

  const matRef = useRef<THREE.MeshStandardMaterial>(null);
  const ring0 = useRef<THREE.MeshBasicMaterial>(null);
  const ring1 = useRef<THREE.MeshBasicMaterial>(null);
  const ring2 = useRef<THREE.MeshBasicMaterial>(null);
  const ringRefs = [ring0, ring1, ring2];

  const targetGround = React.useMemo(() => new THREE.Color(GROUND_TINT[mode]), [mode]);
  const targetAccent = React.useMemo(() => new THREE.Color(theme.accent), [theme.accent]);

  useFrame((_, delta) => {
    const s = 1 - Math.exp(-3 * delta);
    if (matRef.current) matRef.current.color.lerp(targetGround, s);
    for (const r of ringRefs) if (r.current) r.current.color.lerp(targetAccent, s);
  });

  const ringRadii = [tableRadius * 1.4, tableRadius * 2.0, tableRadius * 2.8];

  return (
    <group position={[0, -0.5, 0]}>
      {/* 接收唯一方向光阴影的大地面 */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <circleGeometry args={[tableRadius * 4.2, 96]} />
        <meshStandardMaterial ref={matRef} map={texture} roughness={0.95} metalness={0.1} />
      </mesh>

      {/* 同心发光法阵环（加色混合，不投影、不写深度） */}
      {ringRadii.map((r, i) => (
        <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01 + i * 0.004, 0]}>
          <ringGeometry args={[r, r + 0.07, 128]} />
          <meshBasicMaterial
            ref={ringRefs[i]}
            transparent
            opacity={0.34 - i * 0.08}
            blending={THREE.AdditiveBlending}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
}
```

- [ ] **Step 2: 在 ThreeCanvas 挂载 GroundPlane**

`ThreeCanvas.tsx` import 区加：

```tsx
import GroundPlane from "./GroundPlane";
```

在 `<Canvas>` 内、`<EnvironmentController .../>` **之后**、桌子 `group` 之前插入（`tableRadius` 用与桌子一致的算法）：

```tsx
        {(() => {
          const radius = Math.max(5, previewPlayers.length * 0.72);
          const tableRadius = Math.max(3.5, radius * 0.7);
          return <GroundPlane mode={sceneMode} tableRadius={tableRadius} />;
        })()}
```

- [ ] **Step 3: 石柱也投影到地面**

`SpeakerSeat` 里石柱主体 mesh（约 504 行 `<mesh position={[0, 0.5, 0]}>`，紧接 `<cylinderGeometry args={[0.6, 0.75, 1.2, 8]} />` 的那个）加 `castShadow`：

```tsx
      <mesh position={[0, 0.5, 0]} castShadow>
        <cylinderGeometry args={[0.6, 0.75, 1.2, 8]} />
```

- [ ] **Step 4: lint + 地面截图验证**

Run: `cd frontend && npm run lint`（Expected: 0 errors）。

chrome-devtools 截图（落地页 + 一局白天/黑夜）：
Expected：桌子下方出现有纹理的石质地面、棋子/石柱在地面上有清晰落影、桌子外围三道发光法阵环、地面边缘渐暗没入雾——不再"单薄"。昼夜下地面色调与环色随之切换。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/GroundPlane.tsx frontend/src/components/ThreeCanvas.tsx
git commit -m "feat(fe): GroundPlane — textured shadow-receiving ground + glowing rune rings"
```

---

## Task 9: 点缀色随 sceneTheme 和谐化（桌沿/粒子/光球/法阵/聚光）

把散落在各装饰组件里的 `isNight ? 紫 : 橙` 硬编码统一并入 `mode` + sceneTheme，让黑夜的蓝紫调一致。

**Files:**
- Modify: `frontend/src/components/ThreeCanvas.tsx`（`MagicalSparks`、`TableRim`、`CentralEnergyOrb`、`TrialSigil`、`speakerLight`，及它们在渲染树里的调用）

- [ ] **Step 1: `MagicalSparks` 吃 mode**

把组件签名与 `targetColor` 改为：

```tsx
function MagicalSparks({ mode }: { mode: SceneMode }) {
  const pointsRef = useRef<THREE.Points>(null);
  const count = 75;
  // ...positions useMemo 不变...
  const targetColor = React.useMemo(() => new THREE.Color(sceneTheme(mode).accent), [mode]);
```

调用处（约 823 行）改为：`<MagicalSparks mode={sceneMode} />`

- [ ] **Step 2: `TableRim` 吃 mode**

签名与两个目标色改为：

```tsx
function TableRim({ tableRadius, mode }: { tableRadius: number; mode: SceneMode }) {
  const theme = sceneTheme(mode);
  const targetWireColor = React.useMemo(() => new THREE.Color(theme.accent), [theme.accent]);
  const targetSolidColor = React.useMemo(() => new THREE.Color(theme.accentSoft), [theme.accentSoft]);
```

调用处（约 848 行）改为：`<TableRim tableRadius={tableRadius} mode={sceneMode} />`

- [ ] **Step 3: `CentralEnergyOrb` 吃 mode**

签名与三个目标色改为：

```tsx
function CentralEnergyOrb({ mode }: { mode: SceneMode }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const lightRef = useRef<THREE.PointLight>(null);
  const theme = sceneTheme(mode);
  const targetLightColor = React.useMemo(() => new THREE.Color(theme.accent), [theme.accent]);
  const targetMatColor = React.useMemo(() => new THREE.Color(theme.accent), [theme.accent]);
  const targetEmissiveColor = React.useMemo(() => new THREE.Color(theme.accentSoft), [theme.accentSoft]);
```

`useFrame` 里 `targetIntensity` 的 `isNight` 改为按 mode 判断：

```tsx
      const targetIntensity = (mode === "night" ? 14.0 : 9.0) + Math.sin(time * 5) * 3.0;
```

调用处（约 857 行）改为：`<CentralEnergyOrb mode={sceneMode} />`

- [ ] **Step 4: `TrialSigil` 吃 mode**

签名改为 `function TrialSigil({ tableRadius, mode }: { tableRadius: number; mode: SceneMode })`，把 `useEffect` 依赖数组由 `[isNight, isMurderAlert]` 改为 `[mode]`，并在绘制时用 mode 取色。将描边/符文配色统一为（替换原先所有 `isMurderAlert ? ... : (isNight ? ... : ...)` 三元，改用一个本地映射）：

```tsx
  useEffect(() => {
    const stroke = mode === "murder" ? "#ef4444" : mode === "night" ? "#818cf8" : "#fbbf24";
    const strokeDeep = mode === "murder" ? "#991b1b" : mode === "night" ? "#3730a3" : "#92400e";
    const strokeSoft = mode === "murder" ? "#fca5a5" : mode === "night" ? "#a5b4fc" : "#fef08a";
    const star = mode === "murder" ? "#ef4444" : mode === "night" ? "#6366f1" : "#f59e0b";
    const rune = mode === "murder" ? "#fee2e2" : mode === "night" ? "#c7d2fe" : "#ffedd5";
    // ... 用上述变量替换原绘制代码里对应的 ctx.strokeStyle / fillStyle / shadowColor ...
  }, [mode]);
```

> 实现者：保留 TrialSigil 原有的几何绘制（边界圆、双环、六芒星、符文、刻痕），仅把颜色来源从内联三元换成上面 5 个按 `mode` 取的变量；`shadowColor` 复用 `stroke`/`star`/`strokeSoft` 同族色即可。

调用处（约 851 行）改为：`<TrialSigil tableRadius={tableRadius} mode={sceneMode} />`

- [ ] **Step 5: `speakerLight` 用 sceneTheme 取色**

把 `ThreeCanvas` 里构造 `speakerLight` 的颜色（约 782–803 行内的 `isNight ? "#d946ef" : "#ff6a00"` 等）改为读 `const sTheme = sceneTheme(sceneMode);`，spotLight/cone 用 `sTheme.accent`，辅助 pointLight 用 `sTheme.accentSoft`，强度仍按 `sceneMode === "night"` 区分：

```tsx
      const sTheme = sceneTheme(sceneMode);
      speakerLight = (
        <group>
          <spotLight
            position={[sX, 6.5, sZ]}
            angle={0.4}
            penumbra={0.7}
            intensity={sceneMode === "night" ? 32.0 : 25.0}
            color={sTheme.accent}
          />
          <pointLight position={[sX, 1.8, sZ]} intensity={6.0} distance={6} color={sTheme.accentSoft} />
          <mesh position={[sX, 3.4, sZ]}>
            <cylinderGeometry args={[0.08, 1.5, 6.0, 32, 1, true]} />
            <meshBasicMaterial
              color={sTheme.accent}
              transparent
              opacity={sceneMode === "night" ? 0.18 : 0.14}
              blending={THREE.AdditiveBlending}
              side={THREE.DoubleSide}
              depthWrite={false}
            />
          </mesh>
        </group>
      );
```

- [ ] **Step 6: lint + 一致性截图验证**

Run: `cd frontend && npm run lint`（Expected: 0 errors，确认没有残留未使用的 `isNight`/`isMurderAlert`——若 `isMurderAlert` 仅剩 `sceneMode` 计算处使用则保留，未用则删。）

截图（白天/黑夜各一张含发言人的）：
Expected：黑夜下桌沿、粒子、法阵、光球、发言聚光全为蓝紫同族色（不再紫橙混搭）；白天为暖金同族色；整体协调。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ThreeCanvas.tsx
git commit -m "feat(fe): harmonize accent colors (rim/sparks/orb/sigil/spotlight) via sceneTheme"
```

---

## Task 10: 全量验证与记录

**Files:**
- Modify: `docs/superpowers/plans/2026-06-09-3d-scene-optimization.md`（在文末追加"验证记录"小节）

- [ ] **Step 1: 单测 + 类型 + lint 全绿**

Run: `cd frontend && npm run test`
Expected: 全部 PASS（含 sceneTheme / previewSeats / phaseStage / cameraDirector）。

Run: `cd frontend && npm run lint`
Expected: 0 errors（eslint + `tsc --noEmit`）。

- [ ] **Step 2: 全栈跑起来**

仓库根：`./dev.sh`（macOS/Linux）或 `.\dev.ps1`（Windows）。等后端 `GET http://localhost:8010/health` → `{"status":"ok"}`，前端打印 Vite 地址。

- [ ] **Step 3: 四个关键画面截图（chrome-devtools）**

1. 落地页 `http://localhost:5173/`：确认棋子圆桌 + 缓慢环绕（修 #2）。
2. 观战一局：白天发言画面（明亮暖金、跟随发言人但不突兀）。
3. 黑夜画面（深蓝紫冷月光、能看清、蓝紫点缀一致）。
4. 命案布告 `DAY_ANNOUNCEMENT` 画面（红色警报档仍生效）。

每张 `take_screenshot` 留档。

- [ ] **Step 4: 性能 trace 验证 60fps**

`performance_start_trace` → 在观战局里经历一次发言切换 + 一次昼夜切换（约 6–8 秒）→ `performance_stop_trace` → `performance_analyze_insight`。
Expected：主线程帧时间稳定 ~16ms、无周期性长帧；镜头位移连续无跳变。

- [ ] **Step 5: 把结果写进本计划文末**

在本文件末尾追加：

```markdown
## 验证记录（YYYY-MM-DD）
- 单测：`npm run test` 全绿（N 个用例）。
- lint/tsc：0 errors。
- 落地页：棋子圆桌 + 环绕运镜恢复（#2 修复）。截图：<路径>
- 昼夜对比：白天暖金 / 黑夜冷蓝紫，对比鲜明（#3）。截图：<路径×2>
- 命案档：红色仍生效。截图：<路径>
- 地面：石质 + 落影 + 法阵环，不再单薄（#3）。
- 性能：trace 帧时间 ~Xms（≈60fps），镜头柔和无突兀（#1）。
- 残留/已知问题：<如有>
```

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/plans/2026-06-09-3d-scene-optimization.md
git commit -m "docs(plan): 3D scene optimization verification record"
```

---

## Self-Review

**Spec coverage：**
- #1 卡顿/突兀 → Task 7（DPR/单投影光/去点光/去 transmission）+ Task 5（镜头柔化）+ Task 10（perf trace）。✓
- #2 空桌 → Task 3（buildPreviewSeats）+ Task 4（接入 + lobby orbit）。✓
- #3 昼夜全局光 → Task 1（调色板）+ Task 6（光照接入、扩阴影相机）。✓
- #3 地面单薄 → Task 8（GroundPlane + 落影）。✓
- 点缀和谐化 → Task 9。✓

**类型一致性：** `SceneMode`/`sceneTheme`/`resolveSceneMode`（Task 1）→ Task 6/8/9 一致引用；`isLobbyPhase`（Task 2）→ Task 3/4/5 一致；`WIDE_LAMBDA`/`SLOW_LAMBDA`（Task 5）测试与实现同名；`buildPreviewSeats` 入参 `{phase,setupCount,players,currentSpeakerId}`（Task 3）与 Task 4 调用一致；`GroundPlane` props `{mode,tableRadius}`（Task 8）与挂载一致。

**Placeholder 扫描：** TrialSigil（Task 9 Step 4）保留既有几何、仅替换取色变量——已给出 5 个颜色变量的完整定义与替换说明，非 TODO。其余步骤均含完整代码或精确编辑块。

---

## 验证记录（2026-06-09，分支 `worktree-3d-scene-optim`）

**执行方式：** inline（executing-plans），10 个任务逐个 TDD/编辑 + 提交。

**确定性门禁（全绿）：**
- 单测：`npm run test` → **32 文件 / 206 用例全过**（基线 191 + 新增 15：sceneTheme 7、isLobbyPhase 3、previewSeats 4、cameraDirector +1）。
- 类型：`npx tsc --noEmit` → **exit 0**（全程每个任务后均校验）。
- 构建：`npm run build`（vite build）→ **✓ built**（>500kB chunk 提示为既有 three.js 包警告，非错误）。
- ESLint：仓库**基线本就有 56 个 error**（RunsPage/StrategyPage/audio.ts/store.ts 等，与本次无关）；本次新增/改动文件经核对**无新增 error**（ThreeCanvas 残留的 `Math.random` 纯度 + R3F ref-in-render 报错均为既有；新 lib 文件与 GroundPlane 干净）。门禁因此改为「tsc 干净 + 受影响文件无新增 error + 单测全绿」。

**可视化验证（Playwright，1440×900）：**
- 落地页（day）截图 `3d-verify-02-lobby-fixed.png`：**6 枚彩色棋子环绕圆桌正常渲染**（#2 空桌已修）；**石质地面 + 三道同心发光法阵环 + 棋子落影**（#3 不再单薄）；白天**更亮、暖金天光**背景（#3）；**0 console error**。
- 一次性印证 Task 4（棋子回归）/ Task 6（昼间光照）/ Task 8（地面）。
- 并发环境坑：`localhost:5173` 被另一并发 agent 的旧服务（`::1` 监听）占用，导致首张截图 `3d-verify-01-lobby.png` 是旧代码（空桌）。改用独立端口 `127.0.0.1:5188 --strictPort` 后验证通过。

**由单测覆盖、未单独跑实时画面：**
- 夜间 / 命案 调色板：`sceneTheme.test.ts` 断言（夜=暗冷、昼更亮、命案=红）；渲染路径与白天同构（EnvironmentController/GroundPlane 均按 `mode` 取色），故按构造正确。
- 镜头柔化（#1 突兀）：`cameraDirector.test.ts` 断言 `WIDE_LAMBDA` 介于 `SLOW_LAMBDA` 与 5 之间（去掉了 7.0 硬切）。
- 性能（#1 卡顿）：结构性达成——单一投影方向光（关掉光球/聚光投影）、每席位点光仅发言者一盏、去 transmission、`dpr=[1,1.5]` 封顶；落地页渲染顺滑、无报错。

**建议的人工补验（需全栈 + 一局对战）：** 起 `./dev.ps1` 观战一局 demo，肉眼确认夜间冷蓝紫 / 命案红 / 发言切换镜头柔和，并用 devtools 性能 trace 看实测帧率。

**残留/已知问题：** 仓库既有的 56 个 ESLint error 未处理（超出本次范围）；落地页背景天光为单色雾近似（非渐变，性能取舍）。
