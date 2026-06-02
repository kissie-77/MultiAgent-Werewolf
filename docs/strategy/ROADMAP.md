# Strategy 开发进度

> **模块**：strategy
> **状态**：active
> **最后更新**：2026-05-26

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| Prompt 外置化（legacy v2 整包） | ✅ Done | manifest + variables + 22 角色 |
| **Per-role Prompt 小包 + 版本目录** | ✅ Done | `prompts/roles/<role>/<version>/` |
| **RoleVersionManifest + 默认最新** | ✅ Done | prompt/skill 分身份 pin 或自动 latest |
| 结构化决策模型 | ✅ Done | SpeechDecision 等 |
| 信念矩阵 / 投票意向 | ✅ Done | |
| GamePrompts → phase 外置 | 📋 Planned | 仍暂留 `role_prompts.py` |

## 已完成

- [x] Legacy v2 整包（`prompt_registry.py`）
- [x] 22 身份 bootstrap 到 `roles/<role>/v1/`
- [x] `role_prompt_registry.py`：加载、复制、列举版本
- [x] `role_version_manifest.py`：manifest、latest 解析、`next_version_label`
- [x] `PromptManager` / `factory` 走 per-role 版本
- [x] `prompt_evolver`：仅对改动身份 bump prompt 版本
- [x] 默认运行时解析**最新** prompt/skill 版本（非固定 v1）

## 进行中

- [ ] 信念格式化 / `belief_updater` 与运行时对齐

## 计划中

- [ ] `GamePrompts` → `phase/*.md` 外置
- [ ] `PlanStrategies` → 外置 plan 变量
- [ ] 清理运行时对 legacy v2 整包的残余依赖（仅保留测试）

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-05-26 | Per-role Prompt/Skill 版本控制；默认 latest；更新模块文档 |
| 2026-05-24 | 初始化 strategy 三件套文档 |
| 2026-05-23 | Prompt v2 外置化重构 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
