# MultiAgent-Werewolf 全项目改动主计划（核心重构）

> 版本：2026-05-20
> **权威分工**：规则/可见性 → [project-governance.md](./project-governance.md)；目录 → [project-structure.md](./project-structure.md)；夜间调度 → [adr/0005-night-skill-scheduler.md](./adr/0005-night-skill-scheduler.md)。

## 1. 目标与边界

- **目标**：规则正确、夜间技能可调度、信息隔离闭环、Prompt 单源、UI/评测一致。
- **不含**：Web/FastAPI、信念矩阵、同夜 LLM 并发。

## 2. Phase 0 — 已完成

- [x] 删除 `ActionSelector`；`PhaseInteraction` + `InformationHub` 显式注入
- [x] `event_visibility.py` + `_log_event` 默认规则
- [x] 删除 `discussion_history` 双写

## 3. Phase 1 — 规则与可见性漏洞

- [x] **R1** 天亮救/守公布改公开 `MESSAGE`（`death_handler`）
- [x] **R2** 狼票明细单独 `MESSAGE` + `visibility=wolf_team`
- [x] **R3** 验人 `message` 脱敏（`seer_checked_public`）
- [x] **R4** 评测 `data` 敏感字段检测（`InformationIsolationChecker`）

## 4. Phase 2 — 夜间技能调度

- [x] `core/night_scheduler.py`：pre-wolf → 狼票 → 结算刀口 → 女巫及其他
- [x] `night_phase.py` 两批 `process_actions`
- [x] `tests/core/test_night_scheduler.py`

## 5. Phase 3 — Role 瘦化

- [x] `core/role_night_plans.py`（狼/女巫/守卫/预言家）
- [x] `core/action_registry.py`
- [x] `core/death_abilities.py`

## 6. Phase 4 — Prompt 单源

- [x] Bridge 中文模板 + `GamePrompts` 引用
- [x] `MessageAdapter` 标 deprecated

## 7. Phase 5 — UI 与评测

- [x] `present_event` / `display_event` 支持 `viewer_id`
- [x] CLI `--viewer` 参数

## 8. Phase 6 — 文档同步

- [x] 本文档、`roadmap.md`、`architecture-improvement` 链、ADR-0005
- [x] `test_bridge_parsing.py` 重命名

## 9. 全局验收（DoD）

- [x] 夜晚顺序：守卫等 → 狼票 → 女巫 → 其余
- [x] 女巫在 `werewolf_target` 确定后询问
- [x] 狼票明细不进入公开 `WEREWOLF_KILLED.data`
- [x] 验人结果不在公开 `message`
- [x] UI 支持 `viewer_id` 过滤
- [ ] 扩展狼角色迁入 `role_night_plans`（后续）
- [x] 核心测试：`pytest tests/core tests/adapter tests/evaluation`

## 10. 远期附录

Web 观战、信念矩阵、同夜并发 — 见 [roadmap.md](./roadmap.md)。
