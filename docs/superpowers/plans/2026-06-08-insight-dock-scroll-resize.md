# InsightDock 滚动修复 + 左右拖拽拓宽 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复观战读心栏（InsightDock）内容被裁剪无法滚动到底部（狼队雷达）的 bug，并新增桌面左边缘拖拽拓宽面板的能力。

**Architecture:** 纯前端、零后端。垂直滚动修复 = 桌面内容容器 `h-full` → `flex-1 min-h-0`（+`w-full`），移动端补 `min-h-0`。拓宽 = 组件 `width` state + 左缘拖拽手柄（`stopPropagation` 避开 framer-motion 移动拖拽），宽度夹取逻辑抽到 `lib/dockWidth.ts` 纯函数（vitest 单测）。

**Tech Stack:** React 19 + TypeScript + framer-motion(`motion/react`) + Vite + Vitest（`environment: node`）。

**关联 spec：** `docs/superpowers/specs/2026-06-08-insight-dock-scroll-resize-design.md`

**测试命令：** 工作目录 `frontend/`。单测 `npm test`；类型检查 `npm run lint`（`tsc --noEmit`）；构建 `npm run build`。

---

## 文件结构

| 文件 | 责任 | 类型 |
|------|------|------|
| `frontend/src/lib/dockWidth.ts` | `clampDockWidth` + 常量 | 新建 |
| `frontend/src/lib/dockWidth.test.ts` | 单测 | 新建 |
| `frontend/src/components/InsightDock.tsx` | 滚动修复 + 宽度 state + 左缘拖拽手柄 + 移动端 `min-h-0` | 改 |

依赖：Task1（纯函数+测试）→ Task2（滚动修复，独立）→ Task3（拓宽，用 Task1 的函数）→ Task4（真机）。

---

## Task 1: `lib/dockWidth.ts` — 宽度夹取纯函数

**Files:**
- Create: `frontend/src/lib/dockWidth.ts`
- Test: `frontend/src/lib/dockWidth.test.ts`

- [ ] **Step 1: 写失败测试**

`frontend/src/lib/dockWidth.test.ts`：
```ts
import { describe, it, expect } from "vitest";
import { clampDockWidth, DOCK_MIN_WIDTH, DOCK_MAX_WIDTH } from "./dockWidth";

describe("clampDockWidth", () => {
  it("clamps below the minimum up to 300", () => {
    expect(clampDockWidth(120, 1600)).toBe(DOCK_MIN_WIDTH);
    expect(clampDockWidth(DOCK_MIN_WIDTH, 1600)).toBe(300);
  });
  it("caps at min(720, 90% viewport)", () => {
    expect(clampDockWidth(9999, 1600)).toBe(DOCK_MAX_WIDTH); // 720 < 1440
    expect(clampDockWidth(9999, 600)).toBe(540); // floor(600*0.9)=540 < 720
  });
  it("passes mid-range values through (rounded)", () => {
    expect(clampDockWidth(480.4, 1600)).toBe(480);
    expect(clampDockWidth(512.6, 1600)).toBe(513);
  });
  it("never goes below 300 even on a very narrow viewport", () => {
    // floor(320*0.9)=288 < 300 → floor still returns the 300 lower bound
    expect(clampDockWidth(288, 320)).toBe(300);
    expect(clampDockWidth(9999, 320)).toBe(300);
  });
});
```

- [ ] **Step 2: 运行确认失败**

工作目录 `frontend/`。Run: `npm test -- dockWidth`
Expected: FAIL（模块/导出不存在）

- [ ] **Step 3: 实现**

`frontend/src/lib/dockWidth.ts`：
```ts
export const DOCK_MIN_WIDTH = 300;
export const DOCK_MAX_WIDTH = 720;

/** 夹取面板宽度：下限 300，上限 min(720, 视口 90%)。极窄视口下仍保证 ≥ 300。 */
export function clampDockWidth(raw: number, viewportWidth: number): number {
  const upper = Math.min(DOCK_MAX_WIDTH, Math.floor(viewportWidth * 0.9));
  const hi = Math.max(DOCK_MIN_WIDTH, upper);
  return Math.round(Math.max(DOCK_MIN_WIDTH, Math.min(hi, raw)));
}
```

- [ ] **Step 4: 运行确认通过 + 类型检查**

Run: `npm test -- dockWidth && npm run lint`
Expected: 单测全绿；tsc 无错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/lib/dockWidth.ts frontend/src/lib/dockWidth.test.ts
git commit -m "feat(fe): clampDockWidth pure helper for InsightDock resize"
```

---

## Task 2: InsightDock 垂直滚动修复

**Files:**
- Modify: `frontend/src/components/InsightDock.tsx`

> 布局修复，无单测；靠 `tsc`/build + Task 4 真机。桌面内容容器在 `:83` 一带，移动端在 `:130` 一带。

- [ ] **Step 1: 桌面内容容器 `h-full` → `flex-1 min-h-0`，`w-[320px]` → `w-full`**

把这一行：
```tsx
        <div className={`w-[320px] flex flex-col h-full overflow-y-auto overflow-x-hidden p-3 custom-scrollbar z-10 relative transition-opacity duration-300 ${isExpanded ? 'opacity-100' : 'opacity-0'}`}>
```
改为：
```tsx
        <div className={`w-full flex flex-col flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-3 custom-scrollbar z-10 relative transition-opacity duration-300 ${isExpanded ? 'opacity-100' : 'opacity-0'}`}>
```

- [ ] **Step 2: 移动端内容容器补 `min-h-0`**

把这一行：
```tsx
            <div className="flex-1 overflow-y-auto px-4 pb-6 mt-2 space-y-4">
```
改为：
```tsx
            <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-6 mt-2 space-y-4">
```

- [ ] **Step 3: 类型检查 + 构建 + 既有测试不回归**

Run: `npm run lint && npm test && npm run build`
Expected: tsc 无错误；既有测试无新增失败（既有 `utils/roles.test.ts` 角色素材缺失为预存在失败，与本特性无关）；build 成功

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/InsightDock.tsx
git commit -m "fix(fe): InsightDock content scrolls vertically (flex-1 min-h-0) so wolf radar is reachable"
```

---

## Task 3: InsightDock 左边缘拖拽拓宽

**Files:**
- Modify: `frontend/src/components/InsightDock.tsx`

> DOM/pointer 胶水，无单测（逻辑 `clampDockWidth` 已在 Task1 测）；靠 `tsc`/build + Task4 真机。

- [ ] **Step 1: 引入 `useRef` 与 `clampDockWidth`**

文件首行：
```tsx
import React, { useState } from "react";
```
改为：
```tsx
import React, { useState, useRef } from "react";
```
在其它 import 之后（例如 `import WolfExposurePanel from "./WolfExposurePanel";` 下方）加：
```tsx
import { clampDockWidth } from "../lib/dockWidth";
```

- [ ] **Step 2: 加 width state + 拖拽 handlers**

在组件函数体内、`const canShowIdentities = isLLMOnly && showIdentities;` 之后加：
```tsx
  const [width, setWidth] = useState(320);
  const resizeRef = useRef<{ startX: number; startWidth: number } | null>(null);

  const onResizeDown = (e: React.PointerEvent) => {
    e.stopPropagation(); // 阻止 framer-motion 的「拖拽移动面板」
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    resizeRef.current = { startX: e.clientX, startWidth: width };
  };
  const onResizeMove = (e: React.PointerEvent) => {
    if (!resizeRef.current) return;
    const { startX, startWidth } = resizeRef.current;
    // 面板右锚定：向左拖（clientX 变小）→ 变宽
    setWidth(clampDockWidth(startWidth + (startX - e.clientX), window.innerWidth));
  };
  const onResizeUp = (e: React.PointerEvent) => {
    resizeRef.current = null;
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
  };
```

- [ ] **Step 3: 桌面面板宽度改为动态**

把桌面主面板的 style 块（注意是多行那处，**不是**加载占位的单行）：
```tsx
        style={{
          width: '320px',
          maxHeight: isExpanded ? 'calc(100vh - 4rem)' : '2.5rem'
        }}
```
改为：
```tsx
        style={{
          width: `${width}px`,
          maxHeight: isExpanded ? 'calc(100vh - 4rem)' : '2.5rem'
        }}
```

- [ ] **Step 4: 插入左缘拖拽手柄（仅展开时）**

在该 `motion.div` 开标签 `>` 之后、`{/* Subtle gothic border styling inside */}` 这一行之前，插入：
```tsx
        {isExpanded && (
          <div
            onPointerDown={onResizeDown}
            onPointerMove={onResizeMove}
            onPointerUp={onResizeUp}
            className="absolute left-0 top-0 h-full w-1.5 z-30 cursor-ew-resize bg-amber-500/0 hover:bg-amber-500/40 transition-colors"
            title="拖拽调整宽度"
          />
        )}
```

- [ ] **Step 5: 类型检查 + 构建 + 既有测试**

Run: `npm run lint && npm test && npm run build`
Expected: tsc 无错误；既有测试无新增失败；build 成功

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/InsightDock.tsx
git commit -m "feat(fe): InsightDock left-edge drag-to-resize (width state + clamped handle)"
```

---

## Task 4: Chrome DevTools / Playwright 真机验证

**Files:** 无（验证 only）

> 需后端(8010)+vite(IPv4) 起着，god 12p 局（4 狼，含狼队雷达）。后端 `.env` 含 `DEEPSEEK_API_KEY`（见 `apikey.txt` 的 `deepseek:` 行）+ `OBS_READY_REQUIRE_LLM=0`；vite `npm run dev -- --host 127.0.0.1`。

- [ ] **Step 1: 起服务 + 一局 12p**

```bash
# 仓库根，.env 就绪
uv run werewolf-api --port 8010                       # 后台
cd frontend && npm run dev -- --host 127.0.0.1         # 后台
curl -s -X POST http://127.0.0.1:8010/api/v1/games/start -H 'Content-Type: application/json' \
  -d '{"config_id":"llm-12p-deepseek","run_label":"dock-verify12","track_vote_intentions":true}'
```
轮询 `artifacts/runs/<run_id>/events.jsonl` 到出现 `belief_snapshot` 且 `vote_intention_snapshot`。

- [ ] **Step 2: 打开 god 页，验证垂直滚动**

`browser_navigate` 到 `http://127.0.0.1:5173/game?run_id=<run_id>&source=runs`，`wait_for` `信念矩阵`。
`browser_evaluate`：把桌面滚动容器（`.overflow-y-auto.flex-1` 或含信念矩阵的容器）`scrollTop` 设到 `scrollHeight`，断言 `狼队·暴露雷达` 元素 `getBoundingClientRect().bottom <= window.innerHeight`（可完整滚到可见）。断言该容器 `scrollHeight > clientHeight`（确有可滚内容）。

- [ ] **Step 3: 验证左缘拖拽拓宽**

`browser_evaluate` 读取桌面面板（`motion.div`，`right-6 top-12` 那个）当前 `offsetWidth`（应 320）。用 Playwright 在面板左边缘（`w-1.5` 手柄）做 pointer 拖拽：从手柄中心向左拖 ~160px。再读 `offsetWidth`，断言已增大且 `≤ min(720, innerWidth*0.9)`；断言信念矩阵网格容器 `scrollWidth - clientWidth` 减小（少横滚）或列更多可见。

- [ ] **Step 4: 验证手柄不移动面板**

记录拖拽前面板 `getBoundingClientRect().top/right`；拖完后断言 top/right 基本不变（仅宽度变化，面板未被 framer-motion 整体移动）。`list_console_messages`/`browser_console_messages` 过滤 error = 0（THREE.js deprecation 警告无关）。`take_screenshot` 存 `.tmp/dock-verify.png`。

- [ ] **Step 5: 记录结果 + 收尾**

把结论（PASS/问题 + 截图）回报。取消对局、停后端/vite、删临时 `.env`（key 仍在 `apikey.txt`）、还原运行期无关产物（skill `.md` / lock / pytest 日志）。

---

## Self-Review

- **Spec 覆盖**：§2 垂直滚动→Task2（桌面 `flex-1 min-h-0`+`w-full`、移动 `min-h-0`）；§3 拓宽→Task3（width state、动态宽度、左缘手柄、stopPropagation）；§4 纯函数→Task1（`clampDockWidth`+常量）；§5 测试→Task1 单测 + Task4 真机（滚动到雷达、拖宽、手柄不移动、0 error）。✅
- **占位符**：无 TBD/TODO；每个代码步给完整代码与精确锚点（多行 style 块避开单行加载占位）。✅
- **类型一致**：`clampDockWidth`/`DOCK_MIN_WIDTH`/`DOCK_MAX_WIDTH`（lib，Task1↔Task3 用法一致）；`width:number` state、`resizeRef<{startX,startWidth}>`、三个 `on Resize*` handler 命名贯穿 Task3。✅
- **YAGNI**：宽度不持久化；未触碰其它面板/移动端布局（仅补 `min-h-0`）。✅

---

## 验证结果（2026-06-08）

单测：`dockWidth.test.ts` 4/4 绿；全套件 166/166（含先前因素材缺失而挂的 `roles.test`，现已被 main 合入的素材修复）。`tsc`/`build` 通过。

真机（Playwright，DeepSeek `llm-12p-deepseek` god 局）——真机验证额外抓出并修复了 2 个 bug：
1. **Rules-of-Hooks 崩溃**：resize 的 `useState/useRef` 最初放在 `if(!beliefs) return` 早返回之后，数据到达后 hook 数变化 → GameApp 落入 ErrorBoundary。已上移到早返回之前。
2. **面板被压扁而非滚动**：滚动容器原为 `flex flex-col`，内部各面板（`overflow-hidden`）作为可收缩 flex 子项被压扁（信念矩阵 460→59px、雷达 124→17px）。改为 block-flow（仅保留 `flex-1 min-h-0` 作为 motion.div 的 flex 子项）后，面板保持自然高度、容器真正滚动。
3. **拖手柄导致面板漂移**：framer-motion 的 drag 监听在面板自身，手柄的 React `stopPropagation` 拦不住 → 拓宽时面板同时被移动（right 1256→956）。改用 `dragListener=false` + `useDragControls`，移动仅从头部发起，手柄只改宽度。

最终断言（viewport 1280×800 与 1100×360）：
- 短视口下内容溢出（scrollHeight 1595 > clientHeight 255），面板自然高度（矩阵 460 / 投票 887 / 雷达 124），滚动到底「🐺 狼队·暴露雷达」完整可见。
- 左缘拖拽：宽度 320 → 620（≤ min(720, 90vw)），面板 right/top **不变**（不漂移）。
- 全程 0 console error。
