# Memory 开发进度

> **模块**：agent_team / memory
> **状态**：active
> **最后更新**：2026-06-02
> **关联代码**：`src/llm_werewolf/agent_team/memory/`
> **关联测试**：`tests/agent_team/test_*memory*`、`tests/game_runtime/test_memory_*`

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| 四层记忆框架 | ✅ Done | Working / Episodic / Semantic / Procedural |
| 生命周期闭环 | ✅ Done | start / round_end / game_end 钩子 |
| 架构归位 agent_team | ✅ Done | 非独立第七模块 |
| RuntimeMemoryManager 与 Coach 分层 | ✅ Done | 别名 MemoryManager 保留 |
| ReMe 下线、Skill 语义记忆 | ✅ Done | load_role_skills + weight |
| Episodic 全局查询 + AGENT_THOUGHT | ✅ Done | PostGame / Coach 消费 |
| LLMCompressor 重试降级 | ✅ Done | 3 次退避 + 周期性 warning |
| factory event_logger 修复 | ✅ Done | bind_prompt / configure_role |
| 效果验证实验 | 🔄 In Progress | 记忆是否显著改变 Agent 行为 |
| ReMe 代码彻底移除 | ✅ Done | `reme_backend.py` 已删除 |
| Coach 写回统一入口 | 📋 Planned | 可选：提炼+写回+淘汰收成 Coach |

## 已完成

- [x] `MemoryManager` / `RuntimeMemoryManager` 统一调度
- [x] 运行时输入：决策、公开发言、可见事件
- [x] `extract_semantic_candidates` 规则式提炼（局势/决策/胜败反思）
- [x] 策略卡片 JSON：去重、归并、weight/use_count/win_count
- [x] `ProceduralMemory` 与真实 `plan_name` 对齐
- [x] Skill frontmatter：weight、win_count、use_count、时间戳
- [x] 聚焦回归：75+ passed（agent_team + memory hooks + integration）
- [x] 文档三件套：`agent_team/memory/{README,DESIGN,ROADMAP}`

## 进行中

- [ ] 记忆对决策质量的 A/B 或固定场景对比
- [ ] `SemanticMemory` 与 evaluation 写回 Skill 的端到端显式证明
- [ ] 测试覆盖 Episodic 全局 API、AGENT_THOUGHT 隔离

## 计划中

- [ ] 更高质量 LLM 提炼（非纯规则候选）
- [ ] Coach 统一写回入口（add_or_merge + evict）
- [ ] 信念矩阵与 working memory 深度集成（见 architecture 信念矩阵设计）

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-06-02 | ReMe 代码已移除；文档对齐 |
| 2026-05-26 | 文档三件套；ReMe 下线；Skill 语义；Episodic 全局化；Coach 占位对接 |
| 2026-05-26 | LLMCompressor 重试与降级日志 |
| 2026-05-25 | 四层框架初版；归位 agent_team/memory |
| 2026-05-24 | RuntimeMemoryManager 与 Coach 职责拆分 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
