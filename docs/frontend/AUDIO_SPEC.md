# 前端音效需求规格书（AI 生成用）

> **模块**：frontend / audio
> **状态**：draft
> **最后更新**：2026-06-09
> **关联代码**：`frontend/src/utils/audio.ts`（现有合成）、`frontend/src/components/CastSkillOverlay.tsx`、`frontend/src/lib/castMap.ts`、`frontend/src/store.ts`
> **用途**：本文件是「我用 AI 在外部平台生成音频」的需求清单。每条都给了可直接粘贴的英文 prompt，前置 `[GOTHIC]`、后置 `[NEG]` 两个宏即可。

---

## 1. 决策汇总

| # | 维度 | 选定 |
|---|---|---|
| 1 | 范围 | 全套分层体系（技能 + 事件/转场 + 环境/BGM + UI/座位） |
| 2 | 产出方式 | 外部 AI 生成音频文件；本文件只给规格与 prompt |
| 3 | 技能音粒度 | 按「独特机制」分组，14 个（非每角色 22 个） |
| 4 | 听感基调 | 暗黑哥特 / 神秘学 |
| 5 | 环境/BGM 循环 | 5 段 |
| 6 | 事件/转场单次音 | 12 个（含特殊事件） |
| 7 | UI/座位反馈音 | 9 个（含 hover / 超时） |
| 8 | 播放控制 | 双总线（BGM/SFX）+ 全局静音 + 首次点击解锁 |

**总计 40 个音频资产** = 14 技能 + 12 事件 + 5 BGM + 9 UI/座位。
其中标 ✅ 的 6 个已有 Web Audio 合成版（`utils/audio.ts`），可用 AI 重制升级或保留兜底。

---

## 2. 资产目录结构

```
frontend/public/audio/
├── skill/     # 14 个技能音（SFX 总线）
├── event/     # 12 个事件/转场音（SFX 总线）
├── bgm/       #  5 段环境/BGM 循环（BGM 总线）
└── ui/        #  9 个 UI/座位反馈音（SFX 总线）
```

---

## 3. 全局生成约定

### 3.1 两个可复用宏（生成时手动拼接）

**`[GOTHIC]`（风格前缀，粘到每条 prompt 前面）：**

```
Dark gothic, occult dark-fantasy, dimly lit cathedral atmosphere. Timbre palette:
low cello & double bass, pipe organ, faint distant Latin choir, tolling church bells,
parchment and aged-wood texture. Mood: ominous, ceremonial, tense.
```

**`[NEG]`（负向词，粘到每条 prompt 后面 / 填进 negative 框）：**

```
no modern EDM, no synthwave, no bright pop, no upbeat dance beat, no lyrics,
no clipping/distortion, no lo-fi hiss bed unless specified, no comedic cartoon tone.
```

### 3.2 技术规格

| 项 | 规格 |
|---|---|
| 格式 | 主 `.ogg`（小体积）+ `.mp3` 兜底（Safari） |
| 采样率/声道 | 44.1 kHz / stereo（纯 SFX 可 mono） |
| 响度 | BGM/环境 ≈ **-18 LUFS**；one-shot SFX 峰值 ≈ **-3 dBFS** |
| 循环 | BGM/环境必须 **无缝循环**（首尾零交叉、尾部留 reverb 衔接） |
| 调性 | 统一 **D 小调 / 自然小调(Aeolian)**，BGM ~60-72 BPM，便于多段交叉淡入不冲突 |
| 命名 | 全小写，见各层「文件名」列，落到对应子目录 |

### 3.3 推荐工具

- **one-shot SFX**（技能/事件/UI）：ElevenLabs Sound Effects、Stable Audio、Optimizer 类 SFX 生成器
- **BGM/环境 loop**：Suno / Udio / Stable Audio（生成后用 Audacity 做无缝循环点）

---

## 4. ① 技能层（14 个）

- **目录**：`public/audio/skill/`　**总线**：SFX　**类型**：one-shot
- **生成模板**：`[GOTHIC]` + 下表 EN Prompt + `[NEG]`
- **信息安全**：座位视角下他人技能音不播放（`castFromEvent` 对脱敏角色返回 null），仅本人技能与 god 视角全量播放。

| 文件名 | 触发角色 / 后端事件 | 时长 | EN Prompt（前置 [GOTHIC]、后置 [NEG]） |
|---|---|---|---|
| `bite` ✅ | 全狼夜刀 / `werewolf_killed` | 0.8s | Werewolf night kill: a guttural low growl swelling, then a wet visceral flesh-tearing rip as fangs sink in, heavy and muffled, ending on a low thud. |
| `inspect` ✅ | 预言家 / `seer_checked` | 1.4s | Seer divination: an ethereal rising shimmer with crystalline glints, a soul being peered into, mystical and cold, gentle reverberant tail. |
| `heal` ✅ | 女巫解药 / `witch_saved` | 1.1s | Witch healing potion: a soft major-triad bell arpeggio (C–E–G–C) with warm sacred reverb, life restored, hopeful and holy. |
| `poison` ✅ | 女巫毒药 / `witch_poison_used` | 2.0s | Witch poison: a bubbling acidic cauldron with low sawtooth gurgle and corrosive hissing fizz slowly decaying, sinister and venomous. |
| `shoot` ✅ | 猎人/狼王/白狼 / `hunter_revenge`,`white_wolf_killed` | 1.5s | Hunter's dying gunshot: a metallic hammer cock, then a deep booming black-powder shot with a cavernous reverb tail, final and fatal. |
| `vote` ✅ | 投票落子 / `vote_cast` | 3.0s | Voting verdict: a single deep cathedral dome bell with rich overtones ringing out and slowly decaying, solemn judgement. |
| `guard` | 守卫/守卫狼 / `guard_protected`,`guardian_wolf_protected` | 1.2s | Guardian protection: a holy shield coalescing, a shimmering metallic hum rising into a warm protective chime, sheltering. |
| `charm` | 狼美人 / `wolf_beauty_charmed` | 1.5s | Wolf Beauty charm: an eerie seductive harp glissando with a breathy female sigh and a hypnotic shimmer, alluring yet dangerous. |
| `mark` | 乌鸦 / `raven_marked` | 1.0s | Raven's mark: a sharp crow caw with a searing brand sizzle and a dark resonant stamp, foreboding. |
| `link` | 丘比特 / `lovers_linked` | 1.6s | Cupid links lovers: a plucked heartstring and two bells resonating in unison, a fateful bond, bittersweet and destined. |
| `duel` | 骑士 / `knight_duel` | 1.2s | Knight's duel: twin swords unsheathing and clashing with a bright metallic ring and reverberant tail, resolute and chivalric. |
| `swap` | 魔术师/盗贼 / `magician_swapped` | 1.0s | Magician swap: a magical teleport whoosh with riffling card flutter, a quick sleight-of-hand, mysterious. |
| `corpse` | 守墓人 / `graveyard_keeper_check` | 1.5s | Gravekeeper autopsy: wet soil turned over with a ghostly whisper beneath, examining the dead, grim and cold. |
| `fear` | 梦魇狼 / `nightmare_blocked` | 1.8s | Nightmare Wolf dread: a low sub-bass fear drone with a slowing heartbeat and suffocating ringing silence, paralysing terror. |

---

## 5. ② 事件 / 转场层（12 个）

- **目录**：`public/audio/event/`　**总线**：SFX　**类型**：one-shot stinger
- **生成模板**：`[GOTHIC]` + 下表 EN Prompt + `[NEG]`

| 文件名 | 触发 / 后端事件 | 时长 | EN Prompt（前置 [GOTHIC]、后置 [NEG]） |
|---|---|---|---|
| `nightfall` | 入夜 `phase_changed→night` / stageFx | 2.5s | Night falls: a descending dark whoosh into a low tolling bell with a cold night wind, darkness descending over the village. |
| `dawn` | 天亮 `phase_changed→day` | 2.5s | Dawn breaks: a rising choir swell into a bright morning bell, light returning and dread lifting. |
| `game_start` | 开局 `game_started` | 2.0s | Game begins: a single heavy gong strike, then a swelling pipe-organ minor chord, a court convening, ceremonial. |
| `death_reveal` | 夜亡揭晓 `player_died` | 2.0s | Death announced: a lone funeral bell toll with a faint mournful female wail beneath, a life lost in the night. |
| `execution` | 投票放逐 `player_eliminated` | 2.0s | Banishment by vote: a heavy guillotine drop impact with a low crowd gasp and a dying chord, the verdict carried out. |
| `vote_tally` | 投票揭晓 `vote_result` | 1.5s | Votes revealed: paper ballots riffling, then a wooden gavel strike, the count finalized. |
| `sheriff_elected` | 警徽加身 `sheriff_elected` | 2.0s | Sheriff badge bestowed: a short brass fanfare into a metallic badge chime, a coronation, authoritative. |
| `victory_good` | 好人胜 `game_ended` (villager) | 4.0s | Villagers win: a triumphant Latin choir chorus rising with morning bells and warm strings, redemption and dawn. |
| `victory_evil` | 狼人胜 `game_ended` (werewolf) | 4.0s | Werewolves win: ominous low brass with a sinister chuckle and a final death knell, darkness usurps the throne. |
| `lover_death` | 情侣殉情 `lover_died` | 2.5s | Lovers die together: a single broken piano note shattering with a snapping heartstring and a sorrowful string fall, tragic and beautiful. |
| `vote_tie` | 平票 PK `sheriff_tie` / 平票 | 1.5s | Tied vote standoff: a suspended trembling string tremolo holding unresolved, a tense pregnant pause. |
| `shield_break` | 长老抗刀 / 护盾破碎（白狼自爆复用重版） | 1.2s | Shield shatters: a crystalline barrier cracking and exploding into metallic shards, defense broken. |

---

## 6. ③ 环境 / BGM 循环层（5 段）

- **目录**：`public/audio/bgm/`　**总线**：BGM　**类型**：无缝 loop
- **生成模板**：`[GOTHIC]` + 下表 EN Prompt + `[NEG]`；统一 D 小调，生成后做无缝循环点。

| 文件名 | 场景（前端状态） | 时长(loop) | EN Prompt（前置 [GOTHIC]、后置 [NEG]） |
|---|---|---|---|
| `lobby` | 开局设置页（`!isLiveRun`） | 40-60s | Mysterious astrolabe lobby ambience: slow harp arpeggios over a warm dark pad with distant bells, anticipation, dark fantasy. Seamless loop, D minor, ~60 BPM. |
| `amb_day` | 白天阶段床（DAY_*） | 40-60s | Daytime deliberation bed: low-tension sustained strings with faint parchment rustle, watchful unease. Seamless loop, D minor, ~66 BPM, no melody, no drums. |
| `amb_night` | 黑夜阶段床（NIGHT_*） | 40-60s | Night phase bed: a deep ominous drone with night insects and a slow heartbeat pulse, lurking predation. Seamless loop, very dark, sparse, no melody. |
| `tension` | 投票/警长竞选（DAY_VOTE, SHERIFF_*） | 30-45s | Voting / sheriff-campaign tension: building strings crescendo with rolling timpani and rising dread, confrontation approaching. Loopable, D minor, ~72 BPM. |
| `settlement` | 结算面板（GAME_OVER） | 40-60s | Game-over settlement bed: solemn slow strings and pipe organ closing theme, the curtain falling, dignified. Seamless loop, sits under victory/defeat stingers. |

---

## 7. ④ UI / 座位反馈层（9 个）

- **目录**：`public/audio/ui/`　**总线**：SFX（座位音也走 SFX 总线）　**类型**：short one-shot
- **生成模板**：`[GOTHIC]` + 下表 EN Prompt + `[NEG]`（UI 音可弱化风格前缀，保持极短干净）

| 文件名 | 触发 | 时长 | EN Prompt（前置 [GOTHIC]、后置 [NEG]） |
|---|---|---|---|
| `click` | 按钮点击 | 0.1s | UI button click: a short crisp wooden tap / wax-seal stamp, tactile and dry. |
| `hover` | 悬停（极轻，可全局调低） | 0.08s | UI hover: an extremely subtle quill-feather brush, very quiet. |
| `panel_open` | 面板/抽屉展开 | 0.3s | Panel open: a short parchment scroll unrolling whoosh. |
| `panel_close` | 面板收起 | 0.25s | Panel close: a short parchment scroll furling whoosh, slightly lower pitch. |
| `error` | 报错/非法输入（`humanInputError`、AlertOverlays） | 0.5s | Error / invalid input: a low dissonant error hum, a minor-second clash, brief and discouraging. |
| `submit` | 提交成功（`submitHumanInput` 成功） | 0.4s | Submit success: a wax-seal press into a soft confirming bell ding, satisfying. |
| `your_turn` | 轮到你了（座位 `awaiting_input`） | 1.0s | Your-turn alert: a summoning hand-bell with a gentle heartbeat reminder, attention-grabbing but not harsh. |
| `tick` | 末 10 秒倒计时（每秒触发，`deadline`） | 0.15s | Countdown tick: a single dry pocket-watch tick, neutral. |
| `timeout` | 超时（`input_timeout`） | 0.8s | Time expired: an hourglass running out into a muffled low bell, a missed chance. |

---

## 8. 后端事件 → 音效映射（接线参考）

> 前端在 `store.ts` 的 SSE `onmessage` 按 `event_type` 触发；技能音经 `castMap.ts` 的 `effectType` 派发。

| 后端 `event_type` | 触发音效 | 层 |
|---|---|---|
| `werewolf_killed` | `skill/bite` | 技能 |
| `seer_checked` | `skill/inspect` | 技能 |
| `witch_saved` | `skill/heal` | 技能 |
| `witch_poison_used` / `witch_poisoned` | `skill/poison` | 技能 |
| `hunter_revenge` | `skill/shoot` | 技能 |
| `white_wolf_killed` | `skill/shoot` + `event/shield_break`(重版) | 技能/事件 |
| `vote_cast` | `skill/vote` | 技能 |
| `guard_protected` / `guardian_wolf_protected` | `skill/guard` | 技能 |
| `wolf_beauty_charmed` | `skill/charm` | 技能 |
| `raven_marked` | `skill/mark` | 技能 |
| `lovers_linked` | `skill/link` | 技能 |
| `knight_duel` | `skill/duel` | 技能 |
| `magician_swapped` | `skill/swap` | 技能 |
| `graveyard_keeper_check` | `skill/corpse` | 技能 |
| `nightmare_blocked` | `skill/fear` | 技能 |
| `phase_changed`→night（含 `sub_phase`） | `event/nightfall` + BGM→`amb_night` | 事件/BGM |
| `phase_changed`→day | `event/dawn` + BGM→`amb_day` | 事件/BGM |
| `game_started` | `event/game_start` + BGM→`amb_day`/`amb_night` | 事件/BGM |
| `player_died` | `event/death_reveal` | 事件 |
| `player_eliminated` | `event/execution` | 事件 |
| `vote_result` | `event/vote_tally` | 事件 |
| `sheriff_elected` | `event/sheriff_elected` | 事件 |
| `sheriff_tie` / 平票 | `event/vote_tie` | 事件 |
| `lover_died` | `event/lover_death` | 事件 |
| `game_ended`(villager) | `event/victory_good` + BGM→`settlement` | 事件/BGM |
| `game_ended`(werewolf) | `event/victory_evil` + BGM→`settlement` | 事件/BGM |
| `awaiting_input`(seat) | `ui/your_turn`；`deadline` 末10s 起 `ui/tick` | 座位 |
| `input_received` | `ui/submit` | 座位 |
| `input_timeout` | `ui/timeout` | 座位 |
| 进入 `DAY_VOTE`/`SHERIFF_*` | BGM→`tension` | BGM |

---

## 9. 播放控制规格（双总线 + 静音 + 解锁）

- **两条总线**：`bgmBus`（BGM/环境）、`sfxBus`（技能/事件/UI/座位）各接一个 `GainNode` → `destination`，各自音量 0–1。
- **全局静音**：一键 mute/unmute（不丢失各总线音量值）。
- **自动播放解锁**：`AudioContext` 初始 suspended；首屏显示「🔊 点击开启声音」浮层，用户首次手势 `ctx.resume()` 后才起 BGM（满足浏览器 autoplay 策略）。未解锁前所有 `play*` 静默兜底（沿用现有 `try/catch`）。
- **持久化**：音量/静音存 `localStorage`，跨会话保留。
- **建议 UI 位置**：`TopHeader` 加静音按钮 + 两个音量滑块；解锁浮层在 `GameApp` 首屏。

---

## 10. 落地接线（生成完音频后实现）

1. **`utils/audio.ts` → 升级为 `SoundManager`**：双 `GainNode` 总线；`unlock()`；`playSfx(id)` / `playBgm(id,{loop,fadeMs})` / `crossfadeBgm(id)`；`setVolume(bus,v)` / `toggleMute()`；保留现有 6 个合成函数作缺失兜底。
2. **`castMap.ts` 扩展**：`EffectType` 从 7 扩到 14（加 `guard/charm/mark/link/duel/swap/corpse/fear`）；`castFromEvent` 增配后端各技能事件 → 文件名。
3. **`store.ts` SSE 钩子**：`connectSpectate/connectSeat` 的 `onmessage` 按 §8 表派发事件音；`reduceEvent` 输出 phase 切换时触发 `nightfall/dawn` + BGM crossfade；座位 `awaiting_input/input_*` 触发座位音。
4. **控制 UI**：`TopHeader` 静音+双滑块；`GameApp` 首屏解锁浮层。

---

## 11. 验收清单

- [ ] 40 个文件齐全（`skill`14 / `event`12 / `bgm`5 / `ui`9），命名与目录一致
- [ ] 5 段 BGM 无缝循环、无爆点
- [ ] 响度达标（BGM ≈ -18 LUFS，SFX 峰值 ≈ -3 dBFS）
- [ ] 座位视角他人技能音不泄漏（`bite/inspect/...` 仅本人 + god 视角播放）
- [ ] 首次进入需点击解锁，未解锁不报错、不白屏
- [ ] 双总线音量 + 静音生效并持久化
- [ ] 昼夜切换 BGM 平滑 crossfade，不与事件 stinger 打架

---

## 12. 批次生成清单（音频网站工作流）

> 适配「音效包」模式的三条硬约束：**每批 ≤10 条**、**整批共用一个时长**（下拉 0.5–10 秒）、**5 credits/秒/条**。
> 故按「时长一致」把 35 个 SFX 分成 6 批（音效包模式）；5 段 BGM 超 10 秒，单独走 **BGM 模式**。
>
> **通用设置（每批都一样）**：模式=`音效包`；`响度归一化`=**开**；`温度`=**偏「更准确」（拉高）**。每条 prompt 已内联风格词，可独立粘贴；若有负向框，统一填 `no EDM, no pop, no lyrics, no clipping`。

### 批次 A — `音效包` / 时长 `0.5秒` / 7 条（UI）　≈17.5 credits

```
1. click        | Dark gothic UI click: a short crisp wooden tap / wax-seal stamp, dry and tactile.
2. hover        | Dark gothic UI hover: an extremely subtle, very quiet quill-feather brush.
3. panel_open   | Dark gothic UI: a short parchment scroll unrolling whoosh.
4. panel_close  | Dark gothic UI: a short parchment scroll furling whoosh, slightly lower pitch.
5. error        | Dark gothic error tone: a low dissonant hum, a brief minor-second clash, discouraging.
6. submit       | Dark gothic confirm: a wax-seal press into a soft confirming bell ding.
7. tick         | Dark gothic countdown tick: a single dry pocket-watch tick, neutral.
```

### 批次 B — `音效包` / 时长 `1秒` / 9 条（技能6 + 事件1 + 座位2）　≈45 credits

```
1. bite         | Dark gothic werewolf kill: a low growl into a wet flesh-tearing rip, heavy and muffled, ending on a thud.
2. heal         | Dark gothic witch healing: a soft major-triad bell chime with warm sacred reverb, hopeful and holy.
3. guard        | Dark gothic guardian shield: a shimmering metallic hum rising into a warm protective chime.
4. mark         | Dark gothic raven mark: a sharp crow caw with a searing brand sizzle and a dark resonant stamp.
5. duel         | Dark gothic knight duel: twin swords unsheathing and clashing, bright metallic ring with reverberant tail.
6. swap         | Dark gothic magician swap: a magical teleport whoosh with riffling card flutter, sleight of hand.
7. shield_break | Dark gothic shield shatter: a crystalline barrier cracking and exploding into metallic shards.
8. your_turn    | Dark gothic your-turn alert: a summoning hand-bell with a gentle heartbeat reminder, clear but not harsh.
9. timeout      | Dark gothic timeout: an hourglass running out into a muffled low bell, a missed chance.
```

### 批次 C — `音效包` / 时长 `2秒` / 10 条（技能7 + 事件3）　≈100 credits

```
1.  inspect       | Dark gothic seer divination: an ethereal rising shimmer with crystalline glints and a cold reverberant tail.
2.  poison        | Dark gothic witch poison: a bubbling acidic cauldron, low sawtooth gurgle and corrosive hissing fizz decaying.
3.  shoot         | Dark gothic hunter gunshot: a metallic hammer cock then a deep booming black-powder shot with cavernous reverb.
4.  charm         | Dark gothic wolf-beauty charm: an eerie seductive harp glissando with a breathy female sigh and hypnotic shimmer.
5.  link          | Dark gothic cupid bond: a plucked heartstring and two bells resonating in unison, bittersweet and fated.
6.  corpse        | Dark gothic gravekeeper autopsy: wet soil turned over with a ghostly whisper beneath, grim and cold.
7.  fear          | Dark gothic nightmare dread: a low sub-bass fear drone with a slowing heartbeat and suffocating ringing silence.
8.  game_start    | Dark gothic game start: a single heavy gong strike into a swelling pipe-organ minor chord, ceremonial.
9.  death_reveal  | Dark gothic death knell: a lone funeral bell toll with a faint mournful female wail beneath.
10. execution     | Dark gothic banishment: a heavy guillotine drop impact with a low crowd gasp and a dying chord.
```

### 批次 D — `音效包` / 时长 `2秒` / 3 条（事件）　≈30 credits

```
1. vote_tally      | Dark gothic vote tally: paper ballots riffling then a wooden gavel strike, the count finalized.
2. sheriff_elected | Dark gothic sheriff coronation: a short brass fanfare into a metallic badge chime, authoritative.
3. vote_tie        | Dark gothic tied vote: a suspended trembling string tremolo holding unresolved, a tense pause.
```

### 批次 E — `音效包` / 时长 `3秒` / 4 条（技能1 + 事件3）　≈60 credits

```
1. vote        | Dark gothic voting verdict: a single deep cathedral dome bell with rich overtones ringing and slowly decaying.
2. nightfall   | Dark gothic nightfall: a descending dark whoosh into a low tolling bell with cold night wind.
3. dawn        | Dark gothic dawn: a rising choir swell into a bright morning bell, dread lifting.
4. lover_death | Dark gothic lovers' death: a broken piano note shattering with a snapping heartstring and a sorrowful string fall.
```

### 批次 F — `音效包` / 时长 `4秒` / 2 条（事件·胜负）　≈40 credits

```
1. victory_good | Dark gothic villager victory: a triumphant Latin choir chorus rising with morning bells and warm strings.
2. victory_evil | Dark gothic werewolf victory: ominous low brass with a sinister chuckle and a final death knell.
```

### 批次 G — `BGM` 模式 / 逐条生成 / 5 段（时长选该模式上限，建议 30–60s，无缝循环）

> BGM 超 10 秒，不能用音效包。统一 D 小调；生成后用 Audacity 做无缝循环点。响度归一化=开。

```
1. lobby      | Dark gothic occult lobby loop, D minor ~60 BPM: slow harp arpeggios over a warm dark pad with distant bells, mysterious anticipation. Seamless loop.
2. amb_day    | Dark gothic daytime bed loop, D minor ~66 BPM: low-tension sustained strings with faint parchment rustle, watchful unease, no melody, no drums. Seamless loop.
3. amb_night  | Dark gothic night bed loop: deep ominous drone with night insects and a slow heartbeat pulse, lurking predation, sparse, no melody. Seamless loop.
4. tension    | Dark gothic tension loop, D minor ~72 BPM: building strings crescendo with rolling timpani and rising dread. Loopable.
5. settlement | Dark gothic settlement loop: solemn slow strings and pipe organ closing theme, dignified, sits under stingers. Seamless loop.
```

### 批次汇总与预算

| 批次 | 模式 | 时长 | 条数 | 预计 credits |
|---|---|---|---|---|
| A | 音效包 | 0.5秒 | 7 | 17.5 |
| B | 音效包 | 1秒 | 9 | 45 |
| C | 音效包 | 2秒 | 10 | 100 |
| D | 音效包 | 2秒 | 3 | 30 |
| E | 音效包 | 3秒 | 4 | 60 |
| F | 音效包 | 4秒 | 2 | 40 |
| **SFX 小计** | | | **35** | **≈292.5** |
| G | BGM | 30–60s×5 | 5 | 750–1500 |
| **合计** | | | **40** | **≈1042–1792** |

> 省 credits 提示：① BGM 占大头，先做 30s loop（减半）；② 不足 10 条的批次若工具强制选「10 条」，可对同一条多出几个变体里挑最佳，或把 D 并进 C 的下一轮重跑。

