# 对局顶栏换皮 + 模型总胜率对比页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对局顶栏(UnifiedGameHeader)按 `D:\AI_werewolf\werewolf_6_6\front_end (2)` 原型的外观换皮(功能零变化),并新增 `/models/overall` 页面以不区分角色的方式条形图对比各模型总胜率。

**Architecture:** 纯前端改动,后端零变更。顶栏在现组件内原地替换 JSX 布局与样式类,所有 hooks/状态机/实况台词逻辑不动;胜率页复用 `getModelsPageData()` 已映射好的 `ModelUsageStat[]`(`win_rate` 为 0-100 整数百分比),用纯函数过滤 `role_name` 为空的聚合条目,div 宽度百分比自绘条形图。

**Tech Stack:** React 18 + TypeScript + Tailwind v4 + react-router v6 + vitest + lucide-react + motion/react。

**Spec:** `docs/superpowers/specs/2026-06-10-header-restyle-and-model-winrate-overall-design.md`

**执行环境注意:** 本仓库可能有并发 agent 共用,建议通过 superpowers:using-git-worktrees 在独立 worktree 执行(基于 `integrate/seatui-fix-godrole` 分支),完成后 ff 合回。所有命令在 `frontend/` 目录运行(`cd frontend`)。

---

### Task 1: `selectOverallStats` 纯函数(TDD)

**Files:**
- Create: `frontend/src/utils/modelOverall.ts`
- Test: `frontend/src/utils/modelOverall.test.ts`

- [ ] **Step 1: 写失败测试**

创建 `frontend/src/utils/modelOverall.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { selectOverallStats, LOW_SAMPLE_THRESHOLD } from "./modelOverall";
import type { ModelUsageStat } from "../api/types";

const stat = (over: Partial<ModelUsageStat>): ModelUsageStat => ({
  model_id: "m",
  display_name: "M",
  role_name: null,
  run_count: 10,
  win_rate: 50,
  avg_mvp: 30,
  ...over,
});

describe("selectOverallStats", () => {
  it("只保留不带角色的聚合条目", () => {
    const rows = selectOverallStats([
      stat({ model_id: "a", display_name: "A（狼人）", role_name: "Werewolf" }),
      stat({ model_id: "a", display_name: "A" }),
      stat({ model_id: "b", display_name: "B（女巫）", role_name: "Witch" }),
    ]);
    expect(rows.map((r) => r.display_name)).toEqual(["A"]);
  });

  it("默认按胜率降序,胜率相同按对局数降序", () => {
    const rows = selectOverallStats([
      stat({ model_id: "a", win_rate: 25, run_count: 4 }),
      stat({ model_id: "b", win_rate: 50, run_count: 2 }),
      stat({ model_id: "c", win_rate: 25, run_count: 59 }),
    ]);
    expect(rows.map((r) => r.model_id)).toEqual(["b", "c", "a"]);
  });

  it("可切换为按对局数排序", () => {
    const rows = selectOverallStats(
      [
        stat({ model_id: "a", run_count: 4 }),
        stat({ model_id: "b", run_count: 59 }),
      ],
      "run_count",
    );
    expect(rows.map((r) => r.model_id)).toEqual(["b", "a"]);
  });

  it("空字符串 role_name 也视为聚合条目", () => {
    const rows = selectOverallStats([stat({ role_name: "" })]);
    expect(rows).toHaveLength(1);
  });

  it("空输入返回空数组", () => {
    expect(selectOverallStats([])).toEqual([]);
  });

  it("暴露样本少阈值常量", () => {
    expect(LOW_SAMPLE_THRESHOLD).toBe(3);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run src/utils/modelOverall.test.ts`
Expected: FAIL — `Cannot find module './modelOverall'`(或等价的模块缺失报错)

- [ ] **Step 3: 写最小实现**

创建 `frontend/src/utils/modelOverall.ts`:

```ts
import type { ModelUsageStat } from "../api/types";

export type OverallSortKey = "win_rate" | "run_count";

/** 对局数低于该阈值的条目在 UI 上标记「样本少」 */
export const LOW_SAMPLE_THRESHOLD = 3;

/**
 * 从模型页数据中取「不区分角色」的聚合条目并排序。
 * 后端 aggregate_model_usage 对每个模型同时产出 (model, role) 与 model 两个粒度,
 * 这里只保留 role_name 为空的聚合粒度(null / undefined / "")。
 */
export function selectOverallStats(
  models: ModelUsageStat[],
  sortKey: OverallSortKey = "win_rate",
): ModelUsageStat[] {
  return models
    .filter((m) => !m.role_name)
    .sort(
      (a, b) =>
        b[sortKey] - a[sortKey] ||
        b.run_count - a.run_count ||
        a.display_name.localeCompare(b.display_name),
    );
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd frontend && npx vitest run src/utils/modelOverall.test.ts`
Expected: PASS(6 个用例全绿)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/modelOverall.ts frontend/src/utils/modelOverall.test.ts
git commit -m "feat(fe): 模型总胜率聚合条目筛选纯函数 selectOverallStats"
```

---

### Task 2: ModelOverallPage 页面组件

**Files:**
- Create: `frontend/src/pages/ModelOverallPage.tsx`

说明:展示型页面,与现有页面一致不写组件单测(项目测试基建只覆盖纯 .ts 函数);视觉风格对齐 `ModelsPage.tsx`(zinc-950 卡片、amber 强调、mono 小字)。

- [ ] **Step 1: 创建页面组件**

创建 `frontend/src/pages/ModelOverallPage.tsx`(完整内容):

```tsx
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiClient } from "../api/client";
import { ModelUsageStat } from "../api/types";
import { ArrowLeft, Trophy } from "lucide-react";
import { motion } from "motion/react";
import PageLoadState from "../components/PageLoadState";
import {
  selectOverallStats,
  LOW_SAMPLE_THRESHOLD,
  OverallSortKey,
} from "../utils/modelOverall";

export default function ModelOverallPage() {
  const [models, setModels] = useState<ModelUsageStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<OverallSortKey>("win_rate");

  useEffect(() => {
    let active = true;
    ApiClient.getModelsPageData()
      .then((data) => {
        if (!active) return;
        setModels((data.models as unknown as ModelUsageStat[]) || []);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setError("命运迷雾阻扰，无法探寻模型总战绩。");
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <PageLoadState variant="loading" loadingText="聚合各模型总体战绩..." />;
  }

  if (error) {
    return (
      <PageLoadState
        variant="error"
        errorText={error}
        onRetry={() => window.location.reload()}
        retryText="重新感应"
      />
    );
  }

  const rows = selectOverallStats(models, sortKey);

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-10 text-center"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-zinc-950 border border-zinc-900 rounded-full text-[9px] font-mono text-amber-500 uppercase tracking-widest mb-4">
          <Trophy className="w-3.5 h-3.5 text-amber-500" />
          OVERALL WIN RATE
        </div>
        <h1 className="text-2xl md:text-3xl font-extrabold uppercase tracking-widest font-sans text-zinc-100">
          模型总胜率对比
        </h1>
        <p className="text-xs text-zinc-500 mt-2">不区分角色，每个模型跨全部对局的总体胜率</p>
      </motion.div>

      <div className="bg-zinc-950/60 border border-zinc-900 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-900 flex justify-between items-center bg-zinc-950">
          <Link
            to="/models"
            className="flex items-center gap-1.5 text-xs font-mono text-zinc-500 hover:text-amber-500 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            返回模型排行榜
          </Link>
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
            排序:
            <select
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as OverallSortKey)}
              className="bg-zinc-900 border border-zinc-800 rounded px-2 py-1 outline-none focus:border-amber-500 transition-colors text-zinc-300"
            >
              <option value="win_rate">按胜率</option>
              <option value="run_count">按对局数</option>
            </select>
          </div>
        </div>

        {rows.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <p className="text-zinc-500 font-mono text-xs tracking-widest">暂无模型出战记录</p>
            <p className="text-zinc-600 text-[10px] font-mono mt-2">请先通过「对局引擎」发起一场对弈</p>
          </div>
        ) : (
          <ul className="divide-y divide-zinc-900/30">
            {rows.map((m, idx) => (
              <li key={m.model_id} className="px-6 py-4 flex items-center gap-4">
                <span className="w-6 text-center font-mono text-xs text-zinc-500 shrink-0">{idx + 1}</span>
                <div className="w-52 shrink-0 min-w-0">
                  <p className="font-bold text-sm text-zinc-200 truncate" title={m.display_name}>
                    {m.display_name}
                  </p>
                  <p className="font-mono text-[10px] text-zinc-500 mt-0.5">
                    {m.run_count} 局 · 平均 MVP {m.avg_mvp.toFixed(1)}
                    {m.run_count < LOW_SAMPLE_THRESHOLD && (
                      <span className="ml-1.5 px-1 py-px rounded-sm bg-zinc-800 text-zinc-400">样本少</span>
                    )}
                  </p>
                </div>
                <div className="flex-1 h-3 bg-zinc-900/80 rounded-sm overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-amber-700 to-amber-400 rounded-sm"
                    style={{ width: `${Math.min(100, Math.max(0, m.win_rate))}%` }}
                  />
                </div>
                <span className="w-14 text-right font-mono font-bold text-amber-500 shrink-0">
                  {m.win_rate}%
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增报错(若仓库存量报错,确认与本文件无关)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ModelOverallPage.tsx
git commit -m "feat(fe): 模型总胜率对比页 ModelOverallPage(不区分角色,条形图)"
```

---

### Task 3: 路由注册 + 模型页入口按钮

**Files:**
- Modify: `frontend/src/components/AppRouter.tsx`(lazy import 区 + `/models` 路由组)
- Modify: `frontend/src/pages/ModelsPage.tsx:92-106`(排行榜标题栏)

- [ ] **Step 1: AppRouter 注册路由**

在 `AppRouter.tsx` 的 lazy import 列表(`ModelComparePage` 之后)加:

```tsx
const ModelOverallPage = React.lazy(() => import("../pages/ModelOverallPage"));
```

在 `/models` 路由组中、`/models/compare` 之后、`/models/:modelId` 之前加(v6 静态段优先级本就高于动态段,放前面是为了可读性):

```tsx
<Route path="/models/overall" element={<LazyRoute><AppLayout><ModelOverallPage /></AppLayout></LazyRoute>} />
```

- [ ] **Step 2: ModelsPage 标题栏加入口**

`ModelsPage.tsx` 中「全网出战模型总序」标题栏整块(从 `<div className="px-6 py-4 border-b ...">` 到其闭合)替换为如下完整内容——在排序区外包一层并加入口链接(`Link`、`ArrowRight` 该文件第 2、5 行已导入):

```tsx
        <div className="px-6 py-4 border-b border-zinc-900 flex justify-between items-center bg-zinc-950">
           <h3 className="text-sm font-sans tracking-widest text-[#eae5db] font-bold">全网出战模型总序</h3>
           <div className="flex items-center gap-4">
             <Link
               to="/models/overall"
               className="flex items-center gap-1 text-xs font-mono text-amber-500/80 hover:text-amber-400 transition-colors whitespace-nowrap"
             >
               总胜率对比
               <ArrowRight className="w-3.5 h-3.5" />
             </Link>
             <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
               排位依据:
               <select 
                 value={sortOrder} 
                 onChange={(e) => setSortOrder(e.target.value as any)}
                 className="bg-zinc-900 border border-zinc-800 rounded px-2 py-1 outline-none focus:border-amber-500 transition-colors text-zinc-300"
               >
                 <option value="win_rate">胜率 (Win Rate)</option>
                 <option value="run_count">对局数 (Run Count)</option>
                 <option value="avg_mvp">平均MVP分 (MVP Score)</option>
               </select>
             </div>
           </div>
        </div>
```

- [ ] **Step 3: 手动冒烟(可跳过,Task 7 统一实跑)**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增报错

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/AppRouter.tsx frontend/src/pages/ModelsPage.tsx
git commit -m "feat(fe): /models/overall 路由与模型页总胜率对比入口"
```

---

### Task 4: AudioControls 增加 compact 紧凑形态

**Files:**
- Modify: `frontend/src/components/AudioControls.tsx:16`(签名)与 `:55-68`(触发按钮)

说明:换皮后顶栏只有 48px 高(`h-12`),现触发按钮 `p-2 md:p-2.5` + `w-5/w-6` 图标(约 44px)会撑破。加 `compact` prop,默认行为不变(首页浮层等场景不受影响)。根容器的 `data-sfx="off"` 保持原样(`clickSfx.test.ts` 依赖该语义)。

- [ ] **Step 1: 改组件签名与触发按钮**

签名改为:

```tsx
export default function AudioControls({
  className,
  compact = false,
}: {
  className?: string;
  compact?: boolean;
}) {
```

触发按钮 className 中的尺寸类抽出按 compact 切换(其余类与配色逻辑不动):

```tsx
      <button
        type="button"
        onClick={() => setOpenWithSound(!open)}
        aria-label="音量设置"
        aria-expanded={open}
        title="音量设置"
        className={`flex items-center justify-center rounded-full border bg-zinc-900/60 backdrop-blur-md shadow-xl cursor-pointer transition-all active:scale-95 ${
          compact ? "p-1.5" : "p-2 md:p-2.5"
        } ${
          audioMuted
            ? "border-red-500/50 text-red-300/90 hover:text-red-200 hover:bg-zinc-800"
            : "border-amber-500/50 text-amber-200/90 hover:text-amber-100 hover:bg-zinc-800"
        }`}
      >
        {audioMuted ? (
          <VolumeX className={compact ? "w-4 h-4" : "w-5 h-5 md:w-6 md:h-6"} />
        ) : (
          <Volume2 className={compact ? "w-4 h-4" : "w-5 h-5 md:w-6 md:h-6"} />
        )}
      </button>
```

- [ ] **Step 2: 类型检查 + 既有测试**

Run: `cd frontend && npx tsc --noEmit && npx vitest run src/lib/clickSfx.test.ts`
Expected: 无新增报错,clickSfx 测试 PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/AudioControls.tsx
git commit -m "feat(fe): AudioControls 紧凑形态 compact prop(适配换皮后 48px 顶栏)"
```

---

### Task 5: UnifiedGameHeader 换皮(只动 JSX,逻辑零变化)

**Files:**
- Modify: `frontend/src/components/UnifiedGameHeader.tsx:2`(import)与 `:379-557`(整个 return JSX)

**硬性约束:** 第 379 行之前的所有逻辑(ROLE_ACTION_DESC、actorInfo、cueFallback、confirmExit 状态机、badge/dayLabel/phaseSubText/isMoon/isWait 计算)一律不改。只替换 return 的 JSX 与 import 行。

- [ ] **Step 1: 修剪 import**

第 2 行 lucide import 中删去不再使用的 `ArrowLeft`、`Flame`、`Skull`(`BrainCircuit`/`MessageCircle`/`Swords` 仍被 actorInfo 逻辑引用,保留):

```tsx
import { Sun, Moon, Hourglass, LogOut, Home, BrainCircuit, MessageCircle, Swords } from "lucide-react";
```

- [ ] **Step 2: 整体替换 return JSX**

把 `return (` 到组件结尾的整个 JSX 替换为(完整内容):

```tsx
  return (
    <div
      className="w-full h-12 bg-black/45 backdrop-blur-md border-b border-zinc-900/60 px-6 py-1.5 shrink-0 flex items-center justify-between relative z-10 shadow-md gap-4"
      data-unified-header
    >
      {/* ═══════════════ LEFT: logo + 标题 ═══════════════ */}
      <div className="flex items-center gap-1 shrink-0">
        <div className="w-1.5 h-5 bg-red-600" />
        <div className="w-0.5 h-5 bg-red-800" />
        <div className="hidden sm:flex flex-col ml-2 font-sans text-[9px] text-zinc-100 uppercase tracking-widest font-black leading-tight">
          <span>狼人杀神圣审判厅</span>
          <span className="text-[8px] text-zinc-500">{gameState.winner ? "已结案" : "对决轮转中"}</span>
        </div>
      </div>

      {/* ═══════════════ CENTER: 石碑法阵框(阶段 + 实况) ═══════════════ */}
      <div className="flex items-center min-w-0 flex-1 justify-center overflow-hidden">
        {badge ? (
          <div
            className="flex items-center gap-4 bg-black/55 border border-zinc-800/50 px-6 py-1 rounded relative shadow-[0_2px_4px_rgba(0,0,0,0.4)] max-w-full"
            style={{ clipPath: "polygon(0 0, 100% 0, 97% 100%, 3% 100%)" }}
            data-live-cue={actorInfo?.cueType ?? undefined}
          >
            {/* 阶段图标 */}
            {isMoon ? (
              <div className="w-7 h-7 rounded-full bg-black border-2 border-[#ef4444] flex items-center justify-center text-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)] shrink-0">
                <Moon className="w-4 h-4 fill-red-500 animate-pulse" />
              </div>
            ) : isWait ? (
              <div className="w-7 h-7 rounded-full bg-black border-2 border-zinc-600 flex items-center justify-center text-zinc-300 shrink-0">
                <Hourglass className="w-4 h-4 animate-spin" style={{ animationDuration: "3s" }} />
              </div>
            ) : (
              <div className="w-7 h-7 rounded-full bg-black border-2 border-yellow-500 flex items-center justify-center text-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)] shrink-0">
                <Sun className="w-4 h-4 animate-spin-slow" />
              </div>
            )}

            {/* 日期 + 阶段副标 */}
            <div className="flex flex-col shrink-0">
              <span className="font-serif font-black text-xs text-zinc-100 tracking-wider whitespace-nowrap">
                {dayLabel}
              </span>
              {phaseSubText && (
                <span className="font-mono text-[9px] text-[#eab308]/90 tracking-widest font-black uppercase whitespace-nowrap">
                  {phaseSubText}
                </span>
              )}
            </div>

            {/* 分隔 + 实况台词(现有 actorInfo / cueFallback 文案原样) */}
            {(actorInfo || cueFallback) && (
              <>
                <div className="w-px h-6 bg-zinc-700 shrink-0" />
                <div className="flex flex-col min-w-0 text-left">
                  <span
                    className={`font-mono text-[8px] text-red-500 font-black tracking-widest uppercase ${
                      actorInfo?.cueType === "thinking" ? "animate-pulse" : ""
                    }`}
                  >
                    — {actorInfo
                      ? actorInfo.cueType === "thinking"
                        ? "心证推演"
                        : actorInfo.cueType === "acting"
                        ? "神职行动"
                        : "法庭陈词"
                      : "法庭实况"} —
                  </span>
                  <p className="font-sans text-xs text-[#e0e0e0] font-black tracking-[0.14em] whitespace-nowrap leading-tight">
                    {actorInfo ? actorInfo.label : cueFallback}
                    {(actorInfo || phase !== "GAME_OVER") && <BreathingDots />}
                  </p>
                </div>
              </>
            )}
          </div>
        ) : (
          <span className="font-mono text-xs text-zinc-500 italic tracking-wider">
            {phaseSubText || (phase === "ROLE_CHOICE" && "宿命契约抉择") || "等待入场"}
          </span>
        )}
      </div>

      {/* ═══════════════ RIGHT: 文字按钮 + 存活统计 + 音量 ═══════════════ */}
      <div className="flex items-center gap-3 shrink-0">
        {/* 返回上一级 */}
        <button
          type="button"
          onClick={() => {
            soundManager.playUi("ui_click");
            window.history.back();
          }}
          className="h-7 px-2.5 rounded border border-zinc-800 transition-all duration-200 bg-zinc-950/30 hover:bg-zinc-900/50 text-zinc-400 text-[10px] font-mono hover:text-zinc-200 uppercase tracking-widest cursor-pointer whitespace-nowrap flex items-center gap-1.5"
        >
          返回上一级
        </button>

        {/* 回到主界面 */}
        <button
          type="button"
          onClick={() => {
            soundManager.playUi("ui_click");
            window.location.href = "/home";
          }}
          className="h-7 px-2.5 rounded border border-indigo-900/60 transition-all duration-200 bg-indigo-950/30 hover:bg-indigo-900/40 text-blue-200 text-[10px] font-mono hover:text-white uppercase tracking-widest cursor-pointer whitespace-nowrap flex items-center gap-1.5"
        >
          <Home className="w-3.5 h-3.5" />
          回到主界面
        </button>

        {/* 存活 / 死亡统计(参考版两行小字) */}
        <div className="text-right font-mono text-[9.5px] leading-tight hidden md:block">
          <div className="text-yellow-500 font-extrabold uppercase tracking-wider">
            存活已降临: {gameState.players.filter((p) => p.isAlive).length}名
          </div>
          <div className="text-red-600 font-black uppercase tracking-wider mt-0.5">
            已被撕咬放逐: {gameState.players.filter((p) => !p.isAlive).length}名
          </div>
        </div>

        {/* 退出游戏(二次确认状态机原样保留) */}
        <button
          type="button"
          onClick={() => {
            if (confirmExit) {
              soundManager.playUi("ui_submit");
              if (onExit) void onExit();
              else exitGame();
              setConfirmExit(false);
            } else {
              soundManager.playUi("ui_error");
              setConfirmExit(true);
            }
          }}
          title={confirmExit ? "再次点击确认退出" : "退出游戏"}
          className={`h-7 px-2.5 rounded border text-[10px] font-sans font-bold tracking-wider cursor-pointer flex items-center gap-1 transition-all duration-200 whitespace-nowrap ${
            confirmExit
              ? "border-red-500 bg-red-600 text-white shadow-[0_0_12px_rgba(239,68,68,0.4)] animate-pulse"
              : "border-red-900/60 bg-red-950/30 hover:bg-red-900/40 text-red-100 hover:text-white"
          }`}
        >
          <LogOut className="w-3 h-3" />
          <span>{confirmExit ? "二次点击确认退出" : "退出游戏"}</span>
        </button>

        {/* 音量控件(紧凑形态) */}
        <AudioControls compact />
      </div>
    </div>
  );
});
```

- [ ] **Step 3: 类型检查 + 全量测试**

Run: `cd frontend && npx tsc --noEmit && npm test`
Expected: 无新增类型错误;vitest 全绿(顶栏无组件级测试,回归靠纯函数测试与编译)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/UnifiedGameHeader.tsx
git commit -m "feat(fe): 对局顶栏按 front_end(2) 原型换皮(细线石碑风,功能不变)"
```

---

### Task 6: 全量验证(lint + test + build)

**Files:** 无新改动,验证性任务。

- [ ] **Step 1: lint**

Run: `cd frontend && npm run lint`
Expected: eslint 与 tsc 均无新增报错(若有存量报错,确认与本次改动文件无关)

- [ ] **Step 2: 全量测试**

Run: `cd frontend && npm test`
Expected: 全绿,含新增 `modelOverall.test.ts` 6 用例

- [ ] **Step 3: 生产构建**

Run: `cd frontend && npm run build`
Expected: 构建成功,无报错

- [ ] **Step 4: 如有遗漏改动则补提交**

```bash
git status --short  # 应只剩仓库原有的未跟踪文件
```

---

### Task 7: 实跑冒烟验证(对照 spec 验收标准)

**Files:** 无代码改动;需要本地起前后端。

- [ ] **Step 1: 启动前后端**

```bash
# 终端 1(仓库根目录)
OBS_READY_REQUIRE_LLM=0 uv run werewolf-api --port 8010
# 终端 2
cd frontend && npm run dev
```

- [ ] **Step 2: 验收胜率页**

浏览器(或 Playwright MCP)打开 `http://localhost:5173/models`:
- 标题栏出现「总胜率对比 →」入口,点击跳 `/models/overall`;
- 页面只显示**不带角色后缀**的模型条目(无「(狼人)」「(女巫)」等);
- 条形图宽度与胜率一致;排序切换「按胜率/按对局数」生效;
- 对局数 < 3 的行显示「样本少」灰标;
- 无对局数据时显示空态文案。

- [ ] **Step 3: 验收顶栏**

发起一局 demo 对局(首页 → 对局引擎,demo 阵容即可),检查顶栏:
- 整条高 48px 细线风格:左侧红双竖条 + 「狼人杀神圣审判厅」;中央石碑梯形框含阶段图标/日期/副标/实况台词 + 呼吸点;右侧「返回上一级」「回到主界面」「存活已降临/已被撕咬放逐」「退出游戏」文字按钮 + 紧凑音量图标;
- 鎏金 ALIVE/DEAD 框与金框图标按钮已不存在;
- 功能回归:实况台词随阶段滚动;音量浮层可开合调节;退出第一次点击变红脉冲「二次点击确认退出」,4 秒未点自动复原,二次点击真正退出;返回/主页可跳转;按钮点击有音效;
- 与 `D:\AI_werewolf\werewolf_6_6\front_end (2)` 顶栏外观风格一致(可起参考工程对照截图)。

- [ ] **Step 4: 截图留档(可选)**

Playwright MCP 截取 `/models/overall` 与对局顶栏各一张,存仓库根(与现有 `multimodel-*.png` 同位置)或 `docs/reports/` 引用。
