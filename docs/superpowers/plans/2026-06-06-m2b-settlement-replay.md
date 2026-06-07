# M2b — 结算 + 复盘真数据接入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 **结算页（GameOverPanel）** 和 **复盘页（ReplayPage 各面板）** 由后端真数据驱动，丢弃 mock。结算：游戏结束后轮询 `GET /api/v1/games/{id}/status` 直到 `has_post_game===true`，再把跳转链指向真实 `/replay/{run_id}`。复盘：`getReplayData` 改请求 `view=god&source=runs`，经新 `replayMap.ts` 把后端 `ReplayPageData` 映射成前端各面板期望的形状。

**Architecture:** 镜像 M2 的 `lib/insightMap.ts` 模式——新增纯函数映射层 `frontend/src/lib/replayMap.ts`（snake→camel、`*100` 概率、`seat→"P{n}"`、防御默认值）+ `ApiClient.getGameStatus` / 改造 `getReplayData`。**最小切片零后端改动**（状态端点与 per-run 复盘端点都已存在）。

**Tech Stack:** React + Zustand + react-router；Vitest（映射纯函数 + fetch-mock 客户端）。

> **执行前置（必读）：** 每个 task 编辑 symbol 前先 `gitnexus_impact`；提交前 `gitnexus_detect_changes`。后端有效 DeepSeek key 见项目记忆。真机联调需带 key 起后端 + `VITE_API_PROXY` 起前端，并先用真 LLM 局跑出 post-game 产物。

---

## 关键后端事实（来自 m2b 探查工作流，已核实文件位置）

- **状态端点**：`GET /api/v1/games/{run_id}/status?source=runs`（`routes/actions.py:146` → `services/game_sessions.py get_status:347`）返回 `GameStatusResponse`（`models/actions.py:113`），含 **`has_post_game`/`has_replay`/`post_game_status`/`status`/`snapshot`/`alert_count`**。`has_post_game` 在 `post_game_manifest.json` 落盘时翻 true（`services/runs.py _scan_run_dir`）。**轮询无需任何后端改动。**
- **复盘端点**：`GET /api/v1/pages/replay?run_id=&source=runs&view=public|god`（`routes/pages.py:149` → `services/pages.py build_replay_page_enriched:387`）。**必须用 `/pages/replay`（enriched），不是 legacy `/replay/{id}`**（后者 mvp_ranking/phase_summary/turning_points 为空）。
- **god 门控**：`belief_snapshots`/`wolf_camp_snapshots`/`belief_heatmap` 仅 `view=god` 时填充（`services/replay.py:183`）。信念矩阵面板**必须请求 `view=god`**。timeline 在非 god 下隐藏 belief/vote-intention 快照事件。
- **已知后端 bug**：`mvp_ranking.total_score` 恒为 `0.0`（`build_mvp_ranking` 读 `"total"/"score"`，真实字段是 `mvp_total`）。**前端 PlayerScore/score 必须从 `scores[kind=="mvp"].payload.data.players[]` 的 `mvp_total`/`breakdown_norm` 取，不要用 `total_score`。**
- **winner_camp 枚举不一致**：后端 `werewolf`/`villager`（小写），前端 `WOLVES`/`VILLAGERS`。映射层统一转换。
- **VoteSwing 数据**在 `scores[kind=="swing"].payload.data.speeches[]`；**PlayerScore 维度**在 `scores[kind=="mvp"].payload.data.players[].breakdown_norm{persuasion,strategy,outcome,wolf_night}`。
- **无后端来源**：`wolf_camp_snapshots`（前端 WolfCampSnapshot 的 campStrategy/target/wolfVotes 在 `wolf_camp_mind.jsonl` 里没有）→ M2b **降级为空**。`belief_matrix_anchors` 需从 `belief_snapshots` 派生（按 `anchor` 分组）。

---

## 推荐路径与默认决策（实施前请用户确认/否决）

1. **结算优先**（settlement-first），再做复盘面板。结算小、后端齐、自包含，立即打通"进结算→进真实复盘"。
2. **PlayerScore 在前端派生**（挖 `scores[kind=="mvp"]`，带防御默认）作为 MVP 切片；"后端加扁平 per-player 数组"列为后续优化。
3. **轮询门控 `has_post_game===true`**；`post_game_status` 为 `partial/failed` 时仍允许进复盘（面板降级），不死等。
4. **复盘恒用 `view=god`**（god 视角复盘，含剧透型 belief；符合"上帝复盘"语义）。视角选择器留作后续。
5. **`wolf_camp_snapshots` 面板 M2b 降级/隐藏**。
6. **结算仅对有 `?run_id=` 的观战/web 局生效**；纯本地局保留现有客户端 MVP 覆盖层。

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `frontend/src/api/types.ts` | 加 `GameStatusResponse`/`GameSnapshot`；加 `Backend*` 复盘输入类型 | Modify |
| `frontend/src/api/client.ts` | 加 `getGameStatus`；改 `getReplayData`（god+source，过 replayMap） | Modify |
| `frontend/src/lib/replayMap.ts` | 后端 `ReplayPageData` → 前端各面板形状（核心胶水，镜像 insightMap.ts） | Create |
| `frontend/src/lib/settlement.ts` | 纯函数 `isPostGameReady` / `replayPathFor` | Create |
| `frontend/src/components/GameOverPanel.tsx` | 接 `runId`，轮询 status，替换 mock 复盘链 | Modify |
| `frontend/src/pages/GameApp.tsx` | 把 `runId` 透传给 GameOverPanel | Modify |
| `frontend/src/pages/ReplayPage.tsx` | （可选）动态天数/座位，wolf_camp 降级 | Modify |

---

## Task 1: `getGameStatus` 客户端 + 状态类型

**Files:** Modify `frontend/src/api/types.ts`, `frontend/src/api/client.ts`; Test `frontend/src/api/client.getGameStatus.test.ts`

- [ ] Step 1: 在 `types.ts` 加 `GameSnapshot`（phase/round_number/winner_camp:"werewolf"|"villager"|null/is_ended/sheriff_id/alive_count/dead_count/event_count）与 `GameStatusResponse`（run_id/source/status/snapshot/error/result_text/has_post_game/has_replay/post_game_status/alert_count），镜像 `models/actions.py:113`。
- [ ] Step 2: 写失败测试：stub fetch，断言 URL 含 `/api/v1/games/run1/status?source=runs`、解信封后 `has_post_game` 可读。Run `npx vitest run src/api/client.getGameStatus.test.ts` → FAIL。
- [ ] Step 3: 实现 `static async getGameStatus(runId, source="runs")` → 复用现有 `get<T>`（已解 `{data}` 信封）。
- [ ] Step 4: 测试 PASS + `npm run lint`。
- [ ] Step 5: Commit。

## Task 2: 结算助手 + GameOverPanel 轮询 + 真复盘链

**Files:** Create `frontend/src/lib/settlement.ts` + `.test.ts`; Modify `frontend/src/components/GameOverPanel.tsx`, `frontend/src/pages/GameApp.tsx`

- [ ] Step 1: 写失败测试 `settlement.test.ts`：纯函数 `isPostGameReady(status)`（`has_post_game===true`）与 `replayPathFor(runId)`（`/replay/${runId}`）。
- [ ] Step 2: 实现这两个纯函数；测试 PASS。
- [ ] Step 3: `GameOverPanel` 加可选 `runId` prop；用 `useEffect` 轮询 `getGameStatus`（间隔 ~2.5s，组件卸载清除定时器），ready 后启用"查看本局高维深度复盘"链并指向 `replayPathFor(runId)`（替换 `GameOverPanel.tsx:372-378` 的假 `/replay/run-gameover-${winner}`）。保留 `calculateMVP` 作为覆盖层。无 `runId` 时维持现状（本地局）。
- [ ] Step 4: `GameApp.tsx` 把 `runId`（来自 `useSearchParams`）传给 `<GameOverPanel>`。
- [ ] Step 5: `npm run lint && npm run test && npm run build` 全绿。
- [ ] Step 6: Commit。

## Task 3: 复盘输入类型 + `mapRunInfo` + `mapTimeline`

**Files:** Create `frontend/src/lib/replayMap.ts` + `.test.ts`; Modify `frontend/src/api/types.ts`

- [ ] Step 1: 在 types.ts 加 `Backend`-前缀输入类型（`BackendReplayPageData`/`BackendRunDetail`/`BackendReplayEventItem`/`BackendMvpRankItem`/`BackendScoreBlock`…），镜像 `models/pages.py`。
- [ ] Step 2: 写失败测试：`mapRunInfo`（id←run_id、date←created_at、initial_players←player_count、winner_camp `werewolf→WOLVES`/`villager→VILLAGERS`）；`mapTimeline`（id←String(index)、day←round_number、isNight←phase.startsWith("NIGHT")、title/description/type←event_type+data 派生，**过滤 belief/vote 快照事件**）。
- [ ] Step 3: 实现；测试 PASS + lint。Commit。

## Task 4: `mapMvpRanking`/`mapTurningPoints`/`mapReplayPage` + god 视角接线

**Files:** Modify `frontend/src/lib/replayMap.ts` (+test), `frontend/src/api/client.ts` (+`client.replay.test.ts`)

- [ ] Step 1: 失败测试：`mapMvpRanking`（playerId←int(player_id)、score←**从 mvp 块的 mvp_total**、isMvp←rank===1、contributionDesc←golden_speech 摘要或空）；`mapTurningPoints`（`string[]` → `{day:0,title:line,desc:line}`）；`mapReplayPage`（组装全部字段，缺失给空数组）。
- [ ] Step 2: 失败测试：`getReplayData` 断言请求带 `run_id`、`source=runs`、`view=god`，并对响应跑 `mapReplayPage`。
- [ ] Step 3: 实现；PASS + lint。Commit。

## Task 5: `mapPlayerScores`（最难的 gap）

**Files:** Modify `frontend/src/lib/replayMap.ts` (+test)

- [ ] Step 1: 失败测试：`mapPlayerScores` 从 `scores[kind=="mvp"].payload.data.players[]` 取 `breakdown_norm`：`logicSpeechScore←persuasion`、`deceptionMisleaderScore←wolf_night`、`cooperationRate←strategy`、`gameSurvivalScore←outcome`、`totalScore←mvp_total`；`isAlive` 从 `run.roster` join；无 mvp 块返回 `[]`。维度映射用具名常量隔离（便于改）。
- [ ] Step 2: 实现；PASS + lint。Commit。

## Task 6: `mapVoteSwing`

**Files:** Modify `frontend/src/lib/replayMap.ts` (+test)

- [ ] Step 1: 失败测试：从 `scores[kind=="swing"].payload.data.speeches[]` 映射：id←`${speaker_id}-${round_number}`、round←round_number、edges←swings（voter_id←player_id、from_target←from_target_name、to_target←to_target_name）、speaker_role/camp 从 mvp players join；无 swing 块返回 `[]`。
- [ ] Step 2: 实现；PASS + lint。Commit。

## Task 7: god 信念矩阵映射 + wolf_camp 降级

**Files:** Modify `frontend/src/lib/replayMap.ts` (+test), `frontend/src/pages/ReplayPage.tsx`

- [ ] Step 1: 失败测试：`mapBeliefAnchors`（按 `anchor` 分组 `belief_snapshots`，seat number→`"P{n}"`，observers/targets 重组）；`mapBeliefColumns`（`wolf_probability*100`，注意 types.ts 与 insightTypes.ts 的 `BeliefSnapshot` 同名异形）；`mapWolfCampSnapshots` 返回 `[]`（降级）。
- [ ] Step 2: 实现；（可选）ReplayPage 天数选项改为从 timeline 动态推导。PASS + lint。Commit。

---

## Self-Review

- **Goal 覆盖**：结算轮询(Task1-2) ✅；复盘 header/timeline/MVP/turning_points(Task3-4) ✅；PlayerScore(Task5) ✅；VoteSwing(Task6) ✅；信念矩阵 god(Task7) ✅。
- **零后端改动** 满足最小切片；后续可选"后端加扁平 per-player 分数数组"消除 Task5 的脆弱挖取。
- **类型一致**：`Backend*` 输入类型 ↔ 各 `map*` 纯函数 ↔ 现有前端面板 props。
- **契约风险**：god 视角会把 belief/vote 事件混进 timeline → `mapTimeline` 必须过滤（risk 已列）。`mvp_ranking.total_score=0.0` 已绕开。

## Open Questions（实施前需用户拍板）

1. **结算优先 vs 复盘优先？**（推荐结算优先）
2. **PlayerScore 前端挖取 vs 后端加扁平数组？**（推荐前端挖取做 MVP，后端转换列后续）
3. **轮询门控 `has_post_game` vs `post_game_status==='ok'`？partial/failed 是否仍可进复盘（降级）？**（推荐 has_post_game + 允许降级）
4. **复盘恒 god 视角 vs 尊重视角选择器（god/public/P1..P6 + viewer_id）？**（推荐恒 god）
5. **`wolf_camp_snapshots` 面板 M2b 降级隐藏 vs 投入从 night-kill/wolf-vote 事件派生？**（推荐降级）
6. 4 维分数语义标签（persuasion/wolf_night/strategy/outcome → 逻辑/伪装/协作/生存）是否认可？

## Follow-up
- 后端 `build_mvp_ranking` 的 `total_score=0.0` bug 单独修（读 `mvp_total`）。
- 后端可选新增扁平 per-player 分数数组，消除前端对 mvp_scores 内部结构的依赖。
- ReplayPage 的 seat 选择器、`DEEPSEEK-V4-FLASH` 静态标签、天数硬编码 → 接真实 roster/model/天数。
