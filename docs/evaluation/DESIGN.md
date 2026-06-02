# Evaluation 设计

> **模块**：evaluation
> **状态**：active
> **最后更新**：2026-06-02
> **关联代码**：`src/llm_werewolf/evaluation/`
> **关联测试**：`tests/evaluation/`
> **Agent Skill**：`.agents/skills/generated/evaluation/`

## 1. 目标

对局结束后产出可复用的分析资产，并支撑离线正确性验证与版本演进对比：

- 时间线视图（POV / digest）、多维评分、信念校准、LLM 复盘
- Prompt 提案、角色 Skill、Coach 报告
- Leaderboard 聚合与 A/B 对比（含 Wilson CI、z 检验）
- 自进化 runner：manifest 继承、per-role prompt/skill 版本 bump

**设计原则**：评测 LLM 统一经 AgentScope；分数由规则层计算；不直接覆盖运行时 Prompt（`json_only_no_runtime_replace`）。

## 2. 范围

### 做

- 从 `artifacts/runs/<run_id>/` 或 `eval_runs/<name>/games/<id>/` 读取事件、投票意向、信念日志
- PostGame pipeline（14 步，分步 try/except）
- log_views POV 切片、scoring、Skill 提取与 MD 双写
- Leaderboard / A/B / evolution 多轮闭环
- 写 `agent_team/skills/<role>/<skill_version>/`（写前 bump 版本目录）

### 不做

- 不修改对局进行中的 `GameState`
- 不做局内 LLM 决策（归 `agent_team`）
- 不自动回写 Prompt YAML（合并走 `prompt_evolver` + 人工审核）
- 不新增 OpenAI SDK 旁路

### 模块边界

| 模块           | 职责                                         | 禁止                              |
| -------------- | -------------------------------------------- | --------------------------------- |
| `evaluation`   | 赛后流水线、视图、打分、JSON 产物、批量 eval | 直接 AsyncOpenAI；改运行时 Prompt |
| `agent_team`   | Evaluation ReActAgent 工厂；Skill 只读加载   | 评测 Prompt 散落 factory          |
| `strategy`     | 复盘/Skill 输出 Schema                       | 评测业务逻辑                      |
| `game_runtime` | `visible_to`、observation（只读复用）        | PostGame 逻辑                     |
| `interface`    | `finalize_run` 触发 PostGame                 | —                                 |

## 3. 核心流程

```text
game_runtime 事件/日志 + vote_intentions + beliefs.jsonl
    → interface.finalize_run
    → post_game/pipeline（14 步）
    → 产物 → agent_team/skill_loader 读 skills/<role>/<version>/
```

自进化：

```text
run_evolution_cycle → 评测 + PostGame + prompt_evolver
    → version_manifest.json (v2) → restore_runtime_from_manifest
    → leaderboards/ + ab_reports/ + evolution_summary.json
```

## 4. 关键概念

| 概念                | 说明                                                  |
| ------------------- | ----------------------------------------------------- |
| PostGame            | `post_game/pipeline.py` 单场赛后流水线                |
| RunContext          | roster、events、prompt_version；`run_context.py`      |
| Evaluation Analyst  | 单 ReActAgent，经 `eval_agent.py` + factory 创建；结构化输出解析与对局 Agent 对齐 |
| Coach               | enrich Skill、skill_snapshot/diff；`post_game/coach/` |
| log_views           | 按 `visible_to` 的 POV / digest                       |
| RoleVersionManifest | per-role prompt/skill 版本；默认 latest               |
| experiment_meta     | 版本链锚点（previous_run_dir 等）                     |

## 5. PostGame 流水线

| step_id               | 类型     | 主要产物                                         |
| --------------------- | -------- | ------------------------------------------------ |
| `load_context`        | 规则     | —（**必需**）                                    |
| `episodic`            | 规则     | `episodic_reports.json`                          |
| `vote_swing`          | 规则     | `vote_swing_report.md`, `.json`                  |
| `camp_persuasion`     | 规则     | `camp_persuasion_report.md`, `.json`             |
| `log_views`           | 规则     | `views/`, `views_manifest.json`                  |
| `intention_scores`    | 规则     | `intention_scores.json`                          |
| `score_contexts`      | 规则     | `views/score_contexts/`                          |
| `mvp_scores`          | 规则     | `mvp_scores.json`                                |
| `benefit_scores`      | 规则     | `benefit_scores.json`（部分占位）                |
| `llm_replay`          | LLM      | `post_game_analysis.json`, `post_game_report.md` |
| `game_quality_report` | 规则     | `game_quality_report.*`                          |
| `prompt_proposals`    | 规则+LLM | `prompt_proposals.json`                          |
| `role_skills`         | 规则+LLM | `role_skills.json`, `skills/`                    |
| `coach`               | 规则     | `coach_summary.json`                             |

`camp_persuasion` 失败会跳过 `log_views` → `coach`；`episodic`、`vote_swing`、`game_quality_report` 仍执行。

### 5.1 `llm_replay` / eval_agent 结构化输出

Evaluation Analyst 经 `run_eval_replay` 调用 `create_react_agent` + `structured_model=ReplayAnalysisDecision`。Doubao 等 OpenAI 兼容端点常只返回 `generate_response` 的 `tool_use`，而不写入 `Msg.metadata.structured_output`；若仅读 metadata 会误判为 `empty eval agent response`。

`eval_agent._parse_replay_decision` 按下列顺序恢复 `ReplayAnalysisDecision`（与对局 `AgentScopeWerewolfAgent.get_structured_response` 同源工具）：

1. `unwrap_structured_metadata(metadata)`
2. `_extract_structured_payload_from_content(content)` — 从 `tool_use.generate_response.input` 取 JSON
3. 文本 JSON — `_extract_text` 优先 `get_text_content()`，跳过 thinking 与占位 `"Structured response submitted."`

用户 prompt 附加 `generate_response_instruction('ReplayAnalysisDecision')`，与对局 structured 调用一致。

| `post_game_analysis.json.mode` | 含义 |
| ------------------------------ | ---- |
| `llm`                          | 解析成功，字段来自 LLM |
| `failed`                       | 解析或调用失败；`summary_zh` 降级为 `build_rule_summary_zh`（规则转折点） |
| `skipped`                      | 无 API 配置或 key（`no_api_config_or_key`） |

**情景记忆**：`episodic_bridge.py` 复用运行时 `EpisodicMemory` API；Coach 为 Skill 附加 `evidence.episodic_excerpt`。

## 6. log_views

| 视图 ID                     | 读者         | 用途                                    |
| --------------------------- | ------------ | --------------------------------------- |
| `god`                       | 裁判/评测    | 全量 events（可 strip thinking）        |
| `player:{id}`               | 当局 POV     | `visible_to` 过滤时间线                 |
| `role:{prompt_key}`         | 同身份       | 按身份聚合 POV                          |
| `camp:{werewolf\|villager}` | 阵营         | 公开 + 阵营可见私密                     |
| `public_digest`             | LLM 默认输入 | Token 最省摘要                          |
| `swing_digest`              | LLM 输入     | vote_swing + camp_persuasion 高影响条目 |

产物：`views/god_timeline.md`、`player_*_timeline.md`、`public_digest.md`、`swing_digest.json`、`views_manifest.json`。

Token 控制：截断超长 message；剔除 thinking dump；超预算保留死亡、投票、技能结果、发言、意向快照。

## 7. 打分体系

**规则先算、LLM 后解释**；阵营相对；Phase 1 全量 Skill 提取，Phase 2 再按分筛选。

### 7.1 Intention Score

基于 `vote_swing` + `camp_persuasion`：`swing_count`、`camp_aligned_swings`、`matched_elimination`、`swing_to_final_vote`、`persuasion_net` → `intention_scores.json`。

### 7.2 Benefit Score

按玩家聚合阵营收益（夜间击杀、放逐、技能、说服、胜负等）→ `benefit_scores.json`。Phase 1 仅部分规则（`game_won`、`elimination_aligned`、`camp_persuasion_sum` 占位）。

### 7.3 与 Skill 提取

| 阶段            | 策略                                                 |
| --------------- | ---------------------------------------------------- |
| Phase 1（当前） | 每 `prompt_role_key` 有素材则提取；无则 `skipped`    |
| Phase 2         | 仅 `benefit_total >= T` 或 `intention >= T` 进入 LLM |
| Phase 3         | Skill 写入 strategy 版本库（JSON draft）             |

## 8. JSON 产物 Schema 要点

### 8.1 `prompt_proposals.json`

Schema `prompt_proposals_v3`：`proposals[]` 含 `kind`（`positive_persuasion` / `bad_case_rule` / `mvp_golden_quote` 等）、`suggested_patch`、`prompt_role_key`、`apply_policy: json_only_no_runtime_replace`。

### 8.2 `role_skills.json`

Schema `role_skills_v1`：`skills[]` 含 `skill_id`、`prompt_role_key`、`status`、`quality_gate`、`skill_card`、`evidence`；按 `PromptManager.get_prompt_role_key` 分桶。

**质量门（Phase 1）**：该身份有 ≥1 条有效发言或夜间决策 → 进入提取；全程空发言 → `skipped`。

## 9. PostGame 产物详表

| 产物                                  | 生成器            | 消费方                       |
| ------------------------------------- | ----------------- | ---------------------------- |
| `post_game_manifest.json`             | pipeline          | 索引、backfill、前端         |
| `events.jsonl`                        | EventLogger       | PostGame、views、Skill       |
| `post_game_analysis.json`             | eval_agent        | report、proposals            |
| `benefit_scores.json`                 | scoring/benefit   | leaderboard                  |
| `intention_scores.json`               | scoring/intention | leaderboard                  |
| `camp_persuasion_summary.json`        | camp_persuasion   | Skill 提取                   |
| `role_skills.json`                    | skill_extractor   | MD、Coach                    |
| `skills/*.md`                         | skill_md          | 本局归档                     |
| `agent_team/skills/<role>/<ver>/*.md` | skill_extractor   | runtime prompt               |
| `prompt_proposals.json`               | prompt_proposal   | evolver / 人工               |
| `coach_summary.json`                  | coach             | 版本链                       |
| `skill_snapshot.json`                 | coach             | 下一版 diff、experiment_meta |
| `skill_diff.json`                     | coach             | 进化报告                     |
| `leaderboard_entry.json`              | entry_builder     | 聚合、A/B                    |
| `experiment_meta.json`                | entry_builder     | 版本链、Coach 上一版         |
| `version_manifest.json`               | version_manifest  | 进化继承                     |
| `counterfactual_report.*`             | counterfactual    | 答辩、评分                   |

**生命周期**：

```text
events.jsonl → PostGame → scores / views / role_skills / proposals / coach
    → leaderboard_entry + experiment_meta → leaderboards / ab_reports
    → skills MD → agent_team/skills/<role>/<version>/
```

## 10. Skill 写回与状态

| status       | 运行时默认加载                               |
| ------------ | -------------------------------------------- |
| `active`     | 是                                           |
| `draft`      | 否（PostGame 写库默认 draft，审核后 active） |
| `deprecated` | 否                                           |
| `skipped`    | 不写 MD                                      |

写库：`next_skill_version()` → 复制旧版 → 追加新 MD → 更新 manifest。权重 `>= 1.05` 可升 active；`<= 0.95` 可降 deprecated。

**仍待证明**：下局 prompt 中 Skill 使用痕迹、写回前后 A/B 胜率（见 ROADMAP）。

## 11. Leaderboard 与 A/B

产物：`leaderboard_entry.json`、`experiment_meta.json`、`leaderboards/*`、`ab_reports/*`。

Coach 上一版快照顺序：`skill_snapshot.previous.json` → `experiment_meta.previous_skill_snapshot_path` → `previous_run_dir/skill_snapshot.json` → 同级最近有效 run。

```bash
uv run python -m llm_werewolf.evaluation.leaderboard.cli entry <run_dir> --version-id <id> ...
uv run python -m llm_werewolf.evaluation.leaderboard.cli build eval_runs
uv run python -m llm_werewolf.evaluation.leaderboard.cli compare <a.json> <b.json>
```

`win_rate` = 有 `winner_camp` 的局占比，非阵营胜率。A/B 含 Wilson 95% CI、`p-value`、`win_rate_significant`。

## 12. 自进化闭环

**一版 Agent**：per-role prompt/skill、`memory_runtime_params`、`model_config`。

**每轮**：`restore_runtime_from_manifest` → 评测 → `evolve_prompt_from_run`（按身份 bump）→ 写 `version_manifest.json` → 更新 `role_manifest`。

**验收**：`smoke_6p_basic`；≥2 轮；`v1_initial` vs 终局；完成率不降；硬约束无新增失败；终局指标优于初始；存在 A/B 报告。

**已纳入**：prompt version chain、Wilson CI、z 检验、evolution matrix。**暂不做**：自动回滚、LLM 自动采纳 proposal、多模型混跑统一显著性。

## 13. 反事实推演

`post_game/counterfactual.py`：近票差放逐、狼刀换人、预言家查验等规则型 case；不重跑整局。

## 14. 离线评测 Runner

`EvaluationRunner` + DemoAgent；PostGame `skip_llm=True`。Checkers：RoleSkill、InformationIsolation、Victory、AsyncFlow、PromptBadCase、DecisionConsistency、RuntimeError。

场景：`smoke_6p_basic`、`regression_default_demo`。

## 15. 信念校准

`belief_calibration.py`：Brier score（`belief_calibration_v1`）。**未接入 PostGame**，未暴露 replay API。

## 16. 接口与入口

| 入口                               | 说明                    |
| ---------------------------------- | ----------------------- |
| `finalize_run`                     | 对局结束自动 PostGame   |
| `POST /api/v1/runs/{id}/post-game` | API 重跑                |
| `werewolf-eval`                    | 批量离线评测            |
| `leaderboard.cli`                  | entry / build / compare |
| `run_evolution_cycle`              | 多轮自进化              |
| `interface.cli.evidence`           | 答辩评分证据包          |

证据包命令：

```bash
uv run python -m llm_werewolf.interface.cli.evidence \
    --eval_root artifacts/eval_runs \
    --evolution_root artifacts/eval_runs/evolution \
    --output_dir artifacts/eval_runs/grading_evidence
```

输出 `grading_evidence_pack.json` / `.md`（信息隔离、自进化轮次、A/B、manifest、缺口汇总）。

## 17. 答辩与质量自评（2026-05 快照）

非前端部分约 **86–88/100**；主打 **评测 + 复盘**，自进化为亮点。

| 维度          | 状态          | 剩余缺口                           |
| ------------- | ------------- | ---------------------------------- |
| 多 Agent 协作 | 高            | 固定场景验证报告                   |
| 信息隔离      | checker 已有  | 0 泄漏汇总报告                     |
| 评测 + 复盘   | 接近满分      | 反事实可继续增强                   |
| 自进化        | 工程闭环已有  | 20+ 局 initial vs 终局显著提升证据 |
| 版本回溯      | manifest 已有 | 一键恢复 CLI                       |

## 18. 人机对战验证结论（2026-05-26/28）

人类与 Agent 的技能、投票、发言、技能对象可被正确识别；人类公开发言可进入 LLM Agent 记忆并触发策略反应。deepseek 结构化决策静默丢失问题已在 `codex/deepseek-structured-recovery` 修复。详见 [architecture/evaluation/狼人杀对战测试-技能使用验证报告.md](../architecture/evaluation/%E7%8B%BC%E4%BA%BA%E6%9D%80%E5%AF%B9%E6%88%98%E6%B5%8B%E8%AF%95-%E6%8A%80%E8%83%BD%E4%BD%BF%E7%94%A8%E9%AA%8C%E8%AF%81%E6%8A%A5%E5%91%8A.md)。

## 19. 已知风险

| 风险                      | 缓解                                |
| ------------------------- | ----------------------------------- |
| 读档丢 events             | finalize 强制写 `events.jsonl`      |
| thinking 导致 Token 爆炸  | views 层 strip                      |
| Demo eval 与 LLM 质量脱节 | 区分 correctness / quality pipeline |
| PostGame 耗时长           | `skip_llm`、限制并行 Skill LLM      |
| POV 与 visible_to 偏差    | god vs player 视图对比 checker      |

## 20. 依赖与边界

- `evaluation → game_runtime, strategy, agent_team`
- 跨模块版本：[提示词与 Skill 版本控制](../architecture/%E5%90%95%E7%A5%8E%E6%99%97-%E6%8F%90%E7%A4%BA%E8%AF%8D%E7%89%88%E6%9C%AC%E4%B8%8E%E5%8F%98%E9%87%8F%E8%AE%BE%E8%AE%A1.md)

## 21. 相关文档

| 文档                                                    | 用途                         |
| ------------------------------------------------------- | ---------------------------- |
| [ROADMAP.md](./ROADMAP.md)                              | 进度                         |
| [README.md](./README.md)                                | 模块入口                     |
| [strategy/DESIGN.md](../strategy/DESIGN.md)             | Prompt manifest              |
| [architecture/evaluation/](../architecture/evaluation/) | 历史专题原文（已合并至本文） |
