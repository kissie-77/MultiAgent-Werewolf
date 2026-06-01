# Strategy 开发进度

> **模块**：strategy
> **状态**：active
> **最后更新**：2026-05-24

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| Prompt 外置化（v2） | ✅ Done | manifest + variables + 角色卡片 |
| 结构化决策模型 | ✅ Done | SpeechDecision、SeatChoiceDecision 等 |
| 信念矩阵基础 | ✅ Done | B1/B2/W 面板定义 |
| 投票意向追踪 | ✅ Done | 快照、锚点、意向变化统计 |
| 阶段输出契约 | ✅ Done | RoundtablePhase / ActionPhase |
| 信念格式化 | 🔄 In Progress | 信念矩阵输出格式优化 |
| 信念规则更新 | 🔄 In Progress | `belief_updater.py` 与运行时对齐 |
| 多版本 Prompt 管理 | 📋 Planned | v1 → v2 → v3 迁移机制 |

## 已完成

- [x] Prompt 外置文件结构（v2 版本）
- [x] PromptRegistry 版本化管理
- [x] 角色卡片 YAML 定义（7个角色）
- [x] RolePrompts 从 registry 注入
- [x] SpeechDecision 验证（≥15字、非占位符）
- [x] SeatChoiceDecision、VoteIntentionDecision 等决策模型
- [x] 信念矩阵基础结构（MindStateResult）
- [x] 投票意向追踪与快照
- [x] 阶段输出契约（RoundtablePhase / ActionPhase）
- [x] 狼队心智同步（wolf_camp_mind）

## 进行中

- [ ] 信念格式化优化（更清晰的 B1/B2/W 输出）
- [ ] 信念更新规则完善（`belief_updater.py` 与 game_runtime 信念日志对齐）

## 计划中

- [ ] 信念自动更新全链路验证（LLM 辅助 + 持久化）
- [ ] 多版本 Prompt 迁移机制
- [ ] Prompt 效果评估指标
- [ ] 角色策略计划动态生成

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-05-24 | 初始化 strategy 三件套文档 |
| 2026-05-23 | 完成 Prompt v2 外置化重构 |
| 2026-05-22 | 添加信念矩阵基础结构 |
| 2026-05-21 | 完善投票意向追踪与快照功能 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
