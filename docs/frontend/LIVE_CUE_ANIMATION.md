# 实时阶段占位符（LiveCue）— 动画接入说明

> **受众**：前端动画 / 动效同学  
> **数据源**：SSE `GET /api/v1/games/{run_id}/stream` → `gameReducer` → `gameState.liveCue`  
> **最后更新**：2026-06-07

---

## 1. 怎么读状态（推荐）

### 1.1 React Store（主入口）

```ts
import { useGameStore } from "../store";

const liveCue = useGameStore((s) => s.state?.liveCue);
const phase = useGameStore((s) => s.state?.phase);
const currentSpeakerId = useGameStore((s) => s.state?.currentSpeakerId);
```

对局页：`/game?run_id=xxx`（`view=god` 旁观默认；`view=seat&seat=N&token=...` 人机座位）。

### 1.2 DOM 锚点（可选，便于 CSS / GSAP 选择器）

工程里已挂载极简占位 DOM，带 `data-live-cue` 属性，可直接 query：

| 选择器 | 含义 |
|--------|------|
| `[data-live-cue="thinking"]` | 思考中（左下角 `SpeechConsole`） |
| `[data-live-cue="sheriff-stage"]` | 警长阶段 |
| `[data-live-cue="night-sub-phase"]` | 夜间子环节 |
| `[data-live-cue="night-skill"]` | 当前夜间技能行动角色 |

属性示例：

```html
<div data-live-cue="thinking" data-seat="3" data-context="day_speech">...</div>
<div data-live-cue="night-skill" data-seat="4" data-role="Witch" data-sub-phase="witch_decide">...</div>
```

组件位置：`frontend/src/components/LiveCueAnchors.tsx`、`SpeechConsole.tsx`。

---

## 2. `LiveCue` 结构

定义见 `frontend/src/types.ts`。

```ts
interface LiveCue {
  /** 仅在有角色正在等 LLM/人类输入时为非 null；发言开始后清空 */
  thinking: {
    seat: number;
    playerName: string;
    role: string;
    context: ThinkingContext;
  } | null;

  /** 夜间时间轴粗粒度步骤（公开事件） */
  nightSubPhase: string | null;

  /** 某角色正在执行夜间技能（占位，不暴露技能结果） */
  nightSkill: {
    seat: number;
    playerName: string;
    role: string;
    subPhase: string | null;
  } | null;

  /** 警长竞选子阶段 */
  sheriffStage: "campaign" | "vote" | null;
}
```

### `ThinkingContext` 枚举（与后端 `actor_thinking.data.context` 一一对应）

| 值 | 场景 |
|----|------|
| `day_speech` | 白天讨论下一位发言前 |
| `sheriff_speech` | 警长竞选发言前 |
| `sheriff_vote` | 警长投票前 |
| `werewolf_chat` | 狼队夜聊某位狼发言前 |
| `night_skill` | 夜间技能决策（人机等待输入时） |
| `general` | 其它 |

中文标签（可选展示）：`frontend/src/lib/liveCue.ts` → `THINKING_CONTEXT_LABEL`。

---

## 3. 后端 SSE 事件 → 状态变化

所有事件经 `reduceEvent()`（`frontend/src/lib/gameReducer.ts`）折叠进 `gameState`。

### 3.1 思考占位 `liveCue.thinking`

| 事件 | 行为 |
|------|------|
| `actor_thinking` | 设置 `thinking`，**清空** `currentSpeakerId` |
| `player_speech` | **清空** `thinking`，设置 `currentSpeakerId`，写入发言日志 |
| `sheriff_candidate_speech` | 同上 + `sheriffStage = "campaign"` |
| `player_discussion` | 狼队夜聊发言（`speechContext: "wolf"`） |
| `sheriff_elected` / `game_ended` | 清空 `thinking` |

`actor_thinking` 载荷示例：

```json
{
  "event_type": "actor_thinking",
  "phase": "day_discussion",
  "round_number": 2,
  "data": {
    "player_id": "player_3",
    "player_name": "P3",
    "role": "Seer",
    "context": "day_speech"
  },
  "visible_to": null
}
```

**时序（白天）**：

```
actor_thinking(seat=3)  →  thinking 有值，左下角应显示「3号思考中」
        ↓ （LLM 耗时 = 自然思考时长）
player_speech(seat=3)     →  thinking 清空，currentSpeakerId=3，播放发言动效
        ↓
actor_thinking(seat=4)  →  下一位思考…
```

### 3.2 警长竞选 `liveCue.sheriffStage`

| 事件 | `sheriffStage` | `phase` |
|------|----------------|---------|
| `sheriff_campaign_started` / `phase_changed`（`stage: "campaign"`） | `"campaign"` | `DAY_SHERIFF_RUN` |
| `phase_changed`（`stage: "vote"`） | `"vote"` | `DAY_SHERIFF_RUN` |
| `sheriff_candidate_speech` | 保持 `"campaign"` | `DAY_SHERIFF_RUN` |
| `sheriff_elected` / 进入白天讨论投票 | `null` | — |

警长发言日志：`speechLogs[].speechContext === "sheriff"`。

### 3.3 夜间占位 `nightSubPhase` + `nightSkill`

| 事件 | 行为 |
|------|------|
| `sub_phase`（`data.name`） | 更新 `nightSubPhase`，清空 `nightSkill`，并映射 UI `phase` |
| `role_acting`（`context: "night_skill"`） | 设置 `nightSkill`，清空 `thinking` |
| `phase_changed`（离开 `night`） | 清空夜间相关 cue |

`sub_phase` 名称与 UI 阶段映射：

| `data.name` | `gameState.phase` | 中文（`NIGHT_SUB_PHASE_LABEL`） |
|-------------|-------------------|--------------------------------|
| `pre_wolf` | `NIGHT_WOLF` | 预狼行动 |
| `werewolf_kill` | `NIGHT_WOLF` | 狼队刀人 |
| `werewolf_chat` | `NIGHT_WOLF` | 狼队夜聊 |
| `witch_decide` | `NIGHT_WITCH` | 女巫用药 |
| `seer_check` | `NIGHT_SEER` | 神职查验 |

`role_acting` 载荷示例：

```json
{
  "event_type": "role_acting",
  "phase": "night",
  "data": {
    "player_id": "player_4",
    "player_name": "Witch",
    "role": "Witch",
    "context": "night_skill",
    "sub_phase": "witch_decide"
  },
  "visible_to": ["player_4"]
}
```

---

## 4. 旁观 vs 座位视角（可见性）

| 信号 | god 旁观 | seat 座位流 |
|------|----------|-------------|
| `actor_thinking` | ✅ 全部 | ✅ 全部（公开） |
| `sub_phase` | ✅ | ✅ |
| `role_acting` | ✅ 全部 | ⚠️ 仅**自己座位**的行动（防剧透） |
| `sheriff_candidate_speech` | ✅ | ✅ |
| `awaiting_input` | ✅（含在流里） | ✅ 仅本人（操作面板，非 LiveCue） |

动画同学在 **god 视角** 可做全员夜间技能占位；**seat 视角** 夜间只能可靠依赖自己的 `role_acting` + 公开的 `sub_phase`。

---

## 5. 与现有 UI 字段的配合

| 字段 | 用途建议 |
|------|----------|
| `liveCue.thinking` | **思考动效**（头像脉冲、全员低头等）；**仅 thinking 非空时展示** |
| `currentSpeakerId` | **发言动效**（聚光灯、嘴型、字幕）；thinking 清空后才应亮起 |
| `phase` | 大背景（日/夜、警长、投票）；夜间细粒度可看 `nightSubPhase` |
| `speechLogs` | 历史发言；`speechContext` 区分 `day` / `sheriff` / `wolf` |

注意：`ThreeCanvas` 目前仍主要读 `currentSpeakerId`，**尚未**接 `liveCue.thinking`——思考动效需要你们新接。

---

## 6. 动画挂载示例（伪代码）

```tsx
const { thinking, nightSkill, sheriffStage, nightSubPhase } = liveCue ?? {};

// 思考：仅 thinking 存在时
useEffect(() => {
  if (!thinking) return hideThinkingFX();
  showThinkingFX({
    seat: thinking.seat,
    context: thinking.context, // 决定用哪套素材
  });
  return () => hideThinkingFX();
}, [thinking?.seat, thinking?.context]);

// 发言：currentSpeakerId 变化时
useEffect(() => {
  if (currentSpeakerId == null) return;
  playSpeechFX(currentSpeakerId);
}, [currentSpeakerId]);

// 夜间技能占位
useEffect(() => {
  if (!nightSkill) return clearNightSkillFX();
  playNightSkillPlaceholder(nightSkill);
}, [nightSkill?.seat, nightSkill?.role, nightSkill?.subPhase]);

// 警长阶段 banner
useEffect(() => {
  if (sheriffStage === "campaign") showSheriffCampaignBanner();
  else if (sheriffStage === "vote") showSheriffVoteBanner();
  else hideSheriffBanner();
}, [sheriffStage]);
```

---

## 7. 回放 vs 实时对局

| 场景 | `actor_thinking` | `sub_phase` / `role_acting` | 建议 |
|------|------------------|----------------------------|------|
| **新开 live 对局** | ✅ 有 | ✅ 有 | 完整动效 |
| **已结束对局日志回放** | ❌ 旧日志无此事件 | ✅ 有 | 思考动效需降级或跳过 |
| **无 `run_id` 旧 demo** | ❌ | ❌ | 不走 SSE，勿依赖 LiveCue |

回放时 `spectateLog.ts` 对事件有额外延时（便于看清节奏）：

- `actor_thinking`：700ms  
- `sub_phase`：400ms  
- `role_acting`：500ms  
- `sheriff_campaign_started`：450ms  

---

## 8. 相关源码索引

| 文件 | 说明 |
|------|------|
| `frontend/src/types.ts` | `LiveCue`、`ThinkingContext` 类型 |
| `frontend/src/lib/liveCue.ts` | 中文标签、初始值 |
| `frontend/src/lib/gameReducer.ts` | SSE → 状态折叠逻辑 |
| `frontend/src/store.ts` | `connectSpectate` / SSE 订阅 |
| `frontend/src/components/SpeechConsole.tsx` | 左下角思考占位 DOM |
| `frontend/src/components/LiveCueAnchors.tsx` | 右下警长/夜间锚点 DOM |
| `src/llm_werewolf/game_runtime/types/enums.py` | `ACTOR_THINKING`、`SUB_PHASE` 等 |
| `src/llm_werewolf/agent_team/communication/information_hub.py` | 发言前发 `actor_thinking` |

---

## 9. 联调检查清单

- [ ] 后端 + 前端均已重启  
- [ ] 从首页新开一局，URL 带 `run_id`  
- [ ] 白天：每位发言前左下角出现思考文案，发言后消失  
- [ ] 警长局：右下角出现「警长阶段 · 竞选发言」，候选人发言进日志  
- [ ] 夜间：右下角依次出现「夜间环节 · 女巫用药」等 + 「技能占位 · N号 Role」  
- [ ] 浏览器控制台：`useGameStore.getState().state?.liveCue` 随事件变化  

---

## 10. 尚未接入（勿假设已有）

- `CastSkillOverlay` 在 live 对局默认**不渲染**（`GameApp` 中 `!isLiveRun`）  
- 技能**结果**（查验阵营、刀口等）多数为私有事件，占位层**故意不暴露**  
- `ThreeCanvas` 思考态动效需自行接 `liveCue.thinking`  

如有新环节需要占位，请后端补 `actor_thinking` / `sub_phase` 事件，前端在 `gameReducer` 扩展即可。
