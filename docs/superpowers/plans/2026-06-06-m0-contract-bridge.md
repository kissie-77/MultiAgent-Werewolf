# M0 契约打通 (Contract Bridge) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让前端在开发态直连真实 FastAPI 后端、统一解 `ApiResponse{data}` 信封、把 `RunsPage` 等内容页从 mock 切到真实数据、修掉分享死链，并废弃 Express+Gemini mock —— 为后续 M1（SSE 观战）打好地基。

**Architecture:** 前端 `dev` 改用 Vite + `server.proxy` 把 `/api`/`/ready` 反代到 `http://localhost:8000`（uvicorn FastAPI）。`ApiClient` 增加 `unwrap()` 解包 `{success,data,message}` 信封并带 `API_BASE`。`RunsPage` 改读 `GET /api/v1/runs`（`ApiResponse[RunListPageData]`），渲染后端真实字段（`run_id/winner_camp/player_count/created_at/has_replay`），删除原 mock 的虚构座位条/模型/MVP。新增 Vitest 作为前端单测框架，对纯函数（`unwrap`、`mapRunRow`）做 TDD。

**Tech Stack:** React 19 + Vite 6 + TypeScript + Zustand + Vitest（新增）；后端 FastAPI（uvicorn，`werewolf-api`）。

**这是本里程碑的边界（M0 不做）：** SSE/事件流、对局直播、信念矩阵、人机对战、原始 Key 注入 —— 均在 M1–M3。
**M0 显式 Follow-up（本计划末尾列出，不在 M0 任务内）：** 恢复 `frontend/Dockerfile`（nginx 生产托管）、清理 `express`/`@google/genai` 依赖。

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `frontend/vitest.config.ts` | Vitest 配置（node 环境，跑纯函数单测） | Create |
| `frontend/package.json` | 增 `test` 脚本 + `vitest` devDep；`dev`→`vite`；`build`→`vite build`；删 `start` | Modify |
| `frontend/vite.config.ts` | `server.proxy` 反代 `/api`、`/ready` 到 8000 | Modify |
| `frontend/src/api/client.ts` | 导出纯函数 `unwrap`；`get()` 解包 + `API_BASE`；新增 `getRunsPageData` | Modify |
| `frontend/src/api/client.unwrap.test.ts` | `unwrap` 单测 | Create |
| `frontend/src/api/types.ts` | 增 `PageMeta`/`Paginated`/`RunSummary`/`RunListPageData` | Modify |
| `frontend/src/utils/runRows.ts` | 纯函数 `mapRunRow(RunSummary)→RunRow` | Create |
| `frontend/src/utils/runRows.test.ts` | `mapRunRow` 单测 | Create |
| `frontend/src/pages/RunsPage.tsx` | 改读真实 `/api/v1/runs`，渲染后端字段，删 mock | Replace |
| `frontend/src/pages/ReplayPage.tsx` | 修分享死链 `/share/replay/${run.id}`→`/share/${runId}` | Modify (line ~278) |
| `frontend/server.ts` | 废弃 Express+Gemini mock | Delete |

---

## Task 1: 引入 Vitest 前端单测框架

**Files:**
- Create: `frontend/vitest.config.ts`
- Modify: `frontend/package.json`

- [ ] **Step 1: 安装 vitest**

Run（在 `frontend/` 目录）:
```bash
cd frontend && npm install -D vitest@^2
```
Expected: `package.json` devDependencies 出现 `vitest`，无安装错误。

- [ ] **Step 2: 创建 `frontend/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
```

- [ ] **Step 3: 在 `frontend/package.json` 的 `scripts` 增加 `test`**

把 `scripts` 块改为（仅增 `test` 一行，其余暂不动；`dev`/`build`/`start` 在 Task 6 处理）：
```jsonc
"scripts": {
  "dev": "tsx server.ts",
  "build": "vite build && esbuild server.ts --bundle --platform=node --format=cjs --packages=external --sourcemap --outfile=dist/server.cjs",
  "start": "node dist/server.cjs",
  "preview": "vite preview",
  "clean": "rm -rf dist server.js",
  "lint": "tsc --noEmit",
  "test": "vitest run"
}
```

- [ ] **Step 4: 验证 vitest 可运行（无测试时应空跑通过）**

Run: `cd frontend && npm run test`
Expected: vitest 启动，提示 “No test files found” 或 0 passed —— 退出码 0（命令不报错即可）。

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts
git commit -m "test(frontend): add vitest harness for unit tests"
```

---

## Task 2: `ApiClient` 解包 `{data}` 信封 + `API_BASE`

**Files:**
- Modify: `frontend/src/api/client.ts`
- Test: `frontend/src/api/client.unwrap.test.ts`

后端所有响应是 `{ success, data, message }`；旧 mock 返回裸 payload。`unwrap` 必须两者都兼容：是信封就取 `.data`，否则原样返回。

- [ ] **Step 1: 写失败测试 `frontend/src/api/client.unwrap.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import { unwrap } from "./client";

describe("unwrap", () => {
  it("extracts .data from a FastAPI ApiResponse envelope", () => {
    const env = { success: true, data: { hello: "world" }, message: null };
    expect(unwrap<{ hello: string }>(env)).toEqual({ hello: "world" });
  });

  it("returns bare payload unchanged when not an envelope", () => {
    const bare = { hello: "world" };
    expect(unwrap<{ hello: string }>(bare)).toEqual({ hello: "world" });
  });

  it("treats an object that merely has a 'data' key but no envelope marker as bare", () => {
    const bare = { data: [1, 2, 3] }; // no success/message → not an envelope
    expect(unwrap<{ data: number[] }>(bare)).toEqual({ data: [1, 2, 3] });
  });

  it("passes through null/primitive payloads", () => {
    expect(unwrap<null>(null as unknown)).toBeNull();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/api/client.unwrap.test.ts`
Expected: FAIL —— `unwrap` is not exported / not defined。

- [ ] **Step 3: 在 `frontend/src/api/client.ts` 顶部加 `API_BASE` 与 `unwrap`，并改 `get`**

在文件 import 段之后、`export class ApiClient` 之前插入：
```ts
const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/+$/, "");

/**
 * Unwrap the backend's ApiResponse<T> envelope ({ success, data, message }).
 * Returns the inner `data`. If the value is not an envelope (e.g. a bare
 * payload), it is returned unchanged so tests/legacy paths keep working.
 */
export function unwrap<T>(json: unknown): T {
  if (
    json !== null &&
    typeof json === "object" &&
    "data" in (json as Record<string, unknown>) &&
    ("success" in (json as Record<string, unknown>) ||
      "message" in (json as Record<string, unknown>))
  ) {
    return (json as { data: T }).data;
  }
  return json as T;
}
```

把现有私有方法 `get` 改为：
```ts
  private static async get<T>(url: string): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`);
    if (!response.ok) {
      throw new Error(`API error fetching ${url}: ${response.statusText}`);
    }
    return unwrap<T>(await response.json());
  }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/api/client.unwrap.test.ts`
Expected: PASS（4 passed）。

- [ ] **Step 5: 类型检查不回归**

Run: `cd frontend && npm run lint`
Expected: 退出码 0（无新 TS 报错）。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/client.unwrap.test.ts
git commit -m "feat(frontend): unwrap ApiResponse envelope + API_BASE in ApiClient"
```

---

## Task 3: 运行列表类型（前端 DTO）

**Files:**
- Modify: `frontend/src/api/types.ts`

- [ ] **Step 1: 在 `frontend/src/api/types.ts` 末尾追加（与后端 `common.py` 对齐）**

```ts
// --- Runs list (mirrors backend ApiResponse[RunListPageData]) ---
export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface Paginated<T> {
  items: T[];
  meta: PageMeta;
}

export interface RunSummary {
  run_id: string;
  source: string; // "runs" | "eval"
  path: string;
  created_at: string | null;
  player_count: number | null;
  winner_camp: string | null; // "GOOD" | "WEREWOLF" | ... | null
  has_post_game: boolean;
  has_replay: boolean;
}

export interface RunListPageData {
  runs: Paginated<RunSummary>;
}
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npm run lint`
Expected: 退出码 0。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/types.ts
git commit -m "feat(frontend): add RunSummary/RunListPageData types"
```

---

## Task 4: `ApiClient.getRunsPageData`

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 在 `client.ts` 的 import 里补类型**

把顶部从 `"./types"` 的 import 列表里加上 `RunListPageData`（与现有逐项导入风格一致），例如在末项后追加：
```ts
  StrategyPageData,
  RunListPageData
} from "./types";
```

- [ ] **Step 2: 在 `ApiClient` 类内新增方法（放在 `getStrategyPageData` 之后、类结束 `}` 之前）**

```ts
  static async getRunsPageData(page = 1, pageSize = 20): Promise<RunListPageData> {
    return this.get<RunListPageData>(
      `/api/v1/runs?page=${page}&page_size=${pageSize}`
    );
  }
```

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npm run lint`
Expected: 退出码 0。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat(frontend): ApiClient.getRunsPageData -> GET /api/v1/runs"
```

---

## Task 5: `RunsPage` 切到真实后端

后端 `RunSummary` 没有 `model`/`players[]`/MVP，所以删除 mock 的虚构座位条、模型筛选与 MVP 徽章，只渲染后端真实字段。先抽出纯函数 `mapRunRow` 做 TDD。

**Files:**
- Create: `frontend/src/utils/runRows.ts`
- Test: `frontend/src/utils/runRows.test.ts`
- Replace: `frontend/src/pages/RunsPage.tsx`

- [ ] **Step 1: 写失败测试 `frontend/src/utils/runRows.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import { mapRunRow } from "./runRows";
import type { RunSummary } from "../api/types";

const base: RunSummary = {
  run_id: "demo-6-20260606-101010",
  source: "runs",
  path: "/x",
  created_at: "06-06",
  player_count: 6,
  winner_camp: "good",
  has_post_game: true,
  has_replay: true,
};

describe("mapRunRow", () => {
  it("normalizes winner_camp to upper-case canonical value", () => {
    expect(mapRunRow(base).winnerCamp).toBe("GOOD");
    expect(mapRunRow({ ...base, winner_camp: "werewolf" }).winnerCamp).toBe("WEREWOLF");
  });

  it("falls back to UNKNOWN for null/unexpected winner_camp", () => {
    expect(mapRunRow({ ...base, winner_camp: null }).winnerCamp).toBe("UNKNOWN");
    expect(mapRunRow({ ...base, winner_camp: "??" }).winnerCamp).toBe("UNKNOWN");
  });

  it("defaults missing player_count/created_at", () => {
    const r = mapRunRow({ ...base, player_count: null, created_at: null });
    expect(r.playerCount).toBe(0);
    expect(r.createdAt).toBe("");
  });

  it("carries run_id and has_replay through", () => {
    const r = mapRunRow(base);
    expect(r.runId).toBe(base.run_id);
    expect(r.hasReplay).toBe(true);
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/utils/runRows.test.ts`
Expected: FAIL —— `mapRunRow` not defined。

- [ ] **Step 3: 实现 `frontend/src/utils/runRows.ts`**

```ts
import type { RunSummary } from "../api/types";

export type WinnerCamp = "GOOD" | "WEREWOLF" | "DRAW" | "UNKNOWN";

export interface RunRow {
  runId: string;
  winnerCamp: WinnerCamp;
  playerCount: number;
  createdAt: string;
  hasReplay: boolean;
}

export function mapRunRow(s: RunSummary): RunRow {
  const wc = (s.winner_camp ?? "").toUpperCase();
  const winnerCamp: WinnerCamp =
    wc === "GOOD" || wc === "WEREWOLF" || wc === "DRAW" ? (wc as WinnerCamp) : "UNKNOWN";
  return {
    runId: s.run_id,
    winnerCamp,
    playerCount: s.player_count ?? 0,
    createdAt: s.created_at ?? "",
    hasReplay: s.has_replay,
  };
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/utils/runRows.test.ts`
Expected: PASS（4 passed）。

- [ ] **Step 5: 用真实数据 + `mapRunRow` 重写 `frontend/src/pages/RunsPage.tsx`（整文件替换）**

```tsx
import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Shield, Search, ChevronDown, Play, Share, Trophy, Users, AlertCircle } from "lucide-react";
import { motion } from "motion/react";
import { ApiClient } from "../api/client";
import { mapRunRow, type RunRow } from "../utils/runRows";

export default function RunsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [campFilter, setCampFilter] = useState("ALL");
  const [countFilter, setCountFilter] = useState("ALL");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    ApiClient.getRunsPageData(1, 50)
      .then((data) => {
        if (cancelled) return;
        setRuns(data.runs.items.map(mapRunRow));
        setError(null);
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredRuns = runs.filter((run) => {
    if (campFilter !== "ALL" && run.winnerCamp !== campFilter) return false;
    if (countFilter !== "ALL" && run.playerCount.toString() !== countFilter) return false;
    return true;
  });

  const winnerBadge = (camp: RunRow["winnerCamp"]) => {
    if (camp === "GOOD")
      return <span className="text-blue-400 flex items-center gap-1.5 font-bold tracking-widest text-sm"><Trophy className="w-4 h-4" /> 好人胜</span>;
    if (camp === "WEREWOLF")
      return <span className="text-red-500 flex items-center gap-1.5 font-bold tracking-widest text-sm"><Trophy className="w-4 h-4" /> 狼人胜</span>;
    if (camp === "DRAW")
      return <span className="text-zinc-400 flex items-center gap-1.5 font-bold tracking-widest text-sm">平局 / 弃局</span>;
    return <span className="text-zinc-500 flex items-center gap-1.5 font-bold tracking-widest text-sm">未结算</span>;
  };

  return (
    <div className="min-h-screen bg-[#07050d] text-zinc-100 font-sans relative overflow-x-hidden p-6 md:p-12">
      <div className="absolute inset-4 pointer-events-none border border-zinc-900/50 rounded z-0" />
      <div className="absolute inset-5 pointer-events-none border-2 border-zinc-950/80 rounded z-0" />

      <div className="max-w-6xl mx-auto relative z-10">
        <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-zinc-900/80 pb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Shield className="w-6 h-6 text-yellow-500" />
              <h1 className="text-3xl font-black tracking-widest uppercase font-serif text-transparent bg-clip-text bg-gradient-to-r from-zinc-100 to-zinc-400">
                战绩中心
              </h1>
            </div>
            <p className="text-xs font-mono text-zinc-500 tracking-[0.2em]">
              RECORD OF JUDGMENTS &bull; {runs.length} 局记载
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="relative group">
              <select
                value={campFilter}
                onChange={(e) => setCampFilter(e.target.value)}
                className="appearance-none bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-400 px-4 py-2 pr-8 rounded hover:border-zinc-700 outline-none cursor-pointer focus:border-yellow-500/50"
              >
                <option value="ALL">阵营 [全部]</option>
                <option value="GOOD">好人获胜</option>
                <option value="WEREWOLF">狼人获胜</option>
                <option value="DRAW">平局弃局</option>
              </select>
              <ChevronDown className="w-3 h-3 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-600 group-hover:text-zinc-400" />
            </div>
            <div className="relative group">
              <select
                value={countFilter}
                onChange={(e) => setCountFilter(e.target.value)}
                className="appearance-none bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-400 px-4 py-2 pr-8 rounded hover:border-zinc-700 outline-none cursor-pointer focus:border-yellow-500/50"
              >
                <option value="ALL">人数 [全部]</option>
                <option value="6">6 人局</option>
                <option value="9">9 人局</option>
                <option value="12">12 人局</option>
              </select>
              <ChevronDown className="w-3 h-3 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-600 group-hover:text-zinc-400" />
            </div>
            <button className="h-[34px] w-[34px] flex items-center justify-center bg-zinc-900 border border-zinc-800 rounded hover:border-yellow-500 hover:text-yellow-500 transition-colors text-zinc-400">
              <Search className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-40 bg-zinc-900/40 rounded-lg border border-zinc-800/50 animate-pulse" />
            ))}
          </div>
        ) : error ? (
          <div className="py-20 flex flex-col items-center justify-center text-red-400/80 gap-4 text-center">
            <AlertCircle className="w-12 h-12 text-red-700" />
            <p className="font-mono text-xs">加载对局卷宗失败：{error}</p>
          </div>
        ) : filteredRuns.length === 0 ? (
          <div className="py-20 flex flex-col items-center justify-center text-zinc-500 gap-4 text-center">
            <AlertCircle className="w-12 h-12 text-zinc-700" />
            <div className="space-y-1">
              <p className="font-sans text-sm">虚境内尚未窥见相应的对局卷宗</p>
              <p className="font-mono text-xs opacity-60">尝试其他筛选条件，或去推案大厅新开一局。</p>
            </div>
            <Link to="/" className="mt-4 px-6 py-2 bg-yellow-600/20 text-yellow-500 hover:bg-yellow-600/30 border border-yellow-600/50 rounded text-xs font-mono tracking-widest uppercase transition-colors">
              新开对局
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {filteredRuns.map((run, idx) => (
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                key={run.runId}
                className="bg-zinc-950/80 border border-zinc-900 hover:border-zinc-700/80 rounded-lg p-5 flex flex-col justify-between group transition-all"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      {winnerBadge(run.winnerCamp)}
                      <span className="text-zinc-600 text-[10px] font-mono border-l border-zinc-800 pl-2 ml-1">
                        {run.playerCount}人 &middot; {run.createdAt}
                      </span>
                    </div>
                    <div className="text-[10px] font-mono text-zinc-500 tracking-wider">#{run.runId}</div>
                  </div>
                </div>

                <div className="flex items-end justify-between mt-auto">
                  <div className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    {run.playerCount} 座
                  </div>
                  <div className="flex items-center gap-2">
                    {run.hasReplay ? (
                      <Link
                        to={`/replay/${run.runId}`}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30 hover:text-indigo-300 border border-indigo-500/30 rounded font-mono text-[10px] uppercase tracking-widest transition-colors"
                      >
                        <Play className="w-3 h-3" /> 复盘
                      </Link>
                    ) : (
                      <span className="text-[10px] text-zinc-600 font-mono">无回放</span>
                    )}
                    <Link
                      to={`/share/${run.runId}`}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-300 border border-zinc-700 rounded font-mono text-[10px] uppercase tracking-widest transition-colors"
                    >
                      <Share className="w-3 h-3" /> 分享
                    </Link>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: 类型检查 + 单测全绿**

Run: `cd frontend && npm run lint && npm run test`
Expected: lint 退出码 0；vitest 全部 passed。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/utils/runRows.ts frontend/src/utils/runRows.test.ts frontend/src/pages/RunsPage.tsx
git commit -m "feat(frontend): wire RunsPage to real GET /api/v1/runs (drop mock)"
```

---

## Task 6: 修 `ReplayPage` 分享死链

`ReplayPage.tsx` 第 ~278 行链接到不存在的 `/share/replay/${run.id}`，会落到 `*` 兜底重定向回 `/`。正确路由是 `/share/:runId`。

**Files:**
- Modify: `frontend/src/pages/ReplayPage.tsx`

- [ ] **Step 1: 定位并修正链接**

把：
```tsx
          to={`/share/replay/${run.id}`}
```
改为（`runId` 为该页 `useParams<{ runId: string }>()` 解出的同一个值，即调用 `ApiClient.getReplayData(runId)` 用的那个；若当前作用域内变量名不同，使用该页实际的 runId 变量）：
```tsx
          to={`/share/${runId}`}
```

- [ ] **Step 2: 确认 `runId` 在该作用域可用**

用编辑器/grep 确认 `ReplayPage` 顶部有 `const { runId } = useParams<{ runId: string }>();`（或等价）。若该分享按钮位于某个子映射且无法访问页面级 `runId`，则改用该上下文中可得的 run 标识；务必指向 `/share/<真实runId>`。

Run: `cd frontend && npm run lint`
Expected: 退出码 0（无未定义变量）。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ReplayPage.tsx
git commit -m "fix(frontend): correct replay share link to /share/:runId"
```

---

## Task 7: Vite 开发代理 + 废弃 Express mock

让 `dev` 用 Vite 直接服务 SPA 并把 `/api`、`/ready` 反代到 FastAPI；删除 `server.ts` mock；`build` 只产出静态资源。

**Files:**
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/package.json`
- Delete: `frontend/server.ts`

- [ ] **Step 1: 在 `frontend/vite.config.ts` 的 `server` 块加 `proxy`**

把现有 `server: { ... }` 改为：
```ts
    server: {
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      proxy: {
        '/api': { target: 'http://localhost:8000', changeOrigin: true },
        '/ready': { target: 'http://localhost:8000', changeOrigin: true },
      },
    },
```

- [ ] **Step 2: 改 `frontend/package.json` 的 `scripts`（`dev`→vite，`build`→纯静态，删 `start`）**

```jsonc
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "preview": "vite preview",
  "clean": "rm -rf dist",
  "lint": "tsc --noEmit",
  "test": "vitest run"
}
```

- [ ] **Step 3: 删除 mock 服务器**

Run: `git rm frontend/server.ts`
Expected: `server.ts` 从工作树与索引移除。

- [ ] **Step 4: 确认前端可构建（静态产物，不再依赖 server.ts）**

Run: `cd frontend && npm run build`
Expected: `vite build` 成功，生成 `dist/`，无对 `server.ts` 的引用错误。

> 注：`@google/genai`、`express`、`tsx`、`esbuild` 等依赖此刻变为未使用 —— **清理留到 Follow-up**，本任务不删，避免 lockfile 大改干扰评审。

- [ ] **Step 5: Commit**

```bash
git add frontend/vite.config.ts frontend/package.json
git commit -m "build(frontend): vite dev proxy to FastAPI + retire express mock"
```

---

## Task 8: 端到端联调验证（手动）

M0 的「契约打通」靠真实前后端联调验证（代理 + 解包不是单测能覆盖的）。

**Files:** 无（验证步骤）

- [ ] **Step 1: 启动后端**

Run（仓库根，需已 `make setup` 装好依赖；UI-only 联调可设 `OBS_READY_REQUIRE_LLM=0`）:
```bash
OBS_READY_REQUIRE_LLM=0 make api
```
Expected: uvicorn 监听 `127.0.0.1:8000`；`curl -s localhost:8000/health` 返回 `{"status":"ok"}`。

- [ ] **Step 2: 生成一局测试数据（让 runs/replay 有内容）**

Run（另开终端，仓库根）:
```bash
PYTHONUTF8=1 make demo
```
Expected: 离线 demo 局跑完，在 `artifacts/runs/` 下生成一个 run 目录（含 `events.jsonl`、`run_meta.json`）。

- [ ] **Step 3: 验证后端 runs 接口返回信封**

Run:
```bash
curl -s "http://localhost:8000/api/v1/runs?page=1&page_size=5"
```
Expected: JSON 形如 `{"success":true,"data":{"runs":{"items":[{...,"run_id":...}],"meta":{...}}},"message":null}`，`items` 至少 1 条。

- [ ] **Step 4: 启动前端 dev 并验证代理 + 解包**

Run:
```bash
cd frontend && npm run dev
```
打开 `http://localhost:5173/runs`（或 vite 实际端口）。
Expected:
- `/runs` 显示真实 run 卡片（来自 Step 2 的 demo 局），不再是 06-04 / Doubao 这类 mock。
- 浏览器 Network 里 `/api/v1/runs` 经 Vite 代理打到 8000，状态 200。
- 点「复盘」进入 `/replay/<run_id>` 能加载真实复盘页（解包生效，字段非 undefined）。
- 在复盘页点「分享」跳到 `/share/<run_id>`（不再被重定向回 `/`）。

- [ ] **Step 5: 回归 —— 内容页解包生效**

依次访问 `/home`、`/roles`、`/models`、`/about`，确认均渲染真实后端数据（非空白/非 undefined）。
Expected: 各页正常渲染；控制台无 “reading 'xxx' of undefined” 类错误。

- [ ] **Step 6: 全量单测 + lint 收口**

Run: `cd frontend && npm run test && npm run lint`
Expected: 全绿，退出码 0。

- [ ] **Step 7: 记录验证结论（无代码改动则跳过 commit）**

在 PR/任务备注中记录 Step 4–5 的实测结果（截图或文字）。

---

## Self-Review

**Spec coverage（对照 spec §7 C1/C2/C9 与 §11）：**
- C2 ApiClient 解包 + base-url → Task 2 ✅；新增 runs 读取 → Task 4 ✅。
- C9 RunsPage 接真实 `/runs`、修 `/share` 死链 → Task 5、Task 6 ✅。
- C1 删 mock + Vite proxy → Task 7 ✅。
- 内容页接真后端（解包后即生效）→ Task 8 Step 5 验证 ✅。
- 未覆盖（有意留到后续里程碑/Follow-up）：SSE/reducer/store 重写（M1）、信念矩阵真数据（M2）、人机（M3）、prod nginx Dockerfile（Follow-up）。

**Placeholder scan:** 无 TODO/TBD；每个改码步骤都给了完整代码或精确替换串。

**Type consistency:** `unwrap<T>`（Task 2）↔ `get<T>`（Task 2）↔ `RunListPageData`/`RunSummary`（Task 3）↔ `getRunsPageData`（Task 4）↔ `mapRunRow`/`RunRow`（Task 5）↔ `RunsPage` 使用 `data.runs.items.map(mapRunRow)`（Task 5）一致。`winnerCamp` 取值集合 `GOOD|WEREWOLF|DRAW|UNKNOWN` 在 `runRows.ts` 与 `RunsPage` 渲染分支一致。

---

## Follow-up（不在 M0，记录以免遗漏）

1. **恢复生产 `frontend/Dockerfile`**：nginx 托管 `dist/` + 复制 `deploy/nginx-frontend.conf`（需同时核对 `docker-compose.yml` 的 `web.build.context`，因 `deploy/` 在 `frontend/` 之外，可能改 context 为仓库根或把 conf 纳入 `frontend/`）。否则 `docker compose build web` 仍失败。
2. **清理未用前端依赖**：`@google/genai`、`express`、`@types/express`、`tsx`、`esbuild`、`dotenv`。
3. **`/rules` 与 `/how-to-play` 别名、`NotImplementedPage` 未路由**：随手清理（非阻塞）。
