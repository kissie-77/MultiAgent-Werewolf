# Evaluation 设计

> **模块**：evaluation
> **状态**：active
> **最后更新**：2026-06-04
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

**提示词外置**（2026-06-05）：system/user 模板与评分维度在 `evaluation/prompts/replay/v1/`；Coach 语义提取在 `evaluation/prompts/coach/v1/`。`replay_prompt_builder` / `coach_prompt_builder` 经 `post_game_prompt_registry` 组装，含转折点时间线与 `prompt_suggestions` 格式约束。

Evaluation Analyst 经 `run_eval_replay` 调用 `create_react_agent` + `structured_model=ReplayAnalysisDecision`。Doubao 等 OpenAI 兼容端点常只返回 `generate_response` 的 `tool_use`，而不写入 `Msg.metadata.structured_output`；若仅读 metadata 会误判为 `empty eval agent response`。

`eval_agent._parse_replay_decision` 按下列顺序恢复 `ReplayAnalysisDecision`（与对局 `AgentScopeWerewolfAgent.get_structured_response` 同源工具）：

1. `unwrap_structured_metadata(metadata)`
2. `_extract_structured_payload_from_content(content)` — 从 `tool_use.generate_response.input` 取 JSON
3. 文本 JSON — `_extract_text` 优先 `get_text_content()`，跳过 thinking 与占位 `"Structured response submitted."`

用户 prompt 附加 `generate_response_instruction('ReplayAnalysisDecision')`，与对局 structured 调用一致。

**重试与降级**（`eval_agent._invoke_eval_analyst`）：

1. 结构化调用最多 3 次；遇 `429` 指数退避后重试
2. 仍失败则 plain JSON 二次请求（禁止 tool，直接输出 JSON 对象）
3. 解析仍失败 → `mode=failed`，`summary_zh` 降级为 `build_rule_summary_zh`

| `post_game_analysis.json.mode` | 含义 |
| ------------------------------ | ---- |
| `llm`                          | 解析成功，字段来自 LLM |
| `failed`                       | 解析或调用失败；`summary_zh` 降级为 `build_rule_summary_zh`（规则转折点） |
| `skipped`                      | 无 API 配置或 key（`no_api_config_or_key`） |

**情景记忆**：`episodic_bridge.py` 复用运行时 `EpisodicMemory` API；Coach 为 Skill 附加 `evidence.episodic_excerpt`。

### 5.2 RunContext / roster

`run_context.roster_from_events` 从全量 `events.jsonl`（上帝视角）构建身份表，除 `role_acting` / `player_eliminated` / `role_revealed` / `player_discussion` 外，还从下列事件补全 role：

- `message`（如猎人开枪提示）
- `hunter_revenge`、`guard_protected`、`seer_checked`、`witch_*` 等带 `data.role` 的动作事件
- `player_died`（若带 role）

`load_run_context` 末尾对已有 `role_name` 但缺 `camp` 的条目调用 `role_name_to_camp` 回填。缺 roster 会导致 `speaker_camp: null`、MVP 归一化失真、persuasion skill 误跳过。

### 5.3 PostGame 质量门控（2026-06-02）

规则层在生成 proposal / skill / MVP 前过滤假阳性，与 `tests/evaluation/test_prompt_proposal_quality.py` 对齐。

| 环节 | 规则 |
| ---- | ---- |
| **camp_persuasion** `matched_round_elimination` | 狼推好人 / 好人推狼 且对发言方阵营有利；误出同伴不算 matched；`speaker_camp` 未知 → false |
| **无 swing 终局归票** | 当轮实际出局者与发言者 `vote_intentions` 中自身意向一致时，即使 `drive_count=0` 也算 matched |
| **MVP** | 缺 `role_name` 或 `camp` 的玩家不参与按身份归一化；全场 MVP 优先选有完整身份条目 |
| **prompt_proposals** | golden / positive 仅 `matched_elimination` 或 `matched_round_elimination=true`；误出关键好人（Seer 等）生成 `bad_case_mis_elim_*`；摘录按句截断、guard 等身份脱敏 |
| **skill_generation** | persuasion skill：狼需推掉好人；好人需出狼或 swing 对齐狼出局；unknown camp → 不通过 |
| **prompt_evolver** | `positive_persuasion` / `mvp_golden_quote` 的 evidence 必须带 matched 标记才采纳；`bad_case_rule` 仍按置信度 |

**注意**：修复前 run 已写入的 `applied_prompt_proposals.json` / per-role prompt 版本不会自动回滚；需人工回退 `artifacts/prompt_versions` 或基于新 pipeline 重跑 evolver。

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

基于 `vote_swing` + `camp_persuasion`：`swing_count`、`camp_aligned_swings`、`matched_elimination`（同 `matched_round_elimination`）、`swing_to_final_vote`、`persuasion_net` → `intention_scores.json`。

MVP 综合分见 `mvp_scores.json`（`mvp_scores_v2`）：persuasion / strategy / outcome / wolf_night 按身份权重加权；golden 片段同样要求 matched 才进入 proposal 正向池。

### 7.2 Benefit Score

按玩家聚合阵营收益（夜间击杀、放逐、技能、说服、胜负等）→ `benefit_scores.json`。Phase 1 仅部分规则（`game_won`、`elimination_aligned`、`camp_persuasion_sum` 占位）。

### 7.3 与 Skill 提取

| 阶段            | 策略                                                 |
| --------------- | ---------------------------------------------------- |
| Phase 1（当前） | 每 `prompt_role_key` 有素材则提取；无则 `skipped`    |
| Phase 2         | 仅 `benefit_total >= T` 或 `intention >= T` 进入 LLM |
| Phase 3         | Skill 写入 strategy 版本库（JSON draft）             |

### 7.4 数据质量门禁

`mvp_scores.json.data_quality` 是赛后评分置信度的统一入口。除投票意向数量、完整白天轮数和有效发言外，若本局存在 `error` 事件（如 Timeout、结构化输出中断、运行时解析失败），`confidence` 必须降为 `low`，并在 `limitations` 与 `runtime_error_samples` 中记录原因。此类对局的 MVP、Prompt proposal 和 Skill 仅供排查参考，不应直接作为高置信度调优样本。

## 8. JSON 产物 Schema 要点

### 8.1 `prompt_proposals.json`

Schema `prompt_proposals_v3`：`proposals[]` 含 `kind`（`positive_persuasion` / `bad_case_rule` / `mvp_golden_quote` 等）、`suggested_patch`、`prompt_role_key`、`apply_policy: auto_evolve_next_prompt_version`（JSON 产物；运行时 YAML 仍经 evolver + 审核）。

生成顺序：MVP golden（需 matched）→ camp 正向发言（需 `matched_round_elimination`）→ 误出关键好人 bad_case → `PromptBadCaseChecker` 规则 bad_case（最多 10 条）。`llm_replay_notes` 来自 eval_agent，非 proposal 正文。

### 8.2 `role_skills.json`

Schema `role_skills_v1`：`skills[]` 含 `skill_id`、`prompt_role_key`、`status`、`quality_gate`、`skill_card`、`evidence`；按 `PromptManager.get_prompt_role_key` 分桶。

**质量门（Phase 1）**：该身份有 ≥1 条有效发言或夜间决策 → 进入提取；全程空发言 → `skipped`。

**写库策略（2026-06-04）** — `apply_policy: merge_when_to_use_then_sparse_bump`：

| 字段 | 说明 |
|------|------|
| `merge_policy.match_field` | `when_to_use`（frontmatter 或正文「何时使用」） |
| `merge_policy.similarity_threshold` | `0.78` |
| `merge_policy.weight_delta_on_merge` | `0.15` |
| `library_action` | `merged`（合并进已有 card）或 `created`（新建） |
| `merged_into_skill_id` | 合并目标（仅 `merged`） |

实现：`skill_extractor.find_matching_library_skill` / `merge_candidate_into_existing_skill` / `write_skill_markdown_files`。

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
| `draft`      | 否（PostGame 写库默认 draft，胜方新 skill 常因 weight≥1.05 升为 active） |
| `deprecated` | 否                                           |
| `skipped`    | 不写 MD                                      |

### 10.1 稀疏版本 bump

不是每局都新建 `skill_version` 目录。仅当某 `prompt_role_key` 本局有**使用场景不匹配**的新 Skill 时：

1. `next_skill_version()` → copy `vN/*` → `vN+1/`
2. 写入新 `{skill_id}.md`
3. `set_active_manifest` 将该 role 指向 `vN+1`

同局若既有合并又有新建，只 bump 一次，合并与新建均落在同一 `vN+1`。

### 10.2 场景合并（写库前）

候选 Skill 与当前版本库内 MD 按 `when_to_use` 相似度 ≥ 0.78 匹配时：

- **不**生成新 library 文件
- 合并 `## 公开行为` / `## 避免` / `## 提取依据`
- **weight += 0.15**（`clamp_weight`，上限 5.0），`use_count += 1`
- 在当前版本目录**原地**更新 MD（不 bump）

本局归档仍写 `runs/<id>/skills/*.md`；`role_skills.json` 记录 `library_action`。

### 10.3 权重与 status

- 本局候选：胜方阵营 weight +0.10 → 常 `active`；败方 -0.05
- 局内 `RuntimeMemoryManager.on_game_end`：对本局 prompt 注入过的 skill id 再 ±0.10 / -0.05（与 PostGame 合并增量独立）
- weight `>= 1.05` 可升 `active`；active 且 `<= 0.95` 可降 `deprecated`

**仍待证明**：下局 prompt 中 Skill 使用痕迹、写回前后 A/B 胜率（见 ROADMAP）。

**关联测试**：`tests/evaluation/test_skill_extractor.py`（`test_find_matching_library_skill_by_when_to_use`、`test_merge_matching_when_to_use_updates_weight_without_version_bump`、`test_new_when_to_use_creates_next_version`）。

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

**每轮**：`restore_runtime_from_manifest` → 评测 → `evolve_prompt_from_run`（按身份 bump；`_judge_proposal` 对正向提案要求 evidence 含 matched）→ 写 `version_manifest.json` → 更新 `role_manifest`。

**验收**：`smoke_6p_basic`；≥2 轮；`v1_initial` vs 终局；完成率不降；硬约束无新增失败；终局指标优于初始；存在 A/B 报告。

**已纳入**：prompt version chain、Wilson CI、z 检验、evolution matrix。**暂不做**：自动回滚、LLM 自动采纳 proposal、多模型混跑统一显著性。

## 13. 反事实推演

`post_game/counterfactual.py`：近票差放逐、狼刀换人、预言家查验等规则型 case；不重跑整局。

## 14. 离线评测 Runner

`EvaluationRunner` + DemoAgent；PostGame `skip_llm=True`。Checkers：RoleSkill、InformationIsolation、Victory、AsyncFlow、PromptBadCase、DecisionConsistency、RuntimeError。

`PromptBadCaseChecker` 会标记公开发言中的低质量输出、重复查验、伤害性神职目标等 bad case。新增“公开事实无支撑”检查：如果玩家在公开发言中声称“某人已跳身份 / 报救人 / 报验人”等，但此前公开发言没有对应支撑，会作为 Prompt bad case 记录，便于定位模型幻觉或过度补全。

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
| 旧 run 污染 prompt 版本   | 重跑 pipeline + evolver；或手动回退 per-role 版本 |

## 20. 依赖与边界

- `evaluation → game_runtime, strategy, agent_team`
- 跨模块版本：[提示词与 Skill 版本控制](../architecture/%E5%90%95%E7%A5%8E%E6%99%97-%E6%8F%90%E7%A4%BA%E8%AF%8D%E7%89%88%E6%9C%AC%E4%B8%8E%E5%8F%98%E9%87%8F%E8%AE%BE%E8%AE%A1.md)

## 21. 相关文档

| 文档                                                    | 用途                         |
| ------------------------------------------------------- | ---------------------------- |
| [ROADMAP.md](./ROADMAP.md)                              | 进度                         |
| [README.md](./README.md)                                | 模块入口                     |
| [review-dashboard.html](./review-dashboard.html)        | PostGame 流水线与产物静态可视化 |
| [strategy/DESIGN.md](../strategy/DESIGN.md)             | Prompt manifest              |
| [architecture/evaluation/](../architecture/evaluation/) | 历史专题原文（已合并至本文） |
