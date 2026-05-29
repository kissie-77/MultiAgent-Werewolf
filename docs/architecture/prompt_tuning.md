# Prompt 调优记录

## 目的

本文档用于记录 AI 狼人杀项目中的 Prompt 迭代过程，重点展示：

- Prompt 工程的迭代历史。
- 不同角色的行为差异。
- 可追溯的决策链路与 bad case 分析。
- 不同 Prompt 版本之间的量化对比。

## 版本历史

| 版本                | 日期       | 范围                                                               | 改动依据                 | 目标                                                                             | 状态               |
| ------------------- | ---------- | ------------------------------------------------------------------ | ------------------------ | -------------------------------------------------------------------------------- | ------------------ |
| v1_baseline         | 2026-05-23 | 重构前项目内原始角色 Prompt                                        | 项目初始实现             | 提供基础角色身份说明和输出格式约束                                               | 基线版本           |
| v2_role_strategy    | 2026-05-23 | 改写村民、预言家、女巫、狼人、狼王、守卫、猎人 7 个核心角色 Prompt | 评分标准与本项目角色目标 | 完成初始策略化改写，提升角色策略、信息边界意识、发言质量、投票逻辑和技能使用决策 | 已实现，待对局验证 |
| v2_strategy_module  | 2026-05-24 | `src/llm_werewolf/strategy/role_prompts.py`                        | 工程架构重构计划         | 将角色策略 Prompt 收口到 strategy 策略层，作为角色 Prompt 的唯一主实现           | 已实现             |
| v2_prompt_manager   | 2026-05-24 | `PromptManager` 统一构建                                           | 工程架构重构计划         | 已实现                                                                           |                    |
| v2_prompt_variables | 2026-05-25 | `strategy/prompts/v2/` + `prompt_registry.py`                      | 提示词版本与变量设计     | 已实现（agent.base + 7 角色外置）                                                |                    |

## v2 变量化外置（2026-05-25）

- 设计文档：[吕祎晗-提示词版本与变量设计.md](./%E5%90%95%E7%A5%8E%E6%99%97-%E6%8F%90%E7%A4%BA%E8%AF%8D%E7%89%88%E6%9C%AC%E4%B8%8E%E5%8F%98%E9%87%8F%E8%AE%BE%E8%AE%A1.md)
- 变量 id 示例：`v2.agent.base`、`v2.role.wolf`
- 正文路径：`src/llm_werewolf/strategy/prompts/v2/text/`、`roles/*.yaml`
- 代码只通过 `PromptRegistry` / `PromptManager(prompt_version="v2")` 引用，**改 Prompt 优先改外置文件**
- YAML 可选 `prompt_version: v2`（`PlayersConfig`），贯通运行时与 PostGame
- `GamePrompts` / `PlanStrategies` 仍暂留 `role_prompts.py`（Phase 2 迁为 `v2.phase.*` / `v2.plan.*`）

## v2_role_strategy 改动说明

本次 v2 Prompt 改写将原本较短的身份描述升级为“角色策略卡”。这是一次基于评分标准和角色设计目标的初始策略化改写，尚未基于真实对局 bad case 完成闭环调优。

当前角色策略卡的权威位置为 `src/llm_werewolf/strategy/prompts/v2/`（经 `prompt_registry.py` 加载）；`role_prompts.py` 保留薄封装与 `GamePrompts` / `PlanStrategies`。

当前 AgentScope 运行主线不再直接拼接 `RolePrompts.BASE_PROMPT`。角色名映射、plan 解析和最终系统 prompt 构建统一由 `src/llm_werewolf/game_runtime/prompts/manager.py` 中的 `PromptManager` 提供；`agent_team/factory.py` 与 `agent_team/agentscope_agent.py` 只调用该入口。为避免运行时初始化阶段循环导入，`PromptManager` 对 `strategy.role_prompts` 使用懒加载。

主要改动：

- 增加更强的全局行为约束：以阵营胜利为目标，遵守信息边界，只基于当前可见信息推理。
- 增加每个角色的胜利目标和决策优先级。
- 增加白天发言要求：需要给出立场、怀疑对象、信任对象、理由和投票倾向。
- 增加技能使用策略：覆盖预言家、女巫、守卫、猎人、狼人、狼王等核心角色。
- 发言/遗言等圆桌任务：通过 `generate_response` 提交 `SpeechDecision`（`public_speech` / `private_thought`）。
- 选座、投票、女巫用药：仍用 `[[...]]` 文本格式（与引擎 bridge 解析一致）。

## 角色差异目标

| 角色   | 预期行为差异                                           |
| ------ | ------------------------------------------------------ |
| 村民   | 重点分析公开发言、投票链、前后矛盾和带票行为。         |
| 预言家 | 将查验结果视为高价值信息，并根据局势判断是否跳身份。   |
| 女巫   | 权衡解药和毒药收益，避免情绪化用毒，优先保护关键好人。 |
| 狼人   | 协调夜间击杀，隐藏身份，制造错误怀疑链并操纵投票。     |
| 狼王   | 承担更高风险，提前准备死亡技能的高价值目标。           |
| 守卫   | 保护疑似关键神职或强势好人，同时隐藏守护路径。         |
| 猎人   | 避免过早暴露身份，临死开枪时基于证据而非情绪。         |

## 赛后 PostGame 闭环（v2+）

对局结束后由 `evaluation/post_game/` 自动运行（`interface/finalize_run.py` 触发），**不修改运行时 Prompt**，仅产出 JSON/Markdown：

| 产物                                                         | 说明                                                            |
| ------------------------------------------------------------ | --------------------------------------------------------------- |
| `vote_swing_report.md` / `vote_swing_summary.json`           | 投票意向摇摆统计                                                |
| `camp_persuasion_report.md` / `camp_persuasion_summary.json` | **阵营匹配**后的正向说服评分                                    |
| `post_game_analysis.json` / `post_game_report.md`            | LLM 复盘（有 API 时）                                           |
| `prompt_proposals.json`                                      | Prompt 补丁提案（`apply_policy: json_only_no_runtime_replace`） |
| `post_game_manifest.json`                                    | 本局赛后流水线索引                                              |

运行时仅使用 **v2+**（`strategy/role_prompts.py`）。提案合并与 `prompt_comparison` 文档待后续手工/脚本接入。

## 后续验证计划

后续应使用相同对局配置分别运行 v1 和 v2 Prompt，并比较以下指标：

| 指标                | 含义                                                     |
| ------------------- | -------------------------------------------------------- |
| `format_score`      | 最终答案是否遵守 `[[...]]` 输出格式。                    |
| `role_consistency`  | 行为是否符合当前身份和阵营目标。                         |
| `reasoning_quality` | 发言和投票是否包含具体证据、目标和理由。                 |
| `team_strategy`     | 狼人是否有协作，好人是否有效利用公开信息。               |
| `decision_validity` | 技能和投票选择是否合法、是否具备基本策略合理性。         |
| `bad_case_count`    | evaluation checker 自动发现的 Prompt bad case 候选数量。 |

对局对比表：

| Game ID | Prompt 版本      | 胜利阵营 | 回合数 | 格式分 | 角色一致性 | 推理质量 | 团队策略 | 决策合理性 | Bad Case 数 |
| ------- | ---------------- | -------- | -----: | -----: | ---------: | -------: | -------: | ---------: | ----------: |
| 待补充  | v1_baseline      | 待补充   | 待补充 | 待补充 |     待补充 |   待补充 |   待补充 |     待补充 |      待补充 |
| 待补充  | v2_role_strategy | 待补充   | 待补充 | 待补充 |     待补充 |   待补充 |   待补充 |     待补充 |      待补充 |

## Bad Case 记录模板

当对局日志中出现 Prompt 相关问题时，使用以下格式记录。

```text
Bad Case：

- 对局 ID：
- Prompt 版本：
- 回合 / 阶段：
- Agent / 角色：
- 当时可见信息：
- 实际行为：
- 为什么这是坏决策：
- Prompt 修正方向：
- 修正后结果：
```

## 自动 Bad Case 检测初版

evaluation 系统中已加入规则型 `PromptBadCaseChecker`，用于自动识别候选 Prompt 问题。

当前可识别的问题包括：

- 白天发言缺少 `[[...]]` 最终答案格式。
- 发言过于空泛，缺少明确对象和判断。
- 预言家重复查验同一目标。
- 女巫毒药命中好人阵营玩家。
- 猎人或狼王死亡技能命中好人阵营玩家。

这些结果属于候选 bad case。用于答辩材料前，仍建议结合完整对局上下文复核一次。
