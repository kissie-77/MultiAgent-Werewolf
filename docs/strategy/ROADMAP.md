# Strategy 开发进度

> **模块**：strategy
> **状态**：active
> **最后更新**：2026-06-05

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| Per-role Prompt 小包 + 版本目录 | ✅ Done | `prompts/roles/<role>/<version>/` |
| RoleVersionManifest + 默认 latest | ✅ Done | prompt/skill 分身份 pin 或自动 latest |
| 结构化决策模型 | ✅ Done | SpeechDecision 等；phase 文案 Schema 化 |
| 信念矩阵 / 投票意向 | ✅ Done | |
| GamePrompts / PlanStrategies 外置 | ✅ Done | `phase/`、`plans/` + `phase_prompt_registry.py` |
| Legacy v2 整包清理 | ✅ Done | 删除 `prompts/v2/`、`prompt_registry.py` |

## 已完成

- [x] 22 身份 bootstrap 到 `roles/<role>/v1/`
- [x] `role_prompt_registry.py`：加载、复制、列举版本
- [x] `role_version_manifest.py`：manifest、latest 解析、`next_version_label`
- [x] `phase_prompt_registry.py`：`GamePrompts`、`PlanStrategies`、`ROLE_SEAT_ACTION`
- [x] `prompt_yaml_utils.py`：YAML 解析与 legacy suggestion 渲染
- [x] `PromptManager` / `factory` 走 per-role 版本
- [x] `prompt_evolver`：仅对改动身份 bump prompt 版本
- [x] 流程 prompt 去掉「放在 `[[]]` 里」；Bridge 保留文本回退
- [x] 清理 legacy `prompts/v2/` 与 `prompt_registry.py`

## 进行中

- [ ] 信念格式化 / `belief_updater` 与运行时边界文档细化

## 计划中

- [ ] 更多 phase/plan 版本 A/B（按需 bump `v2`）

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-06-05 | 文档日期对齐；uv.lock + CI 矩阵 3.10/3.12 修复（基础设施批次） |
| 2026-06-02 | 私密决策 belief skill refresh 文档对齐（agent_team）；phase prompt Schema 化 |
| 2026-06-02 | GamePrompts / PlanStrategies 外置；删除 legacy v2 整包 |
| 2026-05-24 | 初始化 strategy 三件套文档 |
| 2026-05-23 | Prompt v2 外置化重构（已迁移至 per-role） |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
