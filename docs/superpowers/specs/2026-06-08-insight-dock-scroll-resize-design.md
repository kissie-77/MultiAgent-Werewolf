# 观战读心栏（InsightDock）垂直滚动修复 + 左右拖拽拓宽 设计

- 日期：2026-06-08
- 分支：`feature/insight-dock-scroll-resize`
- 关联：`InsightDock.tsx`（承载信念矩阵 / B2 / 投票意向 / 狼队暴露雷达）

## 1. 背景与问题

实测（用户截图）：god 观战时，`InsightDock` 内容（信念矩阵 + B2 + 投票意向 + 🐺狼队暴露雷达）高于视口，**底部的狼队雷达被裁掉、且无法滚动到**。

**根因**：桌面滚动容器（`InsightDock.tsx:83`）用 `h-full`（`height:100%`）置于一个 `max-height` 受限、但**无定高**的 flex 列（`motion.div` 仅有 `maxHeight`）。百分比高度在无定高父级下塌缩为 `auto` → 内容区撑到全内容高度 → `motion.div` 的 `overflow-hidden` 把底部裁掉，内层 `overflow-y-auto` 永不触发。

**目标**（纯前端、零后端）：
1. 修复垂直滚动：内容区改为占据剩余空间并内部滚动，能滚到狼队雷达。
2. 新增左右拖拽拓宽：拖左边缘加宽/变窄面板（面板右锚定），加宽后信念矩阵也少横滚。

**非目标**：移动端布局重构（移动抽屉已 `flex-1 overflow-y-auto` + 定高父，仅补 `min-h-0` 防御）；宽度持久化（YAGNI）；改动其它面板内部。

## 2. 垂直滚动修复

- 桌面内容容器（`:83`）：`w-[320px] flex flex-col h-full overflow-y-auto overflow-x-hidden …` → **`w-full flex flex-col flex-1 min-h-0 overflow-y-auto overflow-x-hidden …`**。
  - `flex-1 min-h-0`：在 `maxHeight` 封顶的 flex 列里，`shrink-0` 的头部（`h-[2.5rem]`）保留，内容区占据剩余空间；`min-h-0` 解除 flex item 默认 `min-height:auto`，允许其收缩并由 `overflow-y-auto` 内部滚动。
  - `w-[320px]` → `w-full`：宽度跟随面板（为拓宽做准备）。
- 移动抽屉内容容器（`:130`，`flex-1 overflow-y-auto px-4 …`）：补 `min-h-0`（防御，父 `h-[60%]` 已定高，当前可滚）。

## 3. 左右拖拽拓宽（仅桌面 `motion.div`）

- 新增组件 state：`const [width, setWidth] = useState(320)`。
- 主面板 `motion.div` 的 `style.width: '320px'` → `style.width: ${width}px`（`:48`）。加载占位面板（`:20`，数据未就绪时短暂出现）保持 320 不变（瞬态，无需跟随）。
- 内容容器宽度由 §2 的 `w-full` 跟随。
- **左边缘拖拽手柄**（仅 `isExpanded` 时渲染）：`motion.div` 内一个绝对定位条
  `absolute left-0 top-0 h-full w-1.5 cursor-ew-resize z-30`（半透明，hover 提示）。
  - `onPointerDown={e => { e.stopPropagation(); e.currentTarget.setPointerCapture(e.pointerId); 记录 startX=e.clientX, startWidth=width; }}`
    —— `stopPropagation` 阻止 framer-motion 的「拖拽移动面板」在手柄上触发。
  - `onPointerMove`：拖拽中时 `setWidth(clampDockWidth(startWidth + (startX - e.clientX), window.innerWidth))`（**左拖 → clientX 变小 → 变宽**，因面板右锚定）。
  - `onPointerUp`：结束拖拽、`releasePointerCapture`。
- 面板的 `drag`（整体移动）保留不变；手柄区域因 `stopPropagation` 不触发移动。

## 4. 唯一可测逻辑（纯函数，沿用本仓 lib+vitest 范式）

`frontend/src/lib/dockWidth.ts`：
```ts
export const DOCK_MIN_WIDTH = 300;
export const DOCK_MAX_WIDTH = 720;
/** 夹取面板宽度：下限 300，上限 min(720, 视口 90%)。 */
export function clampDockWidth(raw: number, viewportWidth: number): number {
  const upper = Math.min(DOCK_MAX_WIDTH, Math.floor(viewportWidth * 0.9));
  const hi = Math.max(DOCK_MIN_WIDTH, upper); // 极窄视口下保证 hi ≥ 下限
  return Math.round(Math.max(DOCK_MIN_WIDTH, Math.min(hi, raw)));
}
```
拖拽 DOM/pointer 胶水与 `flex-1` 改动 = 组件薄壳，靠 `tsc`/build + 真机验证。

## 5. 测试

- `lib/dockWidth.test.ts`（node vitest）：`clampDockWidth`
  - `< 300 → 300`；
  - `> min(720, 0.9*vw) → cap`（如 vw=1600 → cap 720；vw=600 → cap 540）；
  - 中间值四舍五入原样；
  - 极窄视口（vw=320 → cap 288 < 300）时仍返回 300（hi 兜底）。
- 真机（Chrome DevTools/Playwright，god 12p 局）：
  - 内容可垂直滚动，能滚到「🐺 狼队·暴露雷达」并完整可见。
  - 拖左边缘 → 面板变宽（≤ min(720,90vw)）、信念矩阵随宽少横滚；松手保持。
  - 拖手柄**不**移动整个面板（move-drag 未触发）。
  - 0 console error。

## 6. 文件清单

| 文件 | 责任 | 类型 |
|------|------|------|
| `frontend/src/lib/dockWidth.ts` | `clampDockWidth` + 常量 | 新建 |
| `frontend/src/lib/dockWidth.test.ts` | 上述单测 | 新建 |
| `frontend/src/components/InsightDock.tsx` | 滚动修复（`flex-1 min-h-0`/`w-full`）+ 宽度 state + 左缘拖拽手柄；移动端补 `min-h-0` | 改 |

## 7. 风险

- **framer-motion drag 冲突**：手柄 `onPointerDown` 的 `stopPropagation` 须先于 motion 的监听生效；若仍被移动，回退用 `onPointerDownCapture` 阻断。真机用例专门验证「拖手柄不移动面板」。
- **收起态**：手柄仅 `isExpanded` 时渲染，收起（`maxHeight:2.5rem`）不显示，避免在 2.5rem 高度出现半截手柄。
- **宽度不持久化**：刷新回 320（已与用户确认，YAGNI）。
