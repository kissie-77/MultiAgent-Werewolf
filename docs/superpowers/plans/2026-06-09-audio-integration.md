# 音效集成实现计划（实况对局）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有 35 个 SFX 接入实况对局（god 观战 + 座位人机），通过 `SoundManager` 单例统一出声，带 burst 抑制、event_id 去重、座位防泄漏、缺文件合成兜底；并加静音/音量控制。

**Architecture:** 模块级 `SoundManager` 单例（AudioContext + sfxBus/bgmBus + 缓冲缓存 + 兜底）；纯函数 `soundMap`（id↔文件、事件/转场映射、burst/dedup 逻辑）；派发点 = `store.onmessage`（技能+事件音）、`GameAudioBridge`（昼夜转场）、座位组件（座位/UI 音）。BGM 不做，bgmBus 仅占位。

**Tech Stack:** React 19 + Zustand 5 + TypeScript（strict）+ Web Audio API；Vitest（node env）。

> **关联 spec:** `docs/superpowers/specs/2026-06-09-audio-integration-design.md`
>
> **相对 spec 的一处落地细化（请审）：** 技能**声音**从后端**技能结果事件**派发（`effectTypeForEvent` → `effectTypeSfx`），而非从 `activeCast` 取——原因：① 区分女巫毒/救（role_acting 取不到）；② 避免 `role_acting` 与结果事件**双响**；③ 结果事件本身按可见性下发，座位天然不泄漏。**视觉**塔罗动画（activeCast/CastSkillOverlay）保持不变。结果事件紧随 role_acting，音画近乎同步。`vote_cast`（逐人投票）**不**出技能音以免刷屏；改由 `vote_result`→`event_vote_tally` 出声，玩家自己的票由 submit 路径出 `skill_vote`。

---

## File Structure

**新增**
- `frontend/src/audio/soundMap.ts` — 纯函数：`effectTypeSfx`、`eventSfx`、`stageSfx`、`sfxPath`、`ALL_SFX_IDS`、`createBurstGate`、`createEventDedup`
- `frontend/src/audio/soundMap.test.ts`
- `frontend/src/audio/soundManager.ts` — 命令式单例引擎
- `frontend/src/audio/soundManager.test.ts`
- `frontend/src/components/GameAudioBridge.tsx` — 订阅 stageFx 播昼夜转场 + 首次手势解锁 + 同步音量/静音
- 资产：`<repo>/../audio/*.mp3` → `frontend/public/audio/*.mp3`

**改动**
- `frontend/src/types.ts` — `EffectType` 7→15
- `frontend/src/lib/castMap.ts` — `effectTypeForRole` 扩档 + 新增 `effectTypeForEvent`
- `frontend/src/lib/castMap.test.ts` — 加测
- `frontend/src/store.ts` — audio slice + 持久化；onmessage 派发技能/事件音；ingestSeatEvent your_turn/timeout；submitHumanInput submit/own-skill
- `frontend/src/store.humanInput.test.ts` — 加测座位音
- `frontend/src/components/CastSkillOverlay.tsx` — 移除 6 个合成音调用（视觉专用）
- `frontend/src/pages/GameApp.tsx` — 挂 `<GameAudioBridge/>`
- `frontend/src/components/TopHeader.tsx` — 静音键 + 音量滑块
- `frontend/src/components/InsightDock.tsx` — 展开/收起 panel 音
- `frontend/src/components/SeatCommandDock.tsx` — tick + 按钮 click

---

## Task 1: 资产归位到 public/audio/

**Files:**
- 移动：`D:\AI_werewolf\werewolf_6_8\audio\*.mp3` → `frontend/public/audio/*.mp3`

- [ ] **Step 1: 建目录并移动**

Run（仓库根目录）:
```bash
mkdir -p frontend/public/audio
mv ../audio/*.mp3 frontend/public/audio/
```

- [ ] **Step 2: 校验 36 个文件就位**

Run:
```bash
ls -1 frontend/public/audio | wc -l   # 期望 36
ls -1 frontend/public/audio | grep -E '^(skill|event|ui)_' | wc -l  # 期望 36
```
Expected: 36 / 36（含 `event_victory_good_alt.mp3` 备选）。

- [ ] **Step 3: 提交资产**

```bash
git add frontend/public/audio
git commit -m "chore(audio): relocate generated SFX into frontend/public/audio"
```

---

## Task 2: 纯函数映射 `soundMap.ts`

**Files:**
- Create: `frontend/src/audio/soundMap.ts`
- Test: `frontend/src/audio/soundMap.test.ts`

- [ ] **Step 1: 写失败测试**

Create `frontend/src/audio/soundMap.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import {
  effectTypeSfx, eventSfx, stageSfx, sfxPath,
  createBurstGate, createEventDedup,
} from "./soundMap";

describe("effectTypeSfx", () => {
  it("covers new skill effects", () => {
    expect(effectTypeSfx.poison).toBe("skill_poison");
    expect(effectTypeSfx.charm).toBe("skill_charm");
    expect(effectTypeSfx.rally).toBe("skill_vote");
  });
});

describe("eventSfx", () => {
  it("maps public events", () => {
    expect(eventSfx({ event_type: "player_died" })).toBe("event_death_reveal");
    expect(eventSfx({ event_type: "player_eliminated" })).toBe("event_execution");
    expect(eventSfx({ event_type: "vote_result" })).toBe("event_vote_tally");
    expect(eventSfx({ event_type: "sheriff_elected" })).toBe("event_sheriff_elected");
  });
  it("splits game_ended by winner camp", () => {
    expect(eventSfx({ event_type: "game_ended", data: { winner_camp: "villager" } })).toBe("event_victory_good");
    expect(eventSfx({ event_type: "game_ended", data: { winner_camp: "werewolf" } })).toBe("event_victory_evil");
  });
  it("returns null for unmapped", () => {
    expect(eventSfx({ event_type: "actor_thinking" })).toBeNull();
  });
});

describe("stageSfx", () => {
  it("maps night/day only", () => {
    expect(stageSfx("night")).toBe("event_nightfall");
    expect(stageSfx("day")).toBe("event_dawn");
    expect(stageSfx("lobby")).toBeNull();
    expect(stageSfx("over")).toBeNull();
  });
});

describe("sfxPath", () => {
  it("builds public path", () => {
    expect(sfxPath("skill_bite")).toBe("/audio/skill_bite.mp3");
  });
});

describe("createBurstGate", () => {
  it("allows up to max then suppresses within window", () => {
    const g = createBurstGate(700, 3);
    expect(g.allow(0)).toBe(true);
    expect(g.allow(10)).toBe(true);
    expect(g.allow(20)).toBe(true);
    expect(g.allow(30)).toBe(false);
  });
  it("recovers after window passes", () => {
    const g = createBurstGate(700, 3);
    g.allow(0); g.allow(10); g.allow(20);
    expect(g.allow(800)).toBe(true);
  });
});

describe("createEventDedup", () => {
  it("skips already-seen monotonic ids, passes new", () => {
    const d = createEventDedup();
    expect(d.seen(5)).toBe(false);
    expect(d.seen(5)).toBe(true);   // duplicate
    expect(d.seen(4)).toBe(true);   // older (re-send)
    expect(d.seen(6)).toBe(false);  // newer
  });
  it("never dedups when id is undefined", () => {
    const d = createEventDedup();
    expect(d.seen(undefined)).toBe(false);
    expect(d.seen(undefined)).toBe(false);
  });
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npx vitest run src/audio/soundMap.test.ts`
Expected: FAIL（Cannot find module './soundMap'）

- [ ] **Step 3: 实现 `soundMap.ts`**

Create `frontend/src/audio/soundMap.ts`:
```ts
import type { EffectType } from "../types";
import type { CoarseStage } from "../lib/phaseStage";

export type SfxId = string;

/** 技能 effectType → sfx 文件 id。 */
export const effectTypeSfx: Record<EffectType, SfxId> = {
  bite: "skill_bite",
  inspect: "skill_inspect",
  heal: "skill_heal",
  poison: "skill_poison",
  shoot: "skill_shoot",
  vote: "skill_vote",
  rally: "skill_vote",
  guard: "skill_guard",
  charm: "skill_charm",
  mark: "skill_mark",
  link: "skill_link",
  duel: "skill_duel",
  swap: "skill_swap",
  corpse: "skill_corpse",
  fear: "skill_fear",
};

/** 公共事件 event_type → 事件 sfx 文件 id（非技能）。null = 不出声。 */
export function eventSfx(ev: { event_type: string; data?: Record<string, unknown> }): SfxId | null {
  switch (ev.event_type) {
    case "game_started": return "event_game_start";
    case "player_died": return "event_death_reveal";
    case "player_eliminated": return "event_execution";
    case "vote_result": return "event_vote_tally";
    case "sheriff_elected": return "event_sheriff_elected";
    case "sheriff_tie": return "event_vote_tie";
    case "lover_died": return "event_lover_death";
    case "game_ended":
      return ev.data?.winner_camp === "villager" ? "event_victory_good" : "event_victory_evil";
    default:
      return null;
  }
}

/** 粗阶段 → 转场 sfx（仅 nightfall/dawn）。 */
export function stageSfx(stage: CoarseStage): SfxId | null {
  if (stage === "night") return "event_nightfall";
  if (stage === "day") return "event_dawn";
  return null;
}

/** 磁盘上有文件的全部 id（供预加载）。 */
export const ALL_SFX_IDS: SfxId[] = [
  "skill_bite", "skill_inspect", "skill_heal", "skill_poison", "skill_shoot", "skill_vote",
  "skill_guard", "skill_charm", "skill_mark", "skill_link", "skill_duel", "skill_swap",
  "skill_corpse", "skill_fear",
  "event_game_start", "event_death_reveal", "event_execution", "event_vote_tally",
  "event_sheriff_elected", "event_nightfall", "event_dawn", "event_victory_good",
  "event_victory_evil", "event_lover_death", "event_vote_tie",
  "ui_click", "ui_hover", "ui_panel_open", "ui_panel_close", "ui_error", "ui_submit",
  "ui_your_turn", "ui_tick", "ui_timeout",
];

export function sfxPath(id: SfxId): string {
  return `/audio/${id}.mp3`;
}

/** 滑窗 burst 门：窗口内允许至多 max 次，超出抑制（吃掉连入 backlog 的洪流）。 */
export function createBurstGate(windowMs = 700, max = 3) {
  let times: number[] = [];
  return {
    allow(nowMs: number): boolean {
      times = times.filter((t) => nowMs - t < windowMs);
      const ok = times.length < max;
      times.push(nowMs);
      return ok;
    },
  };
}

/** event_id 单调去重（挡 EventSource 重连补发）。 */
export function createEventDedup() {
  let last = -1;
  return {
    seen(eventId?: number): boolean {
      if (eventId == null) return false;
      if (eventId <= last) return true;
      last = eventId;
      return false;
    },
  };
}
```

- [ ] **Step 4: 运行确认通过**

Run: `cd frontend && npx vitest run src/audio/soundMap.test.ts`
Expected: PASS（全部）。注：本步会因 `EffectType` 尚未扩到 15 而 TS 报错——Task 4 扩展后 `npm run lint` 才全绿；vitest 运行不阻塞。若 vitest 因类型失败，先做 Task 4 的 Step 3 再回来。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/audio/soundMap.ts frontend/src/audio/soundMap.test.ts
git commit -m "feat(audio): pure soundMap (id maps, burst gate, event dedup)"
```

---

## Task 3: 单例引擎 `soundManager.ts`

**Files:**
- Create: `frontend/src/audio/soundManager.ts`
- Test: `frontend/src/audio/soundManager.test.ts`

- [ ] **Step 1: 写冒烟测试**

Create `frontend/src/audio/soundManager.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from "vitest";

class FakeGain { gain = { value: 1 }; connect() {} }
class FakeCtx {
  state = "running";
  currentTime = 0;
  destination = {};
  createGain() { return new FakeGain(); }
  createBufferSource() { return { buffer: null, connect() {}, start() {} }; }
  resume() { return Promise.resolve(); }
  decodeAudioData() { return Promise.resolve({} as AudioBuffer); }
}

beforeEach(() => {
  (globalThis as unknown as { AudioContext: unknown }).AudioContext = FakeCtx;
  (globalThis as unknown as { fetch: unknown }).fetch = vi.fn().mockResolvedValue({ ok: false });
});

describe("soundManager", () => {
  it("plays without throwing when files are missing (fallback/silent)", async () => {
    const { soundManager } = await import("./soundManager");
    expect(() => soundManager.playUi("ui_click")).not.toThrow();
    expect(() => soundManager.playGameplay("skill_bite", 1)).not.toThrow();
    expect(() => soundManager.playGameplay("skill_bite", 1)).not.toThrow(); // dedup
  });
  it("mute / volume setters are safe", async () => {
    const { soundManager } = await import("./soundManager");
    expect(() => { soundManager.setMuted(true); soundManager.setSfxVolume(0.5); soundManager.unlock(); }).not.toThrow();
  });
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npx vitest run src/audio/soundManager.test.ts`
Expected: FAIL（Cannot find module './soundManager'）

- [ ] **Step 3: 实现 `soundManager.ts`**

Create `frontend/src/audio/soundManager.ts`:
```ts
import { sfxPath, createBurstGate, createEventDedup, ALL_SFX_IDS, type SfxId } from "./soundMap";
import {
  playInspectSFX, playHealSFX, playPoisonSFX, playBiteSFX, playShootSFX, playVoteSFX,
} from "../utils/audio";

/** 仅这 6 个 id 有合成兜底（文件缺失/未加载时用）。 */
const SYNTH_FALLBACK: Record<string, () => void> = {
  skill_bite: playBiteSFX,
  skill_inspect: playInspectSFX,
  skill_heal: playHealSFX,
  skill_poison: playPoisonSFX,
  skill_shoot: playShootSFX,
  skill_vote: playVoteSFX,
};

class SoundManager {
  private ctx: AudioContext | null = null;
  private sfxBus: GainNode | null = null;
  private bgmBus: GainNode | null = null;
  private cache = new Map<SfxId, AudioBuffer | null>();
  private inflight = new Map<SfxId, Promise<void>>();
  private muted = false;
  private sfxVolume = 0.8;
  private gate = createBurstGate();
  private dedup = createEventDedup();

  private ensureCtx(): AudioContext | null {
    if (this.ctx) return this.ctx;
    try {
      const Ctor = (window.AudioContext
        || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext);
      if (!Ctor) return null;
      this.ctx = new Ctor();
      this.sfxBus = this.ctx.createGain();
      this.bgmBus = this.ctx.createGain();
      this.sfxBus.connect(this.ctx.destination);
      this.bgmBus.connect(this.ctx.destination);
      this.bgmBus.gain.value = 0; // BGM 休眠占位
      this.applyGain();
    } catch {
      this.ctx = null;
    }
    return this.ctx;
  }

  private applyGain(): void {
    if (this.sfxBus) this.sfxBus.gain.value = this.muted ? 0 : this.sfxVolume;
  }

  unlock(): void {
    const ctx = this.ensureCtx();
    if (ctx && ctx.state === "suspended") ctx.resume().catch(() => {});
    this.preloadAll();
  }

  setMuted(m: boolean): void { this.muted = m; this.applyGain(); }
  setSfxVolume(v: number): void { this.sfxVolume = Math.max(0, Math.min(1, v)); this.applyGain(); }

  /** UI 音：即时、不去重、不过 burst 门。 */
  playUi(id: SfxId): void { this.emit(id); }

  /** 对局音：event_id 去重 + burst 门。 */
  playGameplay(id: SfxId, eventId?: number): void {
    if (this.dedup.seen(eventId)) return;
    if (!this.gate.allow(Date.now())) return;
    this.emit(id);
  }

  private emit(id: SfxId): void {
    const ctx = this.ensureCtx();
    if (!ctx || !this.sfxBus) return;
    if (ctx.state === "suspended") ctx.resume().catch(() => {});
    const cached = this.cache.get(id);
    if (cached) { this.playBuffer(cached); return; }
    if (cached === null) { this.fallback(id); return; }   // 已知缺文件
    this.fallback(id);                                     // 首次：先合成兜底
    void this.load(id);                                    // 后台加载，下次放文件
  }

  private playBuffer(buf: AudioBuffer): void {
    if (!this.ctx || !this.sfxBus) return;
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.sfxBus);
    src.start();
  }

  private fallback(id: SfxId): void {
    const fb = SYNTH_FALLBACK[id];
    if (fb) { try { fb(); } catch { /* autoplay blocked */ } }
  }

  private load(id: SfxId): Promise<void> {
    const existing = this.inflight.get(id);
    if (existing) return existing;
    const p = (async () => {
      try {
        const res = await fetch(sfxPath(id));
        if (!res.ok) { this.cache.set(id, null); return; }
        const arr = await res.arrayBuffer();
        const buf = await this.ctx!.decodeAudioData(arr);
        this.cache.set(id, buf);
      } catch {
        this.cache.set(id, null);
      } finally {
        this.inflight.delete(id);
      }
    })();
    this.inflight.set(id, p);
    return p;
  }

  private preloadAll(): void {
    if (!this.ensureCtx()) return;
    for (const id of ALL_SFX_IDS) {
      if (!this.cache.has(id) && !this.inflight.has(id)) void this.load(id);
    }
  }
}

export const soundManager = new SoundManager();
```

- [ ] **Step 4: 运行确认通过**

Run: `cd frontend && npx vitest run src/audio/soundManager.test.ts`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/audio/soundManager.ts frontend/src/audio/soundManager.test.ts
git commit -m "feat(audio): SoundManager singleton (dual-bus, cache, fallback, gate)"
```

---

## Task 4: `EffectType` 扩展 + `castMap` 事件映射

**Files:**
- Modify: `frontend/src/types.ts`（`EffectType`，约 87-88 行）
- Modify: `frontend/src/lib/castMap.ts`（`effectTypeForRole` + 新增 `effectTypeForEvent`）
- Test: `frontend/src/lib/castMap.test.ts`

- [ ] **Step 1: 加失败测试**

在 `frontend/src/lib/castMap.test.ts` 末尾追加：
```ts
import { effectTypeForEvent, effectTypeForRole } from "./castMap";

describe("effectTypeForEvent", () => {
  it("distinguishes witch poison vs save", () => {
    expect(effectTypeForEvent("witch_poison_used")).toBe("poison");
    expect(effectTypeForEvent("witch_saved")).toBe("heal");
  });
  it("maps special skills", () => {
    expect(effectTypeForEvent("raven_marked")).toBe("mark");
    expect(effectTypeForEvent("knight_duel")).toBe("duel");
    expect(effectTypeForEvent("graveyard_keeper_check")).toBe("corpse");
    expect(effectTypeForEvent("nightmare_blocked")).toBe("fear");
  });
  it("ignores vote_cast and unknowns", () => {
    expect(effectTypeForEvent("vote_cast")).toBeNull();
    expect(effectTypeForEvent("phase_changed")).toBeNull();
  });
});

describe("effectTypeForRole (expanded)", () => {
  it("maps the newly covered roles", () => {
    expect(effectTypeForRole("守卫")).toBe("guard");
    expect(effectTypeForRole("乌鸦")).toBe("mark");
    expect(effectTypeForRole("丘比特")).toBe("link");
    expect(effectTypeForRole("骑士")).toBe("duel");
    expect(effectTypeForRole("守墓人")).toBe("corpse");
  });
  it("keeps wolves as bite", () => {
    expect(effectTypeForRole("狼美人")).toBe("bite");
    expect(effectTypeForRole("Werewolf")).toBe("bite");
  });
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npx vitest run src/lib/castMap.test.ts`
Expected: FAIL（effectTypeForEvent is not a function）

- [ ] **Step 3: 扩 `EffectType`**

`frontend/src/types.ts` 把：
```ts
export type EffectType =
  | "inspect" | "heal" | "poison" | "bite" | "shoot" | "vote" | "rally";
```
改为：
```ts
export type EffectType =
  | "inspect" | "heal" | "poison" | "bite" | "shoot" | "vote" | "rally"
  | "guard" | "charm" | "mark" | "link" | "duel" | "swap" | "corpse" | "fear";
```

- [ ] **Step 4: 扩 `effectTypeForRole` + 加 `effectTypeForEvent`**

`frontend/src/lib/castMap.ts` 把 `effectTypeForRole` 整段替换为：
```ts
export function effectTypeForRole(role: string): EffectType {
  if (!role) return "rally";
  if (isWolf(role)) return "bite";
  const r = role.toLowerCase();
  if (role.includes("预言") || r.includes("seer") || r.includes("prophet")) return "inspect";
  if (role.includes("女巫") || r.includes("witch")) return "heal";
  if (role.includes("猎人") || r.includes("hunter")) return "shoot";
  if (role.includes("守墓") || r.includes("graveyard")) return "corpse";
  if (role.includes("守卫") || r.includes("guard")) return "guard";
  if (role.includes("骑士") || r.includes("knight")) return "duel";
  if (role.includes("魔术") || r.includes("magician")) return "swap";
  if (role.includes("乌鸦") || r.includes("raven")) return "mark";
  if (role.includes("丘比特") || r.includes("cupid")) return "link";
  if (role.includes("村民") || r.includes("villager")) return "vote";
  return "rally";
}

/** 后端技能结果事件 → effectType（声音用；不含 vote_cast）。 */
const SKILL_EVENT_EFFECT: Record<string, EffectType> = {
  seer_checked: "inspect",
  witch_saved: "heal",
  witch_poison_used: "poison",
  witch_poisoned: "poison",
  werewolf_killed: "bite",
  hunter_revenge: "shoot",
  white_wolf_killed: "shoot",
  guard_protected: "guard",
  guardian_wolf_protected: "guard",
  wolf_beauty_charmed: "charm",
  raven_marked: "mark",
  lovers_linked: "link",
  knight_duel: "duel",
  magician_swapped: "swap",
  graveyard_keeper_check: "corpse",
  nightmare_blocked: "fear",
};

export function effectTypeForEvent(eventType: string): EffectType | null {
  return SKILL_EVENT_EFFECT[eventType] ?? null;
}
```

- [ ] **Step 5: 运行确认通过 + 全量类型检查**

Run: `cd frontend && npx vitest run src/lib/castMap.test.ts src/audio/soundMap.test.ts && npm run lint`
Expected: PASS + 无 TS 错误（`effectTypeSfx` 现覆盖全 15 档）。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/types.ts frontend/src/lib/castMap.ts frontend/src/lib/castMap.test.ts
git commit -m "feat(audio): expand EffectType to 15 + effectTypeForEvent skill mapping"
```

---

## Task 5: store — audio slice + 持久化 + 初始化

**Files:**
- Modify: `frontend/src/store.ts`

- [ ] **Step 1: 顶部加导入与持久化辅助**

在 `store.ts` 现有 import 块之后加：
```ts
import { soundManager } from "./audio/soundManager";
import { effectTypeSfx, eventSfx, type SfxId } from "./audio/soundMap";
import { effectTypeForEvent, effectTypeForRole } from "./lib/castMap";
import type { SseEvent } from "./lib/gameReducer";

function readAudioPref(): { muted: boolean; volume: number } {
  try {
    const raw = localStorage.getItem("ww_audio");
    if (raw) {
      const p = JSON.parse(raw);
      return { muted: !!p.muted, volume: typeof p.volume === "number" ? p.volume : 0.8 };
    }
  } catch { /* ignore */ }
  return { muted: false, volume: 0.8 };
}
function writeAudioPref(p: { muted: boolean; volume: number }): void {
  try { localStorage.setItem("ww_audio", JSON.stringify(p)); } catch { /* ignore */ }
}

/** 单点：从一条 SSE 事件派发"技能/事件"音（座位安全由流可见性保证）。 */
function dispatchSseSound(ev: SseEvent): void {
  const et = effectTypeForEvent(ev.event_type);
  const sid: SfxId | null = et ? effectTypeSfx[et] : eventSfx(ev);
  if (sid) soundManager.playGameplay(sid, ev.event_id);
}
```
（`castMap` 之前已导入 `castFromSkillSubmit`/`castFromEvent`，本步只新增 `effectTypeForEvent`/`effectTypeForRole`，若重复请合并到同一 import。）

- [ ] **Step 2: `GameStore` 接口加 audio 字段**

在 `interface GameStore { ... }` 的合适位置（如 `insightEnabled` 附近）加：
```ts
  audioMuted: boolean;
  sfxVolume: number;
  setAudioMuted: (m: boolean) => void;
  setSfxVolume: (v: number) => void;
```

- [ ] **Step 3: store body 加初值与 setter**

在 `create<GameStore>((set, get) => ({ ... }))` 内（如 `insightEnabled: true,` 之后）加：
```ts
  audioMuted: readAudioPref().muted,
  sfxVolume: readAudioPref().volume,
  setAudioMuted: (m) => {
    soundManager.setMuted(m);
    writeAudioPref({ muted: m, volume: get().sfxVolume });
    set({ audioMuted: m });
  },
  setSfxVolume: (v) => {
    soundManager.setSfxVolume(v);
    writeAudioPref({ muted: get().audioMuted, volume: v });
    set({ sfxVolume: v });
  },
```

- [ ] **Step 4: 模块加载时把初始偏好推给 SoundManager**

在文件末尾 `export const useGameStore = create(...)` 之后加：
```ts
{
  const init = useGameStore.getState();
  soundManager.setMuted(init.audioMuted);
  soundManager.setSfxVolume(init.sfxVolume);
}
```

- [ ] **Step 5: 类型检查**

Run: `cd frontend && npm run lint`
Expected: PASS（`SseEvent`/`soundManager` 等均解析）。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/store.ts
git commit -m "feat(audio): store audio slice (mute/volume) with localStorage persistence"
```

---

## Task 6: store — SSE 音派发 + 座位提示音

**Files:**
- Modify: `frontend/src/store.ts`
- Test: `frontend/src/store.humanInput.test.ts`

- [ ] **Step 1: 加失败测试（座位音）**

在 `frontend/src/store.humanInput.test.ts` 末尾追加：
```ts
import { soundManager } from "./audio/soundManager";

describe("store: seat prompt sounds", () => {
  it("plays your_turn on awaiting_input", () => {
    const spy = vi.spyOn(soundManager, "playUi");
    useGameStore.getState().ingestSeatEvent({
      event_type: "awaiting_input", request_id: "r1", kind: "seat", seat: 1,
    });
    expect(spy).toHaveBeenCalledWith("ui_your_turn");
    spy.mockRestore();
  });
  it("plays timeout on input_timeout", () => {
    useGameStore.getState().ingestSeatEvent({
      event_type: "awaiting_input", request_id: "r2", kind: "seat", seat: 1,
    });
    const spy = vi.spyOn(soundManager, "playUi");
    useGameStore.getState().ingestSeatEvent({
      event_type: "input_timeout", request_id: "r2", kind: "seat", seat: 1,
    });
    expect(spy).toHaveBeenCalledWith("ui_timeout");
    spy.mockRestore();
  });
});
```
（若文件未导入 `vi`，在顶部 `import { describe, it, expect, vi } from "vitest";`。）

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npx vitest run src/store.humanInput.test.ts`
Expected: FAIL（playUi 未被以 ui_your_turn 调用）

- [ ] **Step 3: `ingestSeatEvent` 加座位音**

把 `ingestSeatEvent` 的两个分支改为：
```ts
    if (t === "awaiting_input") {
      set({ pendingInput: event, humanInputError: null, selectedTargetSeat: null });
      soundManager.playUi("ui_your_turn");
      return true;
    }
    if (t === "input_received" || t === "input_timeout") {
      const cur = get().pendingInput;
      if (cur && (event.request_id == null || event.request_id === cur.request_id)) {
        set({ pendingInput: null });
      }
      if (t === "input_timeout") soundManager.playUi("ui_timeout");
      return true;
    }
```

- [ ] **Step 4: 两个 onmessage 派发 SSE 音**

在 `connectSpectate` 的 `es.onmessage` 内，`const cast = castFromEvent(ev); if (cast) get().triggerCast(cast);` 之后加一行：
```ts
        dispatchSseSound(ev);
```
在 `connectSeat` 的 `es.onmessage` 内，同样在 `if (cast) get().triggerCast(cast);` 之后加：
```ts
        dispatchSseSound(ev);
```

- [ ] **Step 5: `submitHumanInput` 加 submit + 本人技能音**

在 `submitHumanInput` 成功分支，`set({ pendingInput: null, humanInputError: null });` 之后加：
```ts
      soundManager.playUi("ui_submit");
```
并在其后的 `if (selfRole && (kind === "seat" || kind === "witch"))` 块内、`get().triggerCast(...)` 之后加：
```ts
        soundManager.playGameplay(effectTypeSfx[effectTypeForRole(selfRole)]);
```

- [ ] **Step 6: 运行确认通过 + 不回归**

Run: `cd frontend && npx vitest run src/store.humanInput.test.ts src/lib/gameReducer.test.ts && npm run lint`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add frontend/src/store.ts frontend/src/store.humanInput.test.ts
git commit -m "feat(audio): dispatch skill/event sounds on SSE + seat prompt sounds"
```

---

## Task 7: CastSkillOverlay 改为视觉专用

**Files:**
- Modify: `frontend/src/components/CastSkillOverlay.tsx`

- [ ] **Step 1: 删除合成音 import 与播放**

删掉顶部这 6 个导入：
```ts
import { playInspectSFX, playHealSFX, playPoisonSFX, playBiteSFX, playShootSFX, playVoteSFX } from "../utils/audio";
```
并删除 `useEffect` 内 `// Play SFX matching effect type` 起、到 `playVoteSFX();` 那段 `switch (activeCast.effectType) { ... }`（约 24-45 行）。其余视觉逻辑保持不变。

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npm run lint`
Expected: PASS（无未用导入告警）。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/CastSkillOverlay.tsx
git commit -m "refactor(audio): CastSkillOverlay visual-only (sound moved to SoundManager)"
```

---

## Task 8: GameAudioBridge（转场音 + 解锁 + 音量同步）

**Files:**
- Create: `frontend/src/components/GameAudioBridge.tsx`
- Modify: `frontend/src/pages/GameApp.tsx`

- [ ] **Step 1: 创建组件**

Create `frontend/src/components/GameAudioBridge.tsx`:
```tsx
import { useEffect, useRef } from "react";
import { useGameStore } from "../store";
import { soundManager } from "../audio/soundManager";
import { stageSfx } from "../audio/soundMap";

/** 不渲染任何 DOM；把 store 信号桥接到 SoundManager。 */
export default function GameAudioBridge() {
  const stageFx = useGameStore((s) => s.stageFx);
  const audioMuted = useGameStore((s) => s.audioMuted);
  const sfxVolume = useGameStore((s) => s.sfxVolume);
  const lastNonce = useRef<number>(-1);

  // 首次手势解锁 AudioContext（满足浏览器自动播放策略）
  useEffect(() => {
    const unlock = () => soundManager.unlock();
    window.addEventListener("pointerdown", unlock, { once: true });
    return () => window.removeEventListener("pointerdown", unlock);
  }, []);

  // 音量 / 静音同步
  useEffect(() => { soundManager.setMuted(audioMuted); }, [audioMuted]);
  useEffect(() => { soundManager.setSfxVolume(sfxVolume); }, [sfxVolume]);

  // 昼夜转场音（stageFx 已被 PhaseTransitionCard 做过突发抑制）
  useEffect(() => {
    if (!stageFx) return;
    if (stageFx.nonce === lastNonce.current) return;
    lastNonce.current = stageFx.nonce;
    const sid = stageSfx(stageFx.stage);
    if (sid) soundManager.playGameplay(sid);
  }, [stageFx]);

  return null;
}
```

- [ ] **Step 2: 在 GameApp 挂载**

`frontend/src/pages/GameApp.tsx`：在顶部 import 区加：
```ts
import GameAudioBridge from "../components/GameAudioBridge";
```
在实况 `return (...)` 里、`<AlertOverlays />` 同级处加一行（任意 overlay 旁）：
```tsx
      <GameAudioBridge />
```

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npm run lint`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/GameAudioBridge.tsx frontend/src/pages/GameApp.tsx
git commit -m "feat(audio): GameAudioBridge — stage transition sfx, unlock, volume sync"
```

---

## Task 9: UI 音 — TopHeader / InsightDock / SeatCommandDock

**Files:**
- Modify: `frontend/src/components/TopHeader.tsx`
- Modify: `frontend/src/components/InsightDock.tsx`
- Modify: `frontend/src/components/SeatCommandDock.tsx`

- [ ] **Step 1: TopHeader 加静音键 + 音量滑块**

在 `TopHeader.tsx`：lucide 导入加 `Volume2, VolumeX`：
```ts
import { Sun, Moon, Clock, Flame, LogOut, Home, Volume2, VolumeX } from "lucide-react";
```
组件内（`const exitGame = ...` 附近）加：
```ts
  const audioMuted = useGameStore((s) => s.audioMuted);
  const sfxVolume = useGameStore((s) => s.sfxVolume);
  const setAudioMuted = useGameStore((s) => s.setAudioMuted);
  const setSfxVolume = useGameStore((s) => s.setSfxVolume);
```
在右侧按钮簇（`返回上一级` 按钮之前）插入：
```tsx
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setAudioMuted(!audioMuted)}
            aria-label={audioMuted ? "取消静音" : "静音"}
            className="h-7 w-7 rounded border border-zinc-800 bg-zinc-950/30 hover:bg-zinc-900/50 text-zinc-300 flex items-center justify-center cursor-pointer"
          >
            {audioMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
          </button>
          <input
            type="range" min={0} max={1} step={0.05} value={sfxVolume}
            onChange={(e) => setSfxVolume(Number(e.target.value))}
            aria-label="音效音量"
            className="w-16 accent-yellow-500 cursor-pointer hidden sm:block"
          />
        </div>
```

- [ ] **Step 2: InsightDock 展开/收起音**

在 `InsightDock.tsx` 顶部 import 加：
```ts
import { soundManager } from "../audio/soundManager";
```
桌面手风琴头 `onClick={() => setIsExpanded(!isExpanded)}`（约 90 行）改为：
```tsx
          onClick={() => {
            const next = !isExpanded;
            soundManager.playUi(next ? "ui_panel_open" : "ui_panel_close");
            setIsExpanded(next);
          }}
```
移动端按钮 `onClick={() => setIsExpanded(!isExpanded)}`（约 143 行）同样改为上面的形式。

- [ ] **Step 3: SeatCommandDock — 末10秒 tick + 选择 click**

在 `SeatCommandDock.tsx` 顶部 import 加：
```ts
import { soundManager } from "../audio/soundManager";
```
在已有 `const remaining = remainingSeconds(...)` 之后加倒计时滴答 effect：
```ts
  const prevRemainingRef = React.useRef<number>(remaining);
  React.useEffect(() => {
    if (remaining !== prevRemainingRef.current) {
      if (remaining > 0 && remaining <= 10) soundManager.playUi("ui_tick");
      prevRemainingRef.current = remaining;
    }
  }, [remaining]);
```
在 `TargetCard` 的 `onClick` 外包一层 click（找到渲染 `TargetCard` 处的 `onClick={() => setSelected(...)}`，改为）：
```tsx
        onClick={() => { soundManager.playUi("ui_click"); setSelected(selected === seat ? null : seat); }}
```
（witch 毒药目标的 `TargetCard`、multi 的 `toggleMulti` 同理在其 onClick 前加 `soundManager.playUi("ui_click");`。提交动作已由 store 的 `ui_submit` 覆盖，无需重复。）

- [ ] **Step 4: 类型检查 + 全量测试**

Run: `cd frontend && npm run lint && npx vitest run`
Expected: PASS（全部）。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/TopHeader.tsx frontend/src/components/InsightDock.tsx frontend/src/components/SeatCommandDock.tsx
git commit -m "feat(audio): UI sounds — mute/volume control, panel toggles, countdown tick"
```

---

## Task 10: 端到端验证

**Files:** 无（仅验证）

- [ ] **Step 1: 起后端 + 前端**

Run（两个后台）:
```bash
OBS_READY_REQUIRE_LLM=0 uv run werewolf-api --port 8010
cd frontend && npm run dev
```

- [ ] **Step 2: god 观战验证**

用 Playwright MCP 打开一局纯 LLM 观战（`/game?run_id=<live or demo>`），确认：
- 首次点击后有声（解锁生效）
- 昼夜切换有 `nightfall`/`dawn`
- 技能：seer/witch(救/毒)/wolf/guard/charm/mark… 有对应音，与塔罗动画近乎同步
- 死亡/放逐/计票/警长当选/胜负有音
- **中途加入**进行中对局：开头无"机关枪"（burst 门生效）

- [ ] **Step 3: 座位人机验证**

`human-6p-demo` 起一局，开座位视图，确认：
- `your_turn`（轮到你）/ `tick`（≤10s）/ `timeout` / `submit`
- 自己用技能有本人技能音；**他人技能不出声**（无泄漏）

- [ ] **Step 4: 控制验证**

- 顶栏静音键切换即时生效；音量滑块联动；刷新后保持（localStorage）

- [ ] **Step 5: 兜底验证**

临时改名一个文件（如 `event_dawn.mp3`）→ 天亮转场不报错（静默/或合成兜底）；改回。

- [ ] **Step 6: 记录并提交验证笔记**

写 `docs/reports/audio-integration-verification-2026-06-09.md`（测了什么、截图、逐项通过/失败），停后台服务。
```bash
git add docs/reports/audio-integration-verification-2026-06-09.md
git commit -m "docs: audio integration e2e verification"
```

---

## Self-Review（已自检）

- **spec 覆盖**：技能14（effectTypeForEvent+effectTypeSfx，Task4/6）✓；事件（eventSfx，Task2/6）✓；昼夜（stageSfx+GameAudioBridge，Task2/8）✓；座位 your_turn/tick/timeout/submit（Task6/9）✓；UI click/panel（Task9）✓；双总线+静音+解锁+持久化（Task3/5/8/9）✓；六个坑（burst/dedup/StrictMode-once/座位可见性/双响-改用结果事件/无BGM-bgmBus静默）✓；兜底（Task3/10）✓。
- **范围外（按 spec §3.6）**：`shield_break`、`hover` 广接、5 段 BGM — 本计划不实现（资产保留）。`ui_hover` 文件已存在但本期不接（克制；若需，后续给棋盘席位接）。
- **类型一致**：`SfxId`、`effectTypeSfx`(15)、`effectTypeForEvent`、`dispatchSseSound`、`soundManager.playUi/playGameplay/setMuted/setSfxVolume` 全程一致。
- **占位符**：无 TBD；每步含完整代码/命令。
