# 人机座位视图修复 + 角色美术接线 设计 Spec

> **模块**：frontend + interface(api)
> **状态**：draft（待用户评审）
> **最后更新**：2026-06-06
> **关联代码**：`frontend/src/{store.ts,lib/gameReducer.ts,utils/roles.ts,components/*,pages/GameApp.tsx}`、`src/llm_werewolf/interface/api/routes/actions.py`、`src/llm_werewolf/interface/api/services/game_sessions.py`
> **关联测试**：`frontend/src/**/*.test.ts`、`tests/interface/`
> **分支**：`feature/fe-be-integration`

---

## 1. 目标（一句话）

让**人机对战座位视图**像纯 LLM 观战一样渲染（玩家卡牌 + 发言气泡 + 事件时间线），并让**设置页底牌**与**对局内立绘**对全部 22 个角色精准对应美术资源——**复用现有观战渲染，只改数据契约与资源接线，不重做页面**。

## 2. 架构（2–3 句）

座位视图 `connectSeat` 已经和观战 `connectSpectate` 走同一套组件（`GameApp` 同款 `CardDeck`/`SpeechConsole`/事件 UI）与同一个纯函数 `reduceEvent`。三个 bug 的根因都在**数据**而非渲染：(a) 后端 seat 快照不下发名单、(b) reducer 缺 `isUser` 标记与公开对话事件的 case、(c) 美术资源没部署进 `public/` 且 `roles.ts` 把特殊角色一律 fallback。方案因此是「后端发**脱敏名单** + reducer 补字段 + 资源部署进 `public/` 并重写映射」。

## 3. 问题与根因（实测，高置信）

| # | 现象 | 根因（file:line） |
|---|------|------|
| ① | 座位卡牌栏全空 | seat 快照不带 roster：`actions.py:262-271` 仅 `view=='god'` 注入 `snap["roster"]`；`gameReducer.ts:50-58` 只从 `ev.roster` 填 `players[]` → seat 下 `players=[]` → `CardDeck` 空。**连锁**：`ControlPanel` 取不到 `isUser` 玩家 → 误判 `isDead=true` → 错弹「你已死/观战」红条。 |
| ② | 设置页底牌与角色不符 | 设置页 `<img src={getRoleImage(userRole)}>`（`GameSetup.tsx ~L475`）走 `/material/`；`public/material/` 只有 5 张图，`roles.ts:30-39,52-63` 把白痴/守卫/长老/骑士/魔术师/丘比特/乌鸦/守墓人/盗贼/恋人**全 fallback 到 `villiger.png`**，8 种狼全 `wolf.png`。源目录 `frontend/{material,tarot}/` 现已各 22/22 齐全，但**未部署进 `public/`**（`public/tarot/` 根本不存在）。 |
| ③ | 座位中心区无对话 | 两层。**Layer A（设计正确，不改）**：狼人夜聊属狼队可见，非狼人类座位流**正确地**收不到——god 视角是绕过过滤。**Layer B（真 bug）**：公开发言 `player_speech`、`sheriff_candidate_speech` 等（`visible_to=None`）其实到了 seat 流，但 `reduceEvent` 只有 `player_speech`/`player_discussion` 的 case（`gameReducer.ts:60-61`），**无 `sheriff_candidate_speech` case**（故「纯文本记录」恒为 0）；且 `players[]` 空时发言只能显示占位名 `P{seat}`（`gameReducer.ts:68`）。 |

## 4. 设计

### 4.1 后端：脱敏 seat 名单（修 ①，使能 ③）

`god_roster.json` 每条为 `{seat, name, role, camp, is_alive}`（`game_sessions.py:113-119`）。新增脱敏函数，供 seat 视图首帧快照使用：

- 新增 `_redact_roster_for_seat(roster, seat) -> list[dict]`：对每条目，**始终**保留 `seat`/`name`/`is_alive`；`role`/`camp` 仅在以下情形保留，否则置 `null`：
  1. 该条目就是人类本人座位（`entry.seat == seat`）；
  2. **人类本人是狼**（本人 `camp` 为狼阵营）且该条目也是狼阵营 → 露狼队友（标准狼人杀狼队互知）。
- `_initial_snapshot(run_dir, view, seat)` 增参 `seat`：`view=='god'` 维持全量；`view=='seat'` 时 `snap["roster"] = _redact_roster_for_seat(_load_god_roster(...), seat)`。
- `_stream_events` 调用处把 `seat` 传入 `_initial_snapshot`（`actions.py:287`）。

> 阵营字符串以 `god_roster.json` 实际 `camp` 值为准（实现期确认，疑似 `werewolf`/`villager`）。**绝不**下发非己非狼队友的 `role`/`camp` —— 这是反作弊红线。事件流可见性（`event_visible_for`）已正确，**不动**。

### 4.2 前端 reducer：`isUser` 标记 + 隐藏角色 + 公开对话 case（修 ①③）

`reduceEvent`（`gameReducer.ts`）：

- **snapshot case**：读可选 `ev.selfSeat`，`isUser: r.seat === ev.selfSeat`；`role: r.role ?? ""`（脱敏后为 `null` → 空串 → UI 显示「秘匿」）。`connectSeat` 的 snapshot 监听器注入 `selfSeat`：`reduceEvent(cur, { ...snap, event_type:'snapshot', selfSeat: seat })`（`store.ts:502`）。观战 `connectSpectate` 不传 `selfSeat`，行为不变。
- **新增公开对话 case**：`sheriff_candidate_speech`（及其它到达 seat 流的公开发言类型）复用 `player_speech` 同款逻辑入 `speechLogs`。
- **新增事件时间线**（用户选定「加事件时间线旁白」）：`GameState` 增 `eventLog: { round:number; phase:string; type:string; message:string }[]`；`reduceEvent` 对**任何带 `message` 的事件**追加一条（去重相邻重复），供座位/观战中心区在无人发言时（尤其夜晚）始终有内容。`SpeechConsole`/中心区消费 `eventLog` 渲染时间线。

### 4.3 前端：修「假死」面板（修 ①连锁）

`ControlPanel`（`~L281-282,383-387`）：`isDead` 仅在**确有本人玩家**且其 `isAlive===false` 时为真；`players` 为空或找不到本人时**不**判死（默认存活/等待名单）。避免活人被误显示为观战者。

### 4.4 美术：部署 `public/` + 重写 `roles.ts`（修 ②）

- **部署**：把 `frontend/material/*`、`frontend/tarot/*` 复制进 `frontend/public/material/`、`frontend/public/tarot/`，**统一改名为对齐后端角色名的 PascalCase**（`Werewolf.png`/`WolfBeauty.png`/`Cupid.png`/`Knight.png`…），修 `villiger→villager`。源目录保持不动。两个 `public/` 子目录用**同一套规范文件名**。
- **`roles.ts` 重写**：
  - `getRoleImage(role)`：全 22 角色，英文 roster 名 + 中文显示名双键 → `/material/<PascalCase>.png`；未知角色按 `wolf`/`狼` 兜底狼图，否则兜底 `Villager`。（对局内立绘）
  - 新增 `getTarotImage(role)`：同样 22 角色双键 → `/tarot/<PascalCase>.png`。（设置页底牌）
- **接线**：`GameSetup.tsx` 底牌 `<img>` 改 `getTarotImage(userRole)`；`SkillReleaseModal` 硬编码 5 角色塔罗表改调 `getTarotImage()`；`CardDeck` 立绘维持 `getRoleImage()`。

### 4.5 数据流（座位视图，修复后）

```
后端 stream?view=seat&seat=N&token=…
  └─ snapshot 帧：snap + 脱敏 roster（本人+狼队友露角色，余者 role=null）
  └─ 事件帧：仅 visible_to=None 公开事件 + 本人可见事件（过滤不变）
前端 connectSeat
  └─ snapshot → reduceEvent({...snap, selfSeat:N}) → players[]（本人 isUser，余者秘匿）
  └─ onmessage → ingestSeatEvent（awaiting_input 驱动 HumanInputPanel）｜否则 reduceEvent
        ├─ player_speech / sheriff_candidate_speech → speechLogs（气泡）
        ├─ 任何带 message 事件 → eventLog（时间线旁白）
        └─ player_died / sheriff_elected / game_ended → 既有 case
渲染（GameApp，与观战同款组件）：CardDeck（6 人卡牌+本人徽标）｜SpeechConsole（气泡+时间线）｜HumanInputPanel（轮到本人时弹层）
```

## 5. 错误处理 / 边界

- 脱敏函数对缺失 `god_roster.json`（早期/异常）返回 `None` → seat 快照无 roster（退化为今天行为，不崩）。
- `seat` 超界或与 token 不符：沿用现有 stream/token 校验，不在本 spec 扩展。
- reducer 对未知 `role`（脱敏 `null`）渲染「秘匿」，不取图或取通用背板，**不报错**。
- 美术缺图（理论上已不缺）：`getRoleImage`/`getTarotImage` 兜底链（狼→狼图，余→Villager），`<img onError>` 可选兜底。

## 6. 测试策略

- **reducer 纯函数单测**（`gameReducer.test.ts`，新增）：脱敏 roster→`players[]` 且本人 `isUser=true`、他人 `role` 隐藏；`sheriff_candidate_speech`→`speechLogs`；任意带 message 事件→`eventLog`（相邻去重）。
- **roles 单测**（`roles.test.ts`，新增）：22 角色 `getRoleImage`/`getTarotImage` 均解析到对应 `/material|/tarot/<PascalCase>.png`；中文键与英文键一致；狼/未知兜底。
- **后端单测**（`tests/interface/`）：`_redact_roster_for_seat` —— 村民人类只露本人；狼人类露全部狼队友、不露神民；缺名单返回空/None。复用既有 `event_visible_for` 反作弊组合测试，确认 seat 流不含他人私密事件。
- **Playwright 真机回归**：开人机局 → 左栏 6 张卡牌且本人有徽标、无「假死」红条；设置页逐角色切换底牌图与角色名对得上（含白痴≠村民）；白天发言渲染气泡；夜晚中心区有事件时间线。

## 7. 不在本次范围（YAGNI）

- 真·BYO-key（前端 key 驱动 AI）—— 另议。
- 清理遗留 `/api/game/*` mock 控件（`ControlPanel`/`SkillBar`/`CardDeck` 旧技能按钮）—— 可后续单独清理。
- 新增/重绘美术资源 —— 资源已齐全，仅部署 + 接线。

## 8. 风险 / 待确认

- `camp` 字符串实际值（狼阵营判定）—— 实现期读 `god_roster.json` 确认。
- 文件名统一 PascalCase 后，确认无其它代码硬编码旧 `/material/<lowercase>.png` 路径（除 `roles.ts`/`SkillReleaseModal`）。
- GitNexus 索引自 `f5d1d21` 起 stale；按 CLAUDE.md，改符号前对 `reduceEvent`、`_initial_snapshot` 跑 `gitnexus_impact`。
