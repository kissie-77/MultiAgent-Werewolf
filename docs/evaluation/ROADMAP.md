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
- [x] `scan_run_dir` 批量扫描固定包含 `PromptBadCaseChecker`（observability / werewolf-watch 消费）

## 进行中

- [ ] `benefit_scores.json` 完整规则
- [ ] 信念校准接入 PostGame + replay API
- [ ] 初始版 vs 终局版 **20 局以上** A/B 显著提升证据
- [ ] 信息隔离 0 泄漏汇总报告
- [ ] 历史 run backfill 脚本（见 architecture/evaluation/task_for_mimo.md）

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
| 2026-06-02 | `scan_run_dir` 固定跑 PromptBadCaseChecker；后端文档批次对齐 |
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
