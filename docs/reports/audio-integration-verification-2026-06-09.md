# 音效集成验证记录 — 2026-06-09

> **分支**：`feature/audio-integration`（worktree：`.claude/worktrees/audio-integration`）
> **基线**：WIP 快照 `fbf33bf`（含未提交的 seat-ui/god-role 基础）
> **计划**：`docs/superpowers/plans/2026-06-09-audio-integration.md`

## 自动化验证（本会话已完成）

| 项 | 结果 |
|---|---|
| 单元测试 `npx vitest run` | ✅ **218 通过 / 0 失败**（33 个文件） |
| 新增测试 | soundMap 10、soundManager 2、castMap +4、store 座位音 +2 |
| 类型检查 `npx tsc --noEmit` | ✅ 干净（0 错误） |
| 生产构建 `npm run build` | ✅ 10.4s 成功 |
| 音频资产 | ✅ 36 个 `public/audio/*.mp3` → 已打进 `dist/audio`（36） |
| 新代码 eslint | ✅ 改动文件无新增 error（仓库 62 个 error/98 warning 均为既有，未引入） |

## 实现要点核对

- 技能音：`store.onmessage` → `effectTypeForEvent`→`effectTypeSfx` 派发，座位流按可见性天然不泄漏。
- 事件音：`eventSfx`（死亡/放逐/计票/警长/胜负/开局/殉情/平票），`game_ended` 按 `winner_camp` 分好人/狼人。
- 昼夜转场：`GameAudioBridge` 订阅 `stageFx`（复用 `PhaseTransitionCard` 突发抑制）。
- 座位音：`your_turn`/`timeout`（`ingestSeatEvent`）、`submit`+本人技能（`submitHumanInput`）、`tick`（SeatCommandDock ≤10s）。
- UI 音：TopHeader 静音键+音量滑块（持久化 `ww_audio`）、InsightDock 3 个面板开合、SeatCommandDock 目标卡 click。
- 防护：burst 门（700ms/3）、`event_id` 去重、首次手势解锁、缺文件→合成兜底→静默；BGM 总线占位增益 0。
- CastSkillOverlay 改为视觉专用（移除 6 个合成音调用）。

## 范围外（本期未做，按 spec §3.6）

- `event_shield_break`（缺明确引擎事件触发，资产已就位待挂）
- 5 段 BGM（未生成）、`ui_hover` 广接

## 待人工验证（交互式浏览器 e2e，本会话未跑）

需起后端 + 前端 + 浏览器实际听音，建议按计划 Task 10 走一遍：

1. `OBS_READY_REQUIRE_LLM=0 uv run werewolf-api --port 8010` + `cd frontend && npm run dev`
2. **god 观战**：首次点击解锁后，确认昼夜转场音、技能音（与塔罗动画同步）、死亡/放逐/计票/警长/胜负音；中途加入对局无"机关枪"。
3. **座位人机**（`human-6p-demo`）：`your_turn`/`tick`/`timeout`/`submit`/本人技能音；**他人技能不出声**。
4. **控制**：静音键/音量滑块即时生效且刷新后保持。
5. **兜底**：临时改名某 mp3 → 不报错（静默或合成兜底）。

> 结论：代码层面集成完整、类型与构建均通过、单测全绿；仅"真听一遍"的人工 e2e 留待运行环境就绪时执行。
