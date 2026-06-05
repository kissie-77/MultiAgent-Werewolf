# Evaluation 开发进度

> **模块**：evaluation
> **状态**：active
> **最后更新**：2026-06-05
> **关联代码**：`src/llm_werewolf/evaluation/`
> **关联测试**：`tests/evaluation/`
> **Agent Skill**：`.agents/skills/generated/evaluation/`

## 总览

| 阶段                       | 状态           | 说明                                            |
| -------------------------- | -------------- | ----------------------------------------------- |
| PostGame 14 步 + log_views | ✅ Done        | pipeline + POV 视图                             |
| Evaluation v2 Phase 1      | ✅ Done        | Skill MD 双写、prompt_proposals、Coach          |
| Per-role 版本控制          | ✅ Done        | `RoleVersionManifest`；默认 latest（非全局 v2） |
| Leaderboard / A/B + 显著性 | ✅ Done        | Wilson CI、z 检验                               |
| PostGame 质量门控           | ✅ Done        | roster / matched / MVP / proposal / evolver 门控 |
| Phase 2                    | 🔄 In Progress | benefit 完整规则、信念校准、按分筛 Skill        |
| Skill 闭环显式证明         | 🔄 In Progress | 写回 → 下局使用 → 20+ 局 A/B                    |
| Leaderboard Web            | 📋 Planned     | 依赖 frontend                                   |

## 已完成

- [x] AgentScope 替换 AsyncOpenAI（eval_agent）
- [x] eval_agent 结构化输出解析与对局 Agent 对齐（metadata / tool_use / 文本 JSON）
- [x] PostGame pipeline、`finalize_run`、PostGame API
- [x] intention / mvp / benefit（部分）、camp_persuasion、counterfactual
- [x] role_skills 全量提取 + 门控双写 `skills/<role>/<version>/`
- [x] Skill 写库：`when_to_use` 相似合并（+0.15 权重）+ 稀疏 bump（仅新建时 vN→vN+1）
- [x] prompt_evolver per-role + `restore_runtime_from_manifest`
- [x] Leaderboard CLI、evolution runner、grading evidence 命令
- [x] skill draft/active/deprecated 测试（test_skill_extractor 等）
- [x] PostGame 质量门控：roster 补全、matched 无 swing、MVP 资格、proposal/evolver 过滤
- [x] 复盘可视化页 `docs/evaluation/review-dashboard.html`
- [x] 文档：evaluation 仅保留 README / DESIGN / ROADMAP
- [x] Runtime error / Timeout / structured 中断进入 `data_quality`，自动降低赛后评分置信度
- [x] PromptBadCaseChecker 增加「公开事实无支撑」检测，标记凭空跳身份/报技能结果类发言

## 进行中

- [ ] `benefit_scores.json` 完整规则
- [ ] 信念校准接入 PostGame + replay API
- [ ] 初始版 vs 终局版 **20 局以上** A/B 显著提升证据
- [ ] 信息隔离 0 泄漏汇总报告
- [ ] 历史 run backfill 脚本（见 architecture/evaluation/task_for_mimo.md）

## Task 6/7：可追踪证据链整理（2026-06-05）

本节是**证据整理**，不是新功能：不改变对局逻辑、不新增评分规则、不替代正在进行的信息隔离和夜间技能测试。它的用途是把已有产物组织成一条答辩时能讲清楚的链路：Agent 在局内怎么想、怎么影响别人、赛后如何被评分、版本改动是否真的变好。

### Agent 间博弈行为如何可追踪

| 证据点 | 说明 | 答辩时证明什么 |
| --- | --- | --- |
| 信念矩阵 / `beliefs.jsonl` | 记录每个 observer 在每轮、每个 anchor 后的 mind state；能看到“谁在什么时候相信谁更像狼/好人”。 | Agent 不是只输出一句话，而是在持续更新局势判断。 |
| `vote_intentions.jsonl` | 记录发言前后、轮次中的投票意向和目标变化。 | 能追踪“谁打算投谁”，以及发言后是否发生摇摆。 |
| vote_swing / `camp_persuasion_summary.json` | 把意向变化、最终出局、阵营收益连起来；`matched_round_elimination` 区分有效说服和误导同伴。 | 能判断一次发言是否真正改变了其他 Agent 的行为。 |
| `intention_scores.json` / `benefit_scores.json` | 把说服、归票、胜负、阵营收益转成可聚合分数。 | 行为变化可以进入评分，而不是只靠人工观感。 |
| PostGame / Coach | 从 `events.jsonl`、`vote_intentions.jsonl`、`beliefs.jsonl` 生成时间线、复盘、Skill 候选、Prompt proposal 和 evidence。 | 单局可从原始事件回溯到复盘结论和策略改进建议。 |
| Leaderboard / A/B | `leaderboard_entry.json` 汇总单局指标；`leaderboards/*` 排名；`ab_reports/*` 给 Wilson CI、z 检验和显著性字段。 | 版本改动是否更好可以跨局比较，而不是只挑一局展示。 |
| evidence pack | `grading_evidence_pack.json` / `.md` 汇总信息隔离、自进化、A/B、manifest 和缺口。 | 答辩时一键拿到“已有证据”和“还缺什么”。 |

### 当前还缺的可评分证据

- **0 泄漏汇总报告**：`InformationIsolationChecker` 和相关测试能力已在，但还需要把真实评测 run 的检查结果汇总成一份明确的“私密信息 0 泄漏”报告。
- **20 局以上 A/B 显著提升**：Leaderboard / A/B 统计字段已具备，但还需要固定 scenario、固定 seed 策略，跑 `v1_initial` vs 终局版至少 20 局，并保留 `p-value`、Wilson CI、`win_rate_significant`。
- **信念校准正式产物**：`beliefs.jsonl` 已能支撑追踪；Brier score 等信念校准指标仍需接入 PostGame 标准产物，并在 replay / evidence 中形成稳定展示。
- **证据包中的缺口闭环**：`werewolf-evidence` 已能列出缺口；答辩前应补齐上述两类报告，或在 evidence pack 中明确标注“工程能力已具备，样本证据待补跑”。

### 最短答辩证据清单

1. 单局 run 目录：`events.jsonl`、`vote_intentions.jsonl`、`beliefs.jsonl`、`post_game_manifest.json`、`camp_persuasion_report.md`、`camp_persuasion_summary.json`、`intention_scores.json`、`role_skills.json`。
2. 版本对比目录：`leaderboard_entry.json`、`leaderboards/leaderboard.md`、`ab_reports/*.md`、`version_manifest.json`、`experiment_meta.json`。
3. 总证据包：`artifacts/eval_runs/grading_evidence/grading_evidence_pack.md` 和 `.json`。
4. 缺口说明：0 泄漏汇总报告、20+ 局 A/B 显著提升报告、信念校准 PostGame 接入状态。

### 命令入口

```bash
# 生成一批离线评测 run
uv run werewolf-eval --scenario smoke_6p_basic --games 3 --timeout_seconds 20 --output_dir artifacts/eval_runs/manual-smoke

# 查看单局投票摇摆和说服效果
uv run werewolf-vote-swing artifacts/runs/<run_id>

# 聚合排行榜
uv run python -m llm_werewolf.evaluation.leaderboard.cli build artifacts/eval_runs

# 对两个版本做 A/B 对比
uv run python -m llm_werewolf.evaluation.leaderboard.cli compare artifacts/eval_runs/a/leaderboard_entry.json artifacts/eval_runs/b/leaderboard_entry.json

# 生成答辩评分证据包
uv run werewolf-evidence --eval_root artifacts/eval_runs --evolution_root artifacts/eval_runs/evolution --output_dir artifacts/eval_runs/grading_evidence
```

## 计划中

- [ ] PostGame 增量生成
- [ ] eval runner 可选真实 LLM + 完整 PostGame
- [ ] `werewolf-post-game` 独立 CLI
- [ ] Leaderboard 前端可视化
- [ ] evolution overview / 每轮版本摘要 MD
- [ ] 一键 manifest 恢复 CLI
- [ ] Prompt/Skill 贡献拆分实验；Fisher 精确检验（小样本）

## 暂不做

- 自动回滚主策略
- LLM 自动采纳 prompt proposal
- 多模型混跑统一胜率显著性

## 变更记录

| 日期       | 摘要                                               |
| ---------- | -------------------------------------------------- |
| 2026-06-05 | Task 6/7：补充信念矩阵、PostGame、Leaderboard/A/B 与证据包的答辩证据链；明确剩余可评分证据缺口 |
| 2026-06-04 | Skill 写库：when_to_use 相似合并 +0.15、稀疏 bump；DESIGN §8.2 / §10 |
| 2026-06-02 | PostGame 质量门控 + review-dashboard；DESIGN §5.2–§5.3 |
| 2026-06-02 | 赛后质量门禁：运行时错误降置信度；新增公开事实无支撑 bad-case 检测 |
| 2026-06-02 | eval_agent 复盘 structured 解析兜底；DESIGN §5.1    |
| 2026-05-26 | 文档全部合并三件套；专题迁 architecture/evaluation |
| 2026-05-26 | Per-role 版本控制                                  |
| 2026-05-28 | episodic_bridge + Coach episode                    |
| 2026-05-25 | Evaluation v2 Phase 1                              |
| 2026-05-23 | 初始化三件套                                       |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
