# Evaluation 开发进度

> **模块**：evaluation
> **状态**：active
> **最后更新**：2026-05-28
> **关联代码**：`src/llm_werewolf/evaluation/`
> **关联测试**：`tests/evaluation/`
> **Agent Skill**：`.agents/skills/generated/evaluation/`


## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| PostGame 基础流水线（14 步） | ✅ Done | pipeline + manifest/steps |
| Evaluation v2 Phase 1 | ✅ Done | log_views、intention、role_skills、AgentScope、Skill MD 双写 |
| 离线正确性评测 | ✅ Done | runner + 7 checkers + 2 scenarios |
| Leaderboard / A/B | ✅ Done | entry、聚合、compare、experiment_meta |
| Coach + Episodic | ✅ Done | episodic_bridge、coach_summary.json |
| Evaluation v2 Phase 2 | 🔄 In Progress | benefit 完整规则、信念校准进 PostGame、Skill 闭环证明 |
| Leaderboard Web 展示 | 📋 Planned | 依赖 frontend |

## 已完成

- [x] PostGame pipeline 14 步；必需步仅 `load_context`
- [x] `finalize_run` + `POST /api/v1/runs/{id}/post-game`
- [x] log_views、intention_scores、mvp_scores、benefit_scores（部分）、score_contexts
- [x] vote_swing、camp_persuasion、game_quality_report、LLM replay
- [x] role_skills + 门控双写 `agent_team/skills/`
- [x] prompt_proposals v2、Coach enrich
- [x] Leaderboard CLI 与 skill 版本链推断
- [x] EvaluationRunner：smoke_6p_basic、regression_default_demo

## 进行中

- [ ] `benefit_scores.json` 完整规则（Phase 1 部分占位）
- [ ] 按高分筛选 Skill LLM（Phase 2）
- [ ] 信念校准接入 PostGame 并暴露 replay API
- [ ] 旧文档结论合并进 DESIGN，原文 deprecated
- [ ] Skill 写回 → 下局使用 → 效果对比显式证明

## 计划中

- [ ] PostGame 增量生成（仅缺啥补啥）
- [ ] eval runner 可选真实 LLM + 完整 PostGame
- [ ] Leaderboard 统计显著性分析
- [ ] `invalid_action_count` action validation checker
- [ ] 独立 `werewolf-post-game` CLI
- [ ] Leaderboard 前端可视化

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-05-23 | 初始化 README / DESIGN / ROADMAP 三件套 |
| 2026-05-25 | Evaluation v2 Phase 1 完成 |
| 2026-05-28 | episodic_bridge + Coach episode 证据 |
