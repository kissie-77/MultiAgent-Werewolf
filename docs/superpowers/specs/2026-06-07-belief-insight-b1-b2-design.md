# 观战读心·信念矩阵增强（B1 高亮/缩放/百分比 + B2 被怀疑雷达）设计

- 日期：2026-06-07
- 分支：`feature/fe-be-integration`
- 关联：`docs/superpowers/specs/2026-06-06-frontend-backend-integration-design.md`（SSE 观战地基）
- 范围档位：**A 档**（B1 增强 + B2 雷达；狼队面板不做，见 §8）

## 1. 背景与目标

观战读心栏（`InsightDock` → `BeliefMatrixPanel`）当前展示的是 god 视角的 N×N 一阶信念矩阵（每行=一个 agent 对所有人的"狼概率"判断）。经实测与代码分析（后端 `strategy/belief/` + `strategy/contracts/decisions.py`），后端其实维护四类信念结构，但前端只渲染了 B1，且 B1 存在若干缺陷。

**本次目标（A 档）**：在**纯前端、零后端改动**前提下，把实时观战的信念矩阵做扎实：

1. 修掉 B1 矩阵的"当前发言行高亮"硬编码 bug。
2. 按人数自动缩放矩阵，支持 9/12/16 人局。
3. 概率显示从 `.25` 改为 `25%`。
4. 新增 B2「被怀疑雷达」：跟随当前发言人，显示"该 agent 觉得谁在怀疑自己"。

**非目标**：复盘页 `BeliefHeatmap` 不改；狼队"神职猜测矩阵 / 暴露雷达"不做（数据上游未产出，见 §8）；后端不改。

## 2. 数据现状（实测依据）

每个 `belief_snapshot` 事件（god 流）携带 `data = {round, phase, anchor, speaker_id, speaker_name, snapshots[]}`：

- `anchor`：`initial`（讨论开局，`speaker_id=""`）或 `after_speech`（某人发言后，`speaker_id` 为刚发言者）。
- `snapshots[]`：**当帧全部存活 agent 的快照**（6 人活着=6 行，死 2 个=4 行；实测每帧齐全、自洽）。每条 = `{round, phase, anchor, observer_id, observer_seat, vote_intention, first_order[], second_order[], wolf_camp_delta}`。
- `first_order[]`（B1）：`{target_seat, wolf_probability(0~1), reason, note}`，每帧齐全。
- `second_order[]`（B2）：`{observer_seat, suspects_me_as_wolf(0~1), reason, note}`，**实测稀疏**（多数局 0 条，偶尔几条，LLM 偷懒不填）→ 前端必须做空态。

前端取数链路（现状）：`store.connectSpectate` 的 `es.onmessage` 收 `belief_snapshot` → `insightBeliefs = mapBeliefEvent(ev.data)`（= `data.snapshots`，**丢弃了 `speaker_id`、且类型层丢弃了 `second_order`**）→ `useGameInsight` → `InsightDock` → `BeliefMatrixPanel`。

## 3. 当前 B1 的缺陷（本次要修）

| 缺陷 | 位置 | 现状 |
|------|------|------|
| 发言高亮假数据 | `BeliefMatrixPanel.tsx` `isLatestSpeaker` | 永远 `return seat === 2`（mock 残留），高亮永远框 P2 |
| 不随人数缩放 | `BeliefMatrixPanel.tsx` grid | 列宽写死 `minmax(32px,1fr)`、格高 `h-6`、字 `9px`；12/16 人溢出横滚成一团 |
| 概率可读性 | `BeliefMatrixPanel.tsx` | `p.toFixed(2).replace('0.', '.')` → `.25`/`.05`，非直觉 |

## 4. 架构与改动清单

纯前端。新增 2 个文件，修改 4 个文件：

| 文件 | 改动 |
|------|------|
| `frontend/src/lib/beliefFormat.ts`（新） | 纯函数 `matrixScale(n)`、`formatWolfProb(p)` |
| `frontend/src/lib/insightMap.ts` | 新增 `mapSpeakerSeat(data)`；`BeliefSnapshot` 类型补 `second_order?`（见 §5.4） |
| `frontend/src/store.ts` | 新增状态 `insightSpeakerSeat`；`connectSpectate` 的 belief_snapshot 分支同时 set 它 |
| `frontend/src/hooks/useGameInsight.ts` | 返回值新增 `speakerSeat` |
| `frontend/src/components/BeliefMatrixPanel.tsx` | 用 `currentSpeakerSeat` 取代 `isLatestSpeaker`；用 `matrixScale`、`formatWolfProb` |
| `frontend/src/components/ExposureRadarStrip.tsx`（新） | B2 单行雷达组件 |
| `frontend/src/components/InsightDock.tsx` | 透传 `speakerSeat`；在矩阵与投票意向间挂 `ExposureRadarStrip` |

数据流（新增 `speakerSeat`）：

```
belief_snapshot 事件
  └ store.connectSpectate onmessage
       set({ insightBeliefs: mapBeliefEvent(data),
              insightSpeakerSeat: mapSpeakerSeat(data) })   ← 新增
  └ useGameInsight → { beliefs, voteSnapshot, players, speakerSeat }  ← 新增
  └ InsightDock
       ├ BeliefMatrixPanel(currentSpeakerSeat=speakerSeat, ...)        ← 替换假高亮
       └ ExposureRadarStrip(beliefs, speakerSeat, players)            ← 新 B2 strip
```

## 5. 详细设计（按单元）

### 5.1 `lib/beliefFormat.ts`（纯函数，可单测）

```ts
export interface MatrixScale { cell: number; font: number; }

// n = 总座位数（players.length）。设最小格宽下限,超限由调用方允许横滚。
export function matrixScale(n: number): MatrixScale {
  if (n <= 6)  return { cell: 34, font: 10 };
  if (n <= 9)  return { cell: 28, font: 9 };
  if (n <= 12) return { cell: 22, font: 8 };
  return { cell: 17, font: 7 };          // 13–16
}

// 0.25 → "25%"; 0.05 → "5%"; 1 → "100%"; 0.333 → "33%"
export function formatWolfProb(p: number): string {
  return `${Math.round(p * 100)}%`;
}

// 连续热力色,从 BeliefMatrixPanel.getHeatColor 抽出,供矩阵格 + B2 chip 共用。
// p<=0.5: 深蓝→琥珀;p>0.5: 琥珀→暗红。
export function heatColor(p: number): string { /* 见 §5.6 现有 getHeatColor 实现搬运 */ }
```

- `BeliefMatrixPanel` 的 grid 列改为 `auto repeat(N, ${cell}px)`、格高与字号用 `scale.font` 派生（行高 ≈ `font + 14`px），不再写死。最小格宽即 13–16 档的 17px；若 `N*cell + 行头` 仍超面板宽，容器保留 `overflow-x-auto` 兜底（之前确认的方案 ii：可读性优先，允许少量横滚）。
- `formatWolfProb` 用于格内文本。`p===0`/`p===1` 也走同式（`0%`/`100%`）。tooltip 已是 `(p*100).toFixed(0)%`，保持。

### 5.2 `lib/insightMap.ts` — `mapSpeakerSeat`

```ts
// after_speech → 发言人的 observer_seat;initial 或无法解析 → null
export function mapSpeakerSeat(data: any): number | null {
  const sid = data?.speaker_id;
  if (!sid) return null;                       // initial 锚点 speaker_id=""
  const snaps = Array.isArray(data?.snapshots) ? data.snapshots : [];
  const self = snaps.find((s: any) => s?.observer_id === sid);
  return typeof self?.observer_seat === "number" ? self.observer_seat : null;
}
```

- 兜底：`speaker_id` 存在但不在 `snapshots` 中（理论上不该发生）→ 返回 null（不高亮），不抛错。

### 5.3 `store.ts`

- 接口加 `insightSpeakerSeat: number | null`，初值 `null`。
- `connectSpectate`：`disconnectSpectate` 重置时一并清 `insightSpeakerSeat: null`；`onmessage` 中 `belief_snapshot` 分支：
  ```ts
  if (ev.event_type === "belief_snapshot")
    set({ insightBeliefs: mapBeliefEvent(ev.data), insightSpeakerSeat: mapSpeakerSeat(ev.data) });
  ```
- `connectSeat`（人机座位流）：座位流被后端过滤、收不到 belief_snapshot，`insightSpeakerSeat` 维持 null，无需特殊处理（与现状 `insightBeliefs` 行为一致）。

### 5.4 `BeliefSnapshot` 类型补 `second_order`（`api/insightTypes.ts`）

运行时 `snapshots[]` 已含 `second_order`，仅类型层缺。新增：

```ts
export interface SecondOrderCell {
  observer_seat: number;
  suspects_me_as_wolf: number;
  reason: string | null;
  note: string | null;
}
// BeliefSnapshot 增补:
//   second_order?: SecondOrderCell[];
```

`mapBeliefEvent` 不变（原样透传 `data.snapshots`，已带 `second_order`）。

### 5.5 `useGameInsight.ts`

`GameInsight` 接口加 `speakerSeat: number | null`；从 `useGameStore((s) => s.insightSpeakerSeat)` 读出并返回。

### 5.6 `BeliefMatrixPanel.tsx`

- 新增 prop `currentSpeakerSeat: number | null`。
- 删除 `isLatestSpeaker`，所有 `isLatestSpeaker(x)` 替换为 `x === currentSpeakerSeat`（`null` 时不高亮任何行/列）。
- grid 列模板与字号用 `matrixScale(sortedPlayers.length)`。
- 格内概率文本用 `formatWolfProb(p)`（替换 `p.toFixed(2).replace(...)` 那段）。

### 5.7 B2 选择逻辑（纯函数）+ `ExposureRadarStrip.tsx`（薄壳）

**纯函数 `selectExposureRow`（放 `lib/insightMap.ts`，可单测）**：

```ts
export interface ExposureCell { observer_seat: number; suspicion: number; reason: string | null; }

// 取发言人那条 snapshot 的 second_order,按 suspicion 降序;无发言人/无 B2 → []
export function selectExposureRow(
  beliefs: BeliefSnapshot[] | null, speakerSeat: number | null,
): ExposureCell[] {
  if (!beliefs || speakerSeat == null) return [];
  const me = beliefs.find((b) => b.observer_seat === speakerSeat);
  const rows = me?.second_order ?? [];
  return [...rows]
    .map((r) => ({ observer_seat: r.observer_seat, suspicion: r.suspects_me_as_wolf, reason: r.reason }))
    .sort((a, b) => b.suspicion - a.suspicion);
}
```

**组件 `ExposureRadarStrip.tsx`（薄壳，靠真机验证，无单测）**：

- props：`{ beliefs: BeliefSnapshot[]; speakerSeat: number|null }`。
- 调 `selectExposureRow(beliefs, speakerSeat)` → 一行热力 chip：`P{observer_seat} {heatColor()} {formatWolfProb(suspicion)}`，hover 显示 `reason`。复用 `lib/beliefFormat.ts` 的 `heatColor`/`formatWolfProb`。
- 空态：`speakerSeat==null` → `"等待发言…"`；有发言人但无 B2 → `"P{n} 暂未记录被谁怀疑"`。
- 标题含发言人身份：`被怀疑雷达 · P{n}视角`。

### 5.8 `InsightDock.tsx`

- 从 `useGameInsight` 解构出 `speakerSeat`。
- `BeliefMatrixPanel` 传 `currentSpeakerSeat={speakerSeat}`。
- 在 `BeliefMatrixPanel` 与 `VoteIntentionPanel` 之间插入 `<ExposureRadarStrip beliefs={beliefs} speakerSeat={speakerSeat} players={players} />`（桌面与移动两处布局都加）。

## 6. 防作弊与视角

- 本特性仅在 god/观战视角生效（`belief_snapshot` 后端只对 god 流下发；座位流被 `event_visibility` 过滤）。B2 同属 `belief_snapshot`，无新泄漏面。
- 人机座位视角：`insightBeliefs`/`insightSpeakerSeat` 维持 null，`InsightDock` 现有 `if (!beliefs || !voteSnapshot) return null` 已保证整栏不渲染。

## 7. 测试

**测试约束（实测 `frontend/vitest.config.ts`）**：`environment: "node"`、`include: ["src/**/*.test.ts"]`、**无 jsdom / testing-library**。→ 组件无法做渲染单测（`.test.tsx` 不会被收集）。策略：**全部可测逻辑抽成纯函数（lib/`*.ts`）单测，组件做薄壳、靠 Chrome DevTools 真机验证**（与现有 `lib/*.test.ts` + 真机的测试哲学一致）。

**vitest 纯函数单测**

- `lib/beliefFormat.test.ts`：`matrixScale` 各档边界（6/7/9/10/12/13/16 → 期望 {cell,font}）；`formatWolfProb`（0→"0%"、0.05→"5%"、0.333→"33%"、1→"100%"）；`heatColor`（0/0.5/1 各返合法 `rgb(...)`，且 0.5 为两段交界值）。
- `lib/insightMap.test.ts`（补）：`mapSpeakerSeat`（after_speech 取 seat；initial/空 speaker_id 返 null；speaker 不在 snapshots 返 null）；`selectExposureRow`（按 suspicion 降序；speakerSeat=null 返 []；该发言人无 second_order 返 []）。

**Chrome DevTools 真机（组件层验证）**

- 6 人真实局（已有运行环境：后端 8010 + vite 5183）：确认发言高亮跟随真实发言人移动、矩阵数字为 `%`、B2 strip 跟随发言人（有则降序、无则空态）。
- 再开 12 人局：确认矩阵自动缩放、不再溢出成一团。

## 8. 延后：狼队面板（神职猜测矩阵 / 暴露雷达）

后端 `strategy/wolf/camp_mind.py` 已定义 `WolfCampMindModel`（`god_role_intel` 神职猜测 + `exposure_radar` 暴露雷达），但**实测 14 局基本为空**：`wolf_camp_delta` 多为 `{god_role_intel:[], exposure_radar:[]}`，`wolf_camp_mind.jsonl` 的 `god_role_intel` 空、`exposure_radar` cells 空。根因在上游——deepseek-v4-flash 不按 `mind_state_schema_instruction` 填 `wolf_camp_delta`。且完整模型只在赛后 `wolf_camp_mind.jsonl`，直播流只有空 delta。

**结论**：前端 viz 不是瓶颈，先做也长期是空的。列为待办，前置条件=先修上游让狼真正产出该数据。前端设计草案（神职猜测矩阵、暴露雷达条、god 视角 only、空态优先）保留备用。

## 9. 风险

- B2 数据稀疏 → strip 大多数时间是空态（设计已接受，空态文案要友好，不能误导成"无人怀疑"）。
- 16 人档 17px 格 + `100%`（4 字符）偏挤 → 由 `overflow-x-auto` 兜底允许少量横滚（方案 ii）。
- `speaker_id` 与 `observer_id` 格式一致性（均 `player_N`）：`mapSpeakerSeat` 用 `snapshots` 内匹配而非字符串解析，规避格式漂移；附兜底返 null。
- GitNexus 索引自 `f5d1d21` stale：实现前对 `connectSpectate`/`useGameInsight`/`BeliefMatrixPanel` 跑 `gitnexus_impact` 仅作参考，以实读为准。
