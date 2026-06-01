# Evaluation 设计

> **模块**：evaluation
> **状态**：active
> **最后更新**：2026-05-23
> **关联代码**：`src/llm_werewolf/evaluation/`
> **关联测试**：`tests/evaluation/`
> **Agent Skill**：`.agents/skills/generated/evaluation/`


## 1. 目标

对局结束后产出可复用的分析资产：时间线视图、多维评分、信念校准、LLM 复盘、Prompt 提案、角色 Skill 与 Coach 报告；离线批量评测验证系统正确性并支撑版本演进对比。

## 2. 范围

### 做

- 从 `artifacts/runs/<run_id>/` 或 `eval_runs/<name>/games/<id>/` 读取事件、投票意向、信念日志
- 跑 PostGame pipeline（分步 try/except，单步失败不阻断独立步骤）
- 写入 report、scores、skills、manifest 等产物
- Leaderboard 聚合与 A/B 对比，挂接 Skill 版本链
- 将通过质量门控的 Skill 双写至 `agent_team/skills/<prompt_role_key>/`

### 不做

- 不修改对局进行中的 `GameState`
- 不在此模块直接调用 LLM 做局内决策（局内归 `agent_team`）
- 不直接替换运行时 Prompt（`apply_policy: json_only_no_runtime_replace`）
- 评测 LLM 统一经 AgentScope，不新增 OpenAI SDK 旁路

## 3. 核心流程

```text
game_runtime 事件/日志 + vote_intentions + beliefs.jsonl
    → interface.finalize_run（persist_run_artifacts + run_post_game_pipeline）
    → evaluation/post_game/pipeline（14 步）
    → 产物：post_game_manifest.json、scores、views/、skills/、coach_summary.json ...
    → agent_team/skill_loader 读取 agent_team/skills/
```

## 4. PostGame 流水线步骤

编排位于 `post_game/pipeline.py`；步骤状态写入 `post_game_steps.json`，总索引写入 `post_game_manifest.json`。仅 `load_context` 为必需步骤。

| step_id | 类型 | 主要产物 | 说明 |
|---------|------|----------|------|
| `load_context` | 规则 | — | 加载 `RunContext`；**必需** |
| `episodic` | 规则 | `episodic_reports.json` | 与运行时 EpisodicMemory 同源 |
| `vote_swing` | 规则 | `vote_swing_report.md`, `vote_swing_summary.json` | 投票意向变化分析 |
| `camp_persuasion` | 规则 | `camp_persuasion_report.md`, `camp_persuasion_summary.json` | 阵营说服收益 |
| `log_views` | 规则 | `views/`, `views_manifest.json` | POV / digest 视图 |
| `intention_scores` | 规则 | `intention_scores.json` | 意向改变分 |
| `score_contexts` | 规则 | `views/score_contexts/` | 评分上下文 |
| `mvp_scores` | 规则 | `mvp_scores.json` | MVP 与多维评分 |
| `benefit_scores` | 规则 | `benefit_scores.json` | 收益分（Phase 1 部分规则） |
| `llm_replay` | LLM | `post_game_analysis.json`, `post_game_report.md` | AgentScope 复盘 |
| `game_quality_report` | 规则 | `game_quality_report.md`, `.json` | 局质量总览 |
| `prompt_proposals` | 规则+LLM | `prompt_proposals.json` | Prompt 优化提案 |
| `role_skills` | 规则+LLM | `role_skills.json`, `skills/` | Skill 提取与 MD |
| `coach` | 规则 | `coach_summary.json` | Coach enrich |

`camp_persuasion` 失败会跳过依赖 `camp_report` 的步骤（`log_views` → `coach`）；`episodic`、`vote_swing`、`game_quality_report` 仍会执行。

## 5. 离线评测 Runner 与 Checkers

`EvaluationRunner`（`core/runner.py`）使用 `DemoAgent`；每局结束后仍会跑 PostGame，但 `skip_llm=True`（跳过 `llm_replay` 等 LLM 步骤）。

| Checker | 检查内容 |
|---------|----------|
| `RoleSkillChecker` | 角色动作事件结构化字段 |
| `InformationIsolationChecker` | 私有事件信息隔离 |
| `VictoryCheckerEvaluator` | 胜负判定一致性 |
| `AsyncFlowChecker` | 阶段流转顺序 |
| `PromptBadCaseChecker` | Prompt 调优 bad case |
| `DecisionConsistencyChecker` | 决策与事件一致性 |
| `RuntimeErrorEventChecker` | 将 `EventType.ERROR` 归入评测失败项（runner 内联，非独立类） |

内置场景：`smoke_6p_basic`、`regression_default_demo`。

## 6. 关键产物与 Skill 写回

- 单场 PostGame：`post_game_manifest.json`、`post_game_steps.json`、评分 JSON、views/、`role_skills.json`、`coach_summary.json` 等
- `write_role_skills_artifacts`：写出 run 目录 Skill MD；门控通过者双写 `agent_team/skills/<role>/<skill_id>.md`；pipeline 结束 `skill_loader.list_role_skill_files.cache_clear()`
- Leaderboard：`leaderboard_entry.json`、`experiment_meta.json`、聚合 `leaderboards/`、对比 `ab_reports/`、`skill_snapshot.json`、`skill_diff.json`

## 7. 信念校准（Belief Calibration）

`scoring/belief_calibration.py` 的 `compute_belief_brier_scores` 从 `beliefs.jsonl` 计算 `wolf_probability` 的 Brier score（schema: `belief_calibration_v1`）。**已实现，尚未接入 PostGame pipeline**，也未写入 replay API 字段。

## 8. 接口与入口

| 入口 | 说明 |
|------|------|
| `finalize_run` | `interface/cli/runtime/finalize_run.py` |
| `POST /api/v1/runs/{run_id}/post-game` | `game_session_manager.trigger_post_game` |
| `werewolf-eval` | 批量离线评测 CLI |
| `llm_werewolf.evaluation.leaderboard.cli` | entry / build / compare |

## 9. 依赖与边界

- `evaluation → game_runtime, strategy, agent_team`
- `evaluation` 可写入 `agent_team/skills/`；`agent_team` 只读加载
- 分数由规则层计算，LLM 负责复盘文案与 Skill 提取

## 10. 相关文档

- [ROADMAP.md](./ROADMAP.md)
- [PostGame产物地图.md](./PostGame产物地图.md)
- [Leaderboard与AB对比说明.md](./Leaderboard与AB对比说明.md)
- [吕祎晗-评测模块优化设计.md](./吕祎晗-评测模块优化设计.md)
