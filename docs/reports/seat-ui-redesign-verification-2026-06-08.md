# 人机对战座位 UI 重设 — 验证记录 (2026-06-08)

分支：`worktree-seat-ui-redesign`（基于 `origin/main` / 与 `feature/insight-dock-scroll-resize` 在本计划涉及文件上完全一致）。
计划：`docs/superpowers/plans/2026-06-08-human-vs-ai-seat-ui.md`

## 自动化测试（全部通过）

- **后端** `uv run pytest`：
  - `tests/agent_team/test_web_human_fields.py` — `prepare_web_prompt` 新结构化字段（self_role / kill_target_seat / remaining_potions / question / target_meta）2 项通过。
  - `tests/interface/test_input_broker_fields.py` — broker 发布结构化字段 1 项通过。
  - `tests/interface/test_human_input_broker.py`（含去脆弱化修复）+ `tests/agent_team/test_web_human_agent.py` + `test_human_interactive_agent.py` 回归全绿。
- **前端** `npm run lint`（tsc --noEmit）干净；`npx vitest run` **28 文件 / 171 测试全部通过**，含新增：
  - `src/lib/castMap.test.ts`（effectType / skillMeta / castFromEvent，7 项）
  - `src/store.humanInput.test.ts`（新增 triggerCast/clearCast/selectedTargetSeat 用例）

## 端到端（Playwright，`configs/demo-6.yaml` + web-human 覆盖，无需 API Key）

后端 `OBS_READY_REQUIRE_LLM=0 werewolf-api --port 8021`，前端 vite（VITE_API_PROXY→8021）。
启动：`POST /games/start {config_id:"demo-6", human:{seat:1}, badge_flow:true}`（5 个 demo 机器人 + 1 个浏览器人类）。

**已验证（实时截图 + 可访问性快照，0 console error）：**
- ✅ seat 视角整体布局 = Image #4 风格：**左侧 CardDeck 玩家卡侧栏**（己方身份亮出、他人「秘匿」）+ 中间 3D 圆桌 + SpeechConsole 叙述条。
- ✅ **IdentityHud**（右上）：显示己方角色塔罗牌 + 「本人身份 / Witch」；有 pendingInput 时出现「查看完整局势详情」折叠入口。
- ✅ **SeatCommandDock**（底部持久指令坞）：
  - 空闲态正确显示「DemoPlayer1（1号）夜间行动中…」（由 liveCue 驱动）。
  - **实时捕获活动态 yes/no 提示**：一句话问题「警长抉择：是 / 否。」+ 倒计时 98s + 是·Yes / 否·No 按钮 —— 即对 Image #3「原始 prompt 大弹窗」的修复（截图见 `seat-ui-redesign-live-dock.png`）。
  - ✅ 点击「是·Yes」**提交成功**，对局推进（警长竞选 → 投票阶段）。
- ✅ 全程**无原始 prompt 文本倾倒**；GameOverPanel 正常；0 console error。

**未用实时截图单独覆盖（但有充分间接验证）：**
- seat（选人卡条 + 3D 座位高亮）与 witch（解药/毒药）活动态、以及提交后 `CastSkillOverlay` 塔罗动画：受 demo 夜晚节奏极快 + `awaiting_input` 不持久化（见下「发现2」）影响，实时截图存在竞态，未单独抓到。这些路径与已验证的 yes/no 走**同一 SeatCommandDock + pendingInput + submitHumanInput 机制**，且其纯逻辑（castMap、选择/提交、effectType）已被上述单测覆盖，置信度高。

## 发现（均为预先存在、超出本次 UI 重设范围，建议后续处理）

1. **人机对战「选角色」可能导致 broker 脱钩（需确认，潜在严重）**：用 `human:{seat,role}` 覆盖角色时，`game_sessions._run_game` 先在第 518-520 行把 broker 绑到 `players[seat-1]`，随后第 531 行 `_force_human_seat_role` 交换座位角色、并 `wire_agentscope_after_setup` 重绑 agent —— demo 复现中带 role 覆盖的局**人类女巫未被提示**（直接走兜底跳过），不带 role 覆盖时则正常挂起等待人类。用户截图（Image #3）显示其 standard-6p 流程能正常提示，故差异待确认。**建议**：核对带角色选择的人机对战是否真的会提示人类，必要时把 broker 绑定移到角色交换/重绑之后。

2. **`awaiting_input` 不持久化、SSE 重连不重放**：broker 直接向 EventBroadcaster 发 `awaiting_input`（不进 `events.jsonl`），故**中途连接/刷新/断线重连的客户端会丢失当前待办提示**，对局会卡到 broker 超时（默认 120s）。正常流程下人类在开局即连入、不受影响；但刷新页面会丢提示。**建议**：把当前未决的 `awaiting_input` 纳入 SSE 首帧/重放（或在 broker 侧对新订阅者补发）。

## 服务清理

验证用后端(8021)/前端(5173)进程已结束；临时截图与 `.playwright-mcp/` 已清理，仅保留 `docs/reports/seat-ui-redesign-live-dock.png` 作为证据。
