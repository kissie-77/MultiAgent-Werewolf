# 音效集成设计 — 把现有音效接入实况对局

> **模块**：frontend / audio
> **状态**：approved（设计已确认，待实现）
> **最后更新**：2026-06-09
> **关联**：[AUDIO_SPEC.md](../../frontend/AUDIO_SPEC.md)（完整规格）、[AUDIO_TODO.md](../../frontend/AUDIO_TODO.md)（待补 BGM）
> **范围**：仅把**现有 35 个 SFX**（技能14 + 事件12 + UI9，已生成并改英文名）接入**实况对局**（god 观战 + 座位人机）。BGM 暂不做（5 段未生成），但保留总线接口。

---

## 1. 决策摘要（来自 brainstorming）

| # | 决策 | 选定 |
|---|---|---|
| 1 | 生效范围 | **仅实况对局**（GameApp/store 单点接入；复盘页以后再说） |
| 2 | 技能音通路 | **统一走 activeCast**（扩 effectType→14 + castFromEvent 消费细分技能事件） |
| 3 | UI 音覆盖 | **只接关键控件**（座位坞、InsightDock、退出确认、静音键；hover 限棋盘席位/卡片/CTA） |
| 4 | 静音/默认 | **默认开声 + 静音键**（首次手势解锁；TopHeader 放静音+音量滑块；localStorage 持久化） |

---

## 2. 架构总览

```
SSE event ─► store.onmessage ─► dispatchGameSound(ev, prevStage)
                         ├ 技能: triggerCast(cast) ──► SoundManager.playGameplay(effectTypeSfx[effectType], event_id)
                         └ 事件: eventSfx(ev) ───────► SoundManager.playGameplay(id, event_id)
pendingInput ─► ingestSeatEvent ─► playUi(your_turn) / playUi(timeout)
stageFx(nonce) ─► GameAudioBridge ─► SoundManager.playGameplay(stageSfx[stage])
组件交互 ─► playUi(click/hover/panel_open/panel_close/submit/error)
                                            ▼
                              ┌────────────────────────────────┐
                              │  SoundManager (模块级单例)       │
                              │  AudioContext (lazy)            │
                              │  ├ sfxBus  : GainNode           │
                              │  └ bgmBus  : GainNode (休眠占位) │
                              │  bufferCache / inflight dedup    │
                              │  muted / sfxVolume (← store)     │
                              │  unlock() / burstGate / 兜底      │
                              └────────────────────────────────┘
```

**三层职责**
- **SoundManager（命令式单例）**：唯一出声口。持 AudioContext、双总线、缓冲缓存、解锁、burst 门、缺文件兜底。无 React 依赖。
- **soundMap（纯函数）**：`effectTypeSfx` / `eventSfx(ev)` / `stageSfx(stage)` + 资源清单。可单测。
- **派发点**：`store.onmessage`（事件/技能）、`GameAudioBridge`（昼夜转场）、座位组件（座位/UI 音）。

---

## 3. 资源清单与映射

文件位于 `frontend/public/audio/`，扁平命名 `<层>_<id>.mp3`（沿用已生成命名，归位即从仓库外 `audio/` 移入）。

### 3.1 `SfxId` 全集（35）
```
skill: bite inspect heal poison shoot vote guard charm mark link duel swap corpse fear        (14)
event: game_start death_reveal execution vote_tally sheriff_elected nightfall dawn
       victory_good victory_evil lover_death vote_tie shield_break                            (12)
ui:    click hover panel_open panel_close error submit your_turn tick timeout                 (9)
```
（另存 `event_victory_good_alt.mp3` 备选，不进映射。）

### 3.2 `effectTypeSfx`（技能：effectType → 文件）
| effectType | 文件 | effectType | 文件 |
|---|---|---|---|
| bite | skill_bite | charm | skill_charm |
| inspect | skill_inspect | mark | skill_mark |
| heal | skill_heal | link | skill_link |
| poison | skill_poison | duel | skill_duel |
| shoot | skill_shoot | swap | skill_swap |
| vote / rally | skill_vote | corpse | skill_corpse |
| guard | skill_guard | fear | skill_fear |

### 3.3 `effectTypeForEvent`（castMap 扩展：后端事件 → effectType，喂给 castFromEvent）
`seer_checked`→inspect · `witch_saved`→heal · `witch_poison_used`/`witch_poisoned`→poison · `werewolf_killed`→bite · `hunter_revenge`→shoot · `white_wolf_killed`→shoot · `guard_protected`/`guardian_wolf_protected`→guard · `wolf_beauty_charmed`→charm · `raven_marked`→mark · `lovers_linked`→link · `knight_duel`→duel · `magician_swapped`→swap · `graveyard_keeper_check`→corpse · `nightmare_blocked`→fear · `vote_cast`→vote
> `role_acting`/`role_revealed` 仍按角色名走 `effectTypeForRole`，作为细分事件缺失时的兜底；细分事件为权威（防双响，见 §6）。

### 3.4 `eventSfx`（事件层：event_type → 文件）
`game_started`→event_game_start · `player_died`→event_death_reveal · `player_eliminated`→event_execution · `vote_result`→event_vote_tally · `sheriff_elected`→event_sheriff_elected · `sheriff_tie`→event_vote_tie · `lover_died`→event_lover_death · `game_ended`→（`winner_camp==='villager'`? event_victory_good : event_victory_evil）

### 3.5 `stageSfx`（转场：coarseStage → 文件）
`night`→event_nightfall · `day`→event_dawn · `lobby`/`over`→null（胜负由 `game_ended` 事件出声）

### 3.6 本期不接的资产（明确范围，非遗漏）
- `event_shield_break`：缺明确的"长老抗刀/护盾"引擎事件触发，**本期不接**，资产保留待引擎事件确认后挂载。
- 5 段 BGM：未生成，bgmBus 仅占位。

---

## 4. 触发点对照（实现锚点）

| 声音 | 触发文件:位置 | 通路 |
|---|---|---|
| 14 技能音 | `store.ts` `triggerCast` 内联 | onmessage 与 submitHumanInput 都经 triggerCast → 一处覆盖 |
| 8 事件音 | `store.ts` `connectSpectate.onmessage` / `connectSeat.onmessage` | `dispatchGameSound(ev)` |
| nightfall/dawn | `components/GameAudioBridge.tsx`（新）订阅 `stageFx.nonce` | 复用 `PhaseTransitionCard` 既有突发抑制 |
| your_turn / timeout | `store.ts` `ingestSeatEvent`（awaiting_input / input_timeout） | 座位流专属（seat-only 事件） |
| submit | `store.ts` `submitHumanInput` 成功分支 | — |
| tick | `components/SeatCommandDock.tsx` 倒计时 ≤10s 每秒 | — |
| error | `store.ts` 设 `humanInputError` 处 + `AlertOverlays` | playUi |
| click / hover / panel_open / panel_close | `SeatCommandDock` / `InsightDock` / `TopHeader` 关键控件 | playUi |

---

## 5. SoundManager 接口（草案）

```ts
// src/audio/soundManager.ts
type SfxId = string; // 见 §3.1

interface SoundManager {
  unlock(): void;                          // resume AudioContext（首次手势）
  playUi(id: SfxId): void;                 // 不过 burst 门、不去重
  playGameplay(id: SfxId, eventId?: number): void; // 过 burst 门 + event_id 去重
  setMuted(muted: boolean): void;          // 来自 store slice
  setSfxVolume(v: number): void;           // 0..1
  // bgm* 接口预留，本期 no-op
}
```
- **缓冲缓存**：首次 `play*` 异步 `fetch + decodeAudioData`，结果缓存；同 id 并发加载去重；404 → 缓存 `null` → 静默。
- **解锁**：`window.addEventListener('pointerdown', unlock, {once:true})`；`play*` 内若 `ctx.state==='suspended'` 也 `resume()`。
- **兜底**：`synthFallback: Record<SfxId, ()=>void>` 仅含现有 6 个合成（bite/inspect/heal/poison/shoot/vote）。`playGameplay`：有缓冲放文件；否则有兜底放合成；否则静默 → 归位前/缺文件也有核心音、不报错。
- **总线**：`sfxBus.gain = muted ? 0 : sfxVolume`；`bgmBus` 建好但增益 0、不加载。

---

## 6. 六个坑的处理

| 坑 | 对策 |
|---|---|
| **StrictMode 双触发**（`main.tsx`） | 副作用幂等；`unlock` 用 `{once:true}`；onmessage 已有 `sseConnectGen` 守卫沿用 |
| **中途加入→事件机关枪**（`phaseStage.ts` 已记录该突发） | burst 门：滑窗 `BURST_WINDOW_MS=800` 内 gameplay 音 >`BURST_MAX=4` ⇒ 抑制至窗口清空。正常对局每声间隔数秒，永不触发；连入 backlog 的 ms 级洪流被吃掉 |
| **重连补发→重复播** | store 持 `lastSoundEventId` 单调去重；`playGameplay(id, eventId)` 跳过 `eventId <= lastSoundEventId` |
| **座位信息泄漏** | 技能音只经 `castFromEvent`（对脱敏角色返 `null`）→ 座位流不会听出他人身份 |
| **同一施法双响**（`role_acting` + 细分事件） | 细分事件为权威；`role_acting` 退兜底；同 `seat` 短窗（~1.5s）去重 |
| **无 BGM** | 全部 SFX 独立于 bgmBus；bgmBus 仅占位、增益 0 |

burst 门只作用于 `playGameplay`；UI 音（`playUi`）即时、不抑制。

---

## 7. 状态与持久化

- store 新增 audio slice：`audioMuted: boolean`、`sfxVolume: number`（默认 `false` / `0.8`），写入 `localStorage`（键 `ww_audio`）；启动读取。
- store 订阅该 slice → `SoundManager.setMuted/setSfxVolume`。
- `TopHeader` 绑定 slice 渲染静音键 + 音量滑块（仅 `isLiveRun` 时显示）。

---

## 8. 文件改动清单

**新增**
- `src/audio/soundManager.ts` — 单例引擎
- `src/audio/soundMap.ts` — 纯映射 + 资源清单 + burst 判定
- `src/audio/soundMap.test.ts` — 单测
- `src/components/GameAudioBridge.tsx` — 订阅 stageFx 播昼夜转场（挂进 GameApp）
- 资产：`audio/*.mp3` → `frontend/public/audio/*.mp3`

**改动**
- `src/types.ts` — `EffectType` 扩到 14（+poison/guard/charm/mark/link/duel/swap/corpse/fear；保留 rally）
- `src/lib/castMap.ts` — `effectTypeForRole` 扩档 + 新增 `effectTypeForEvent`；`castFromEvent` 消费细分技能事件
- `src/store.ts` — `triggerCast` 内联技能音；`onmessage` 派发事件音（去重+门）；`ingestSeatEvent` your_turn/timeout；`submitHumanInput` submit；audio slice + 持久化 + unlock
- `src/components/CastSkillOverlay.tsx` — 移除 6 个合成音调用（视觉专用；合成迁入 SoundManager 兜底）
- `src/components/SeatCommandDock.tsx` — tick + 按钮 click
- `src/components/InsightDock.tsx` — panel_open/close + toggle click
- `src/components/TopHeader.tsx` — 静音键 + 音量滑块
- `src/pages/GameApp.tsx` — 挂 `<GameAudioBridge/>`
- `src/utils/audio.ts` — 保留（被 SoundManager 引为兜底）

---

## 9. 测试策略

- `soundMap.test.ts`：`effectTypeSfx` 14 档齐全；`effectTypeForEvent` 全事件映射；`eventSfx`/`stageSfx` 正确；`game_ended` 按 winner_camp 分流；burst 判定（滑窗）纯逻辑。
- `castMap` 扩展加测：细分事件→effectType；座位脱敏（role==""）→ `castFromEvent` 返 null。
- SoundManager：vitest(node) 下 mock `AudioContext`/`fetch`，断言"放了哪个 id / 是否被门拦 / 缺文件走兜底"，不真出声。
- 现有 `store.humanInput.test.ts`、`gameReducer.test.ts` 不回归。

---

## 10. 验收

- [ ] 实况 god 观战：技能塔罗动画与对应音同步；昼夜切换有 nightfall/dawn；死亡/放逐/计票/警长/胜负出声
- [ ] 座位人机：your_turn / tick(≤10s) / timeout / submit / error；他人技能**不**出声（无泄漏）
- [ ] 中途加入进行中对局：无"机关枪"（burst 门生效）
- [ ] 重连不重复播（event_id 去重）
- [ ] 静音键 + 音量滑块生效并持久化；默认开声、首次手势解锁
- [ ] 缺某 mp3 或归位前：不报错、核心 6 音走合成兜底
- [ ] `npm run lint` + `npx vitest run` 通过
