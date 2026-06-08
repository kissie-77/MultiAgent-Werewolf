# 观战读心 · ④ 狼队·暴露雷达（god 视角）设计

- 日期：2026-06-08
- 分支（拟）：`feature/wolf-exposure-radar`
- 关联：`docs/superpowers/specs/2026-06-07-belief-insight-b1-b2-design.md`（§8 列为待办的狼队面板 ③/④）
- 范围：**仅 ④ 暴露雷达**。③ 神职猜测矩阵另立项（依赖后端 emit + LLM 产 `god_role_intel`，见 §7）。

## 1. 背景与目标

spec §8 把狼队 ③/④ 面板列为待办，前置条件是「先修上游让狼真正产出数据」。经本轮用真实对局（6p 2 狼、12p 4 狼）核实：

- **③ 神职猜测矩阵**依赖狼的 LLM 自报 `god_role_intel`（含 threat/priority），实测**基本恒空**（`deepseek-v4-flash` 不填 `wolf_camp_delta`），且该计算面板**不进实时流**。→ 需后端改造 + prompt 攻坚，另立项。
- **④ 暴露雷达**——「每只狼有多暴露 / 谁最怀疑它 / 建议姿态」——**可完全从现有 B1 信念矩阵派生**，无需后端或 LLM：一只狼的暴露程度 = 信念矩阵中**该狼这一列**（所有非狼观察者对它的狼概率），这份数据 god 流每帧已下发。

**目标**：纯前端、零后端改动，从现有 `belief_snapshot` 数据派生并实时渲染 god 视角的狼队暴露雷达。范式与 B1/B2 一致（可测逻辑入 `lib/` 纯函数，组件薄壳，真机验证）。

**非目标**：③ 神职猜测矩阵；任何后端/prompt 改动；座位（人类）视角（④ 永不在座位视角出现）。

## 2. 数据来源（均已在 `useGameInsight`）

- `beliefs: BeliefSnapshot[]` —— 当前帧每个**存活**观察者的快照，每条含 `observer_seat` + `first_order[]`（`{target_seat, wolf_probability, reason, note}`，覆盖全体目标）。`insightBeliefs` 每个 `belief_snapshot` 事件整批替换 → 即「当前帧」。
- `players: InsightPlayer[]` —— `{seat, role, camp, alive}`，来自 god_roster + 实时存活态。`camp === "werewolf"` 可靠标识全部狼变体（狼人/白狼/狼王/狼美人/守卫狼/隐狼/血月使徒/梦魇狼），中立（如丘比特 `neutral`）正确排除。

无需改 `store.ts` / `useGameInsight.ts`（数据已具备）。

## 3. 派生逻辑（`frontend/src/lib/wolfExposure.ts`，纯函数，可单测）

```ts
export type WolfStance = "sacrifice" | "bus" | "counter" | "hide" | "push";

export interface WolfSuspector { seat: number; prob: number; }

export interface WolfExposureRow {
  wolfSeat: number;
  role: string;            // 原始 roster 角色名（如 "White Wolf"），组件负责本地化
  exposure: number;        // 0~1，最疑者概率（max）
  topSuspectors: WolfSuspector[];  // 0~2 个，见 §3.2
  stance: WolfStance;
}

// 阈值镜像后端 strategy/wolf/camp_mind.py _stance_from_exposure
export function stanceFromExposure(p: number): WolfStance {
  if (p >= 0.85) return "sacrifice";
  if (p >= 0.60) return "bus";
  if (p >= 0.45) return "counter";
  if (p >= 0.25) return "hide";
  return "push";
}

export function selectWolfExposure(
  beliefs: BeliefSnapshot[] | null,
  players: InsightPlayer[],
): WolfExposureRow[];
```

### 3.1 `selectWolfExposure` 算法
1. 无 `beliefs` 或无 `players` → `[]`。
2. `wolves = players.filter(p => p.camp === "werewolf" && p.alive)`；若空 → `[]`（→ 面板不渲染，§5）。
3. `playerBySeat = Map(seat → player)`。
4. 对每只狼 `W`：构造**暴露列** `column`：遍历 `beliefs` 每条快照 `snap`：
   - 跳过 `snap.observer_seat === W.seat`（自身）。
   - 跳过观察者为狼：`playerBySeat[snap.observer_seat]?.camp === "werewolf"`（队友标 100%「已知队友」，必须排除）。
   - 在 `snap.first_order` 找 `target_seat === W.seat` 的格 → `column.push({ seat: observer_seat, prob: wolf_probability })`。
   - （`beliefs` 只含存活观察者 → 死者天然不计。）
5. `exposure = column.length ? Math.max(...probs) : 0`。
6. `topSuspectors`（§3.2）。
7. `stance = stanceFromExposure(exposure)`。
8. 结果按 `exposure` 降序、`wolfSeat` 升序（同值）排序。

### 3.2 最疑者（共领头规则）
- `sorted = column` 按 `prob` 降序、`seat` 升序。
- 若 `sorted[0]?.prob > 0`：放入 `sorted[0]`；当 `sorted[1] && sorted[1].prob > 0 && sorted[1].prob >= sorted[0].prob - 0.15` 时再放入 `sorted[1]`。最多 2 个。
- 否则 `topSuspectors = []`（组件显示「最疑 —」）。

## 4. 组件（`frontend/src/components/WolfExposurePanel.tsx`，薄壳）

- props：`{ beliefs: BeliefSnapshot[]; players: InsightPlayer[] }`。
- 调 `selectWolfExposure` → 行列表；空 → 返回 `null`（§5）。
- 每行：`P{wolfSeat} {zh角色}` + 进度条（宽 = `exposure*100%`，填充色 `heatColor(exposure)`）+ `formatWolfProb(exposure)` + `最疑 P{x}[,P{y}]`（空时「—」）+ 姿态徽标。
- 姿态文案（狼梗版）：`sacrifice 🩸弃车` / `bus 🚌卖队友` / `counter ⚔️对抗悍跳` / `hide 🙈隐藏` / `push 😎带节奏`（label/emoji 映射放组件内）。
- 角色本地化：复用 `lib/roleCatalog.ts` 的 `roleDisplayName`，对 roster 角色名做去空格归一（`"White Wolf" → "WhiteWolf"`）后查 display_name；未命中回退「狼」。
- 复用 `lib/beliefFormat.ts` 的 `heatColor` / `formatWolfProb`。
- 标题：`🐺 狼队·暴露雷达`。

## 5. 可见性 / 位置 / 边界

- **可见性**：仅在 `canShowIdentities`（`isLLMOnly && showIdentities`）为真时渲染（④ 本质暴露「谁是狼」，与信念矩阵的角色图标一致受同一开关控制）。叠加 InsightDock 既有 god-only 前提——座位视角下 InsightDock 整体不渲染（`GameApp.tsx:183` `insightEnabled && !isSeatView`），故座位视角零泄漏面。
- **位置**：`InsightDock` 桌面 + 移动两处，置于 `VoteIntentionPanel` **之后**（最底部，独立 🐺 狼队区，并为将来 ③ 预留同区位）。
- **空态**：无存活狼 → `selectWolfExposure` 返 `[]` → 组件返回 `null`（整面板不渲染）。
- **死狼**：不显示（`wolves` 已按 `alive` 过滤）。

## 6. 刷新时机

与信念矩阵同频：每个 `belief_snapshot`（`initial` + 每次 `after_speech`）整批替换 `insightBeliefs` → ④ 重算当前帧暴露列。常驻显示全部存活狼，**不**跟随发言人。夜晚/投票阶段无新 belief_snapshot 时，沿用最后一帧（与 B1/B2 行为一致）。

## 7. 与 ③ 的关系（本次不做）

③ 神职猜测矩阵需要：(a) 后端把计算后的 `wolf_camp_minds[seat]`（threat/priority）emit 到 god 流；(b) 让 LLM 稳定产出 `god_role_intel`（prompt/schema 强约束或换模型）。两者均为后端工作且 (b) 结果不确定，故 ③ 单独立项。④ 落地后，③ 可复用本面板的区位与渲染范式。

（附：赛后 `wolf_camp_mind.jsonl` 落盘 bug 已于 `fix/wolf-camp-mind-persistence` 修复合并。）

## 8. 测试

**纯函数单测 `lib/wolfExposure.test.ts`（node vitest）**：
- `stanceFromExposure`：边界 0/.25/.45/.60/.85/1 → 对应 5 档。
- `selectWolfExposure`：
  - 排除狼队友列（队友 100% 不污染暴露）。
  - 排除自身列。
  - `exposure = max`（多观察者取最大）。
  - `topSuspectors` 共领头：单一高者→1 个；两者相差 ≤0.15→2 个；相差 >0.15→1 个；全 0→`[]`。
  - 行按 exposure 降序、seat 升序。
  - 无存活狼 / `beliefs=null` → `[]`。
  - 死者观察者不计（beliefs 只含存活者，构造对应 players.alive）。

**组件薄壳**：无单测（与 `ExposureRadarStrip` 一致），靠 Chrome DevTools/Playwright 真机：起含多狼的 god 局（如 `llm-12p-deepseek` 4 狼），开「显示身份」，断言——面板出现在投票意向下方、行按暴露降序、`NN%` + 姿态徽标随真实信念列变化、关闭「显示身份」时面板消失、0 console error。

## 9. 文件清单

| 文件 | 责任 | 类型 |
|------|------|------|
| `frontend/src/lib/wolfExposure.ts` | `stanceFromExposure` + `selectWolfExposure` + 类型 | 新建 |
| `frontend/src/lib/wolfExposure.test.ts` | 上述纯函数单测 | 新建 |
| `frontend/src/components/WolfExposurePanel.tsx` | god 视角狼队暴露雷达薄壳 | 新建 |
| `frontend/src/components/InsightDock.tsx` | 桌面+移动两处，`canShowIdentities` 时挂在 VoteIntentionPanel 之后 | 改 |

## 10. 风险

- **基线噪声**：默认狼概率（~17–33%）会让低暴露狼也有非零 exposure；共领头 0.15 阈值 + max 语义可缓解，真机确认观感。
- **角色名归一**：roster 角色名带空格（"White Wolf"）与 roleCatalog 键（"WhiteWolf"）不一致，需去空格归一 + 未命中回退「狼」。
- **camp 口径**：依赖 god_roster 的 `camp === "werewolf"`；已用 12p 实测确认覆盖白狼/狼王/狼人，中立丘比特排除。若将来新增非 "werewolf" camp 的狼系角色需同步。
