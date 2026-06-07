# UI 开局（从界面一键开局→观战） Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `GameSetup` 点「开始」直接调真实 `POST /api/v1/games/start` 起一局**全 AI 对局**，成功后用后端返回的 `game_page_path`（`/game?run_id=...`，路由已修可用）跳转进**实时观战**。不再走已废弃的 mock `resetGame()`（`/api/game/reset` → 404）。

**Architecture:** 新增 `ApiClient.startGame(req)`（POST + 解 `data` 信封 + 失败抛后端 detail）。`GameSetup.startMatch` 改为调 `startGame({ config_id: "llm-6p-deepseek", badge_flow: hasSheriff })` → `navigate(res.game_page_path)`。用本地 `starting`/`startError` 管理按钮态与错误显示（不再依赖 store 的 mock `isLoading`）。

**为什么硬编码 `llm-6p-deepseek`：** `/games/modes` 与 `(all_agent,*)` 解析出的是 Kimi/Doubao/AgentScope 配置（需对应 Key）；而当前可用 Key 是 **DeepSeek**，`configs/llm-6p-deepseek.yaml`（`api_key_env: DEEPSEEK_API_KEY`）是确定能用 DeepSeek 跑起来的配置。模式/人数/供应商选择器留作后续（YAGNI）。

**Tech Stack:** React + Zustand + react-router `useNavigate`；Vitest（startGame 用 fetch mock 单测）。

**前置运行条件（人工）：** 后端需带 `DEEPSEEK_API_KEY` 启动（`DEEPSEEK_API_KEY=... uv run werewolf-api --port 8010`）；前端 `VITE_API_PROXY=http://localhost:8010 npm run dev`。Key 无效时对局会以兜底逻辑运行（不报错、但无真发言）。

**边界（本期不做）：** 模式/人数/供应商选择器（后续）；人机对战交互（M3——`humanVsAI` 当前也以全 AI 观战开局）；原始 Key 随请求注入（M3）。

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `frontend/src/api/types.ts` | 增 `StartGameRequest` / `StartGameResponse` | Modify |
| `frontend/src/api/client.ts` | 增 `post<T>` 助手 + `startGame()` | Modify |
| `frontend/src/api/client.startGame.test.ts` | `startGame` 单测（fetch mock） | Create |
| `frontend/src/components/GameSetup.tsx` | `startMatch` 改调真实 startGame + 跳转观战 | Modify |

---

## Task 1: `ApiClient.startGame` + 类型 + 单测

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Test: `frontend/src/api/client.startGame.test.ts`

- [ ] **Step 1: 在 `frontend/src/api/types.ts` 末尾追加类型**

```ts
// --- Start game (mirrors backend StartGameRequest / StartGameResponse) ---
export interface StartGameRequest {
  config_id?: string;
  participation?: string;
  rules?: string;
  player_count?: number;
  badge_flow?: boolean;
}

export interface StartGameResponse {
  run_id: string;
  source: string;
  status: string;
  config_id: string;
  run_dir: string;
  game_page_path: string;
  status_path: string;
  replay_page_path: string;
  player_count?: number | null;
  badge_flow?: boolean;
}
```

- [ ] **Step 2: 写失败测试 `frontend/src/api/client.startGame.test.ts`**

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiClient } from "./client";

describe("ApiClient.startGame", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.unstubAllGlobals());

  it("POSTs to /games/start with JSON body and unwraps the envelope", async () => {
    const data = {
      run_id: "r1", source: "runs", status: "running", config_id: "llm-6p-deepseek",
      run_dir: "x", game_page_path: "/game?run_id=r1&source=runs",
      status_path: "/api/v1/games/r1/status", replay_page_path: "/replay/r1",
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ success: true, data, message: null }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await ApiClient.startGame({ config_id: "llm-6p-deepseek", badge_flow: true });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/v1/games/start");
    expect(opts.method).toBe("POST");
    expect(opts.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(opts.body)).toMatchObject({ config_id: "llm-6p-deepseek", badge_flow: true });
    expect(res.game_page_path).toBe("/game?run_id=r1&source=runs");
  });

  it("throws with the backend detail on error", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false, statusText: "Bad Request", json: async () => ({ detail: "Unknown config_id: nope" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await expect(ApiClient.startGame({ config_id: "nope" })).rejects.toThrow(/Unknown config_id/);
  });
});
```

- [ ] **Step 3: 运行确认失败**

Run: `cd frontend && npx vitest run src/api/client.startGame.test.ts`
Expected: FAIL（`ApiClient.startGame is not a function`）。

- [ ] **Step 4: 在 `frontend/src/api/client.ts` 实现 `post` 助手与 `startGame`**

在 import 段把 `StartGameResponse`、`StartGameRequest` 加入从 `./types` 的导入列表（与现有逐项导入风格一致）。

在 `private static async get<T>` 方法之后、其它静态方法之前，新增：
```ts
  private static async post<T>(url: string, body: unknown): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const j = await response.json();
        detail = (j && (j.detail || j.message)) || detail;
      } catch {
        // non-JSON error body; keep statusText
      }
      throw new Error(`API error POST ${url}: ${detail}`);
    }
    return unwrap<T>(await response.json());
  }

  static async startGame(req: StartGameRequest): Promise<StartGameResponse> {
    return this.post<StartGameResponse>("/api/v1/games/start", req);
  }
```

- [ ] **Step 5: 运行确认通过 + lint**

Run: `cd frontend && npx vitest run src/api/client.startGame.test.ts`
Expected: PASS（2 passed）。
Run: `cd frontend && npm run lint`
Expected: 退出码 0。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/api/client.startGame.test.ts
git commit -m "feat(frontend): ApiClient.startGame -> POST /api/v1/games/start

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `GameSetup` 一键开局 → 跳转观战

**Files:**
- Modify: `frontend/src/components/GameSetup.tsx`

> 先 Read 整个文件，按下述精确改动落地；其余 UI/state 保持不变。

- [ ] **Step 1: 增加 import**

在顶部 import 区加：
```tsx
import { useNavigate } from "react-router-dom";
import { ApiClient } from "../api/client";
```

- [ ] **Step 2: 增加本地状态 + navigate**

在组件内其它 `useState` 附近（如 `const [hasSheriff, ...]` 之后）加：
```tsx
  const navigate = useNavigate();
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
```

- [ ] **Step 3: 重写 `startMatch`（去掉 mock `resetGame`，改真实 startGame + 跳转）**

把现有 `startMatch`（当前内容形如 `setSetupCount(null); await resetGame(userRole, playerCount, gameMode, true, hasSheriff);`）整体替换为：
```tsx
  const startMatch = async () => {
    if (starting) return;
    setStartError(null);
    setStarting(true);
    setSetupCount(null);
    try {
      // 当前一律以全 AI 对局开局并进入实时观战；人机交互在 M3。
      const res = await ApiClient.startGame({
        config_id: "llm-6p-deepseek",
        badge_flow: hasSheriff,
      });
      navigate(res.game_page_path); // "/game?run_id=...&source=runs"
    } catch (e) {
      setStartError(e instanceof Error ? e.message : String(e));
      setStarting(false);
    }
  };
```
> 注：成功跳转后组件卸载，无需复位 `starting`；失败分支已复位并显示错误。`userRole`/`playerCount`/`gameMode` 暂不参与请求（后续接模式/人数选择器）。若 `resetGame` 因此变为未使用且触发 lint 未用变量错误，删除其解构（`const resetGame = useGameStore(...)`）那一行。

- [ ] **Step 4: 开始按钮接本地态 + 显示错误**

把开始按钮的 `disabled={isLoading}` 改为 `disabled={starting}`，按钮文案在 `starting` 时可显示「召唤中…」。在按钮附近（同容器内）加错误提示：
```tsx
              {startError && (
                <p className="mt-2 text-center text-[11px] font-mono text-red-400/90">
                  开局失败：{startError}
                </p>
              )}
```
> 若 `isLoading` 因此变为未使用导致 lint 报错，删除其解构行。

- [ ] **Step 5: 类型检查 + 构建 + 单测**

Run: `cd frontend && npm run lint && npm run test && npm run build`
Expected: tsc 0；vitest 全绿（含 startGame 2 例）；vite build 成功。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/GameSetup.tsx
git commit -m "feat(frontend): start a real game from GameSetup and jump to live spectate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: 真机联调（人工，留人工/我来跑）

- [ ] 起后端：`DEEPSEEK_API_KEY=$(cat <有效key>) OBS_READY_REQUIRE_LLM=0 uv run werewolf-api --port 8010`
- [ ] 起前端：`cd frontend && VITE_API_PROXY=http://localhost:8010 npm run dev`
- [ ] 浏览器开 `http://localhost:5173/`（GameSetup）→ 选「上帝观战模式」→ 点开始 → 应跳到 `/game?run_id=...` 并实时观战（座位/发言/信念矩阵/票型）。
- [ ] 失败路径：后端未带 Key 时对局会标记 failed；选 `nope` 之类错误 config 会显示「开局失败：…」。

---

## Self-Review

**Goal coverage：**
- `ApiClient.startGame`（POST + 解信封 + 抛 detail）→ Task 1 ✅（含 fetch-mock 单测）。
- `GameSetup` 一键真实开局 + 跳转观战，弃用 mock `resetGame` → Task 2 ✅。
- 未覆盖（有意）：模式/人数/供应商选择器、humanVsAI 交互（M3）、原始 Key 注入（M3）。

**Placeholder scan:** 无 TODO/TBD；每个改码步骤给出完整代码或精确替换位置。

**Type consistency:** `StartGameRequest`/`StartGameResponse`(types.ts) ↔ `ApiClient.post<StartGameResponse>` / `startGame` ↔ 测试断言 `game_page_path` ↔ `GameSetup` 用 `res.game_page_path` 跳转；后端 `StartGameResponse.game_page_path = "/game?run_id=...&source=runs"` 与已修的 `/game` 路由一致。

---

## Follow-up
- 模式/人数/供应商选择器（拉 `/games/modes` + 模型列表，让用户选）。
- humanVsAI → M3（座位令牌 + `/games/{id}/input` + `WebHumanAgent` + 固定角色 + 原始 Key 注入）。
- 开局后可显示「正在生成对局…」过渡，或轮询 status 直到首帧事件。
