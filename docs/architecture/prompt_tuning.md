# Prompt 调优记录

> **模块**：architecture
> **状态**：active
> **最后更新**：2026-06-02
> **关联代码**：`src/llm_werewolf/strategy/`
> **关联测试**：`tests/strategy/`
> **Agent Skill**：`.agents/skills/generated/strategy/`

## 目的

本文档用于记录 AI 狼人杀项目中的 Prompt 迭代过程。**运行时默认**：每身份使用 `prompts/roles/<role>/` 下最新 `vN`（`RoleVersionManifest`），而非全局 v2 整包。

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
| v2_prompt_variables | 2026-05-25 | ~~`strategy/prompts/v2/` + `prompt_registry.py`~~                      | 提示词版本与变量设计     | Legacy 整包                                                                       | **已删除 2026-06-02** |
| v3_per_role_packages | 2026-05-26 | `prompts/roles/<role>/<version>/` + `role_version_manifest.py`     | Per-role 版本控制        | 22 身份分包；默认 latest；进化按身份 bump                                        | **当前主路径**     |
| v2_role_card_schema | 2026-06-01 | 已迁入 `prompts/roles/*/v1/role.yaml`（原 v2/roles）               | 角色卡 Schema 迁移报告   | 结构化字段替代自由文本 `suggestion`                                              | 已并入 per-role    |
| v2_20260601_172033_prompt | 2026-06-01 | `artifacts/prompt_versions/v2_20260601_172033_prompt/`             | 自进化 Prompt 快照       | 记录 6.1 迭代后的生成版 Prompt，父版本为 `v2`                                    | generated          |
| v2_role_style_plans | 2026-06-02 | `PlanStrategies` + `PlayersConfig.plan_assignment`                 | 同模型同角色发言同质化问题 | 用角色专属风格 plan 做保守/激进/质疑/协调分流，支持手写与开局随机分配           | 已实现             |
| v2_public_fact_boundary | 2026-06-02 | `EngineContexts.public_speech_information_boundary` + `PromptBadCaseChecker` | 人机混战公开发言幻觉 | 禁止把未公开出现的跳身份、救人、验人、刀口写成事实；赛后标记无支撑公开事实 claim | 已实现             |
| v3_phase_plans_external | 2026-06-02 | `prompts/phase/`、`prompts/plans/` + `phase_prompt_registry.py`   | GamePrompts/PlanStrategies 外置 | 流程文案 Schema 化；删除 v2 整包                                                | **当前主路径**     |
| v3_role_pool_boundary | 2026-06-03 | `factory.build_system_prompt` + `RuntimeMemoryManager` + per-role 角色卡 | 6 人局把不存在的守卫当成可能性 | 将本局真实角色池注入系统 prompt 与工作记忆，收紧“守卫/守护线”泛化话术 | 已实现 |

## v3 Per-role 版本控制（2026-05-26）

- 设计文档：[吕祎晗-提示词版本与变量设计.md](./%E5%90%95%E7%A5%8E%E6%99%97-%E6%8F%90%E7%A4%BA%E8%AF%8D%E7%89%88%E6%9C%AC%E4%B8%8E%E5%8F%98%E9%87%8F%E8%AE%BE%E8%AE%A1.md)
- Prompt 路径：`strategy/prompts/roles/<role>/<version>/role.yaml` + `prompts/shared/agent_base.md`
- Skill 路径：`agent_team/skills/<role>/<skill_version>/*.md`
- 运行时通过 `RoleVersionManifest` 解析版本；**未 pin 则自动用最新 `vN`**
- 改 Prompt 优先改 per-role 小包（`prompts/roles/<role>/<version>/`）与 phase/plans 外置 YAML；**legacy `prompts/v2/` 整包已于 2026-06-02 删除**，历史条目仅作迁移记录
- Bootstrap：`scripts/bootstrap_role_prompt_packages.py`

## v2 变量化外置（2026-05-25，**已移除 2026-06-02**）

历史归档：整包路径与 `prompt_registry.py` 已删除。等价能力见 `role_prompt_registry.py`、`phase_prompt_registry.py`、`prompt_yaml_utils.py` 与 `prompts/roles/`、`prompts/phase/`、`prompts/plans/`。

## v2 角色卡结构化迁移（2026-06-01）

6.1 迭代将角色策略卡从旧 schema：

```yaml
role_name: ...
role_instruction: ...
suggestion: ...
```

升级为结构化 schema：

```yaml
role_name: ...
role_instruction: ...
core_principles: ...
phase_strategies: ...
forbidden_actions: ...
examples: ...
```

本次迁移覆盖 `src/llm_werewolf/strategy/prompts/v2/roles/` 下 22 个角色，包括 7 个核心角色和扩展角色：白狼、狼美人、守墓狼、隐狼、噩梦狼、血月使徒、白痴、长老、骑士、魔术师、丘比特、乌鸦、守墓人、盗贼、恋人等。

兼容机制：

- `PromptRegistry.get_role_card()` 继续返回兼容字段 `suggestion`。
- `_render_legacy_suggestion()` 会把 `core_principles`、`phase_strategies`、`forbidden_actions`、`examples` 渲染成旧版 `suggestion` 文本。
- `agent_base.md` 的 `{suggestion}` 占位符不需要改，旧调用链仍可读取。
- `PromptManager.build_prompt_key_strategy_prompt()` 通过 registry 读取角色卡，不直接依赖 YAML 旧字段。

本次迁移的正式依据文档为：[../evaluation/role_card_migration_report.md](../evaluation/role_card_migration_report.md)。

## 6.1 生成版 Prompt 快照（2026-06-01）

6.1 迭代后，Prompt 版本产物已写入 `artifacts/prompt_versions/`。当前可追溯到的最新生成版为：

```yaml
version: v2_20260601_172033_prompt
status: generated
parent: v2
description: 角色策略卡 + SpeechDecision 主路径（变量化外置文案）
created_at: '2026-06-01'
```

对应目录：

```text
artifacts/prompt_versions/v2_20260601_172033_prompt/
├── manifest.yaml
├── variables.yaml
├── roles/
└── text/
```

同日还存在较早快照：

- `v2_smoke_6p_basic_3_1_prompt`
- `v2_20260601_133500_prompt`
- `v2_20260601_165314_prompt`
- `v2_20260601_171745_prompt`

这些快照用于版本链回溯和自进化对比；运行时是否采用某个快照，仍以配置中的 `prompt_version` 和 registry 加载路径为准。

## 角色专属风格分流（2026-06-02）

6.1 对局暴露出一个同质化问题：同一种模型、同一角色的多个 Agent 会收到几乎相同的系统 prompt，导致发言角度、怀疑方式和投票理由趋同。此前的临时方向是让同角色玩家走不同怀疑链，但这会提前写死具体怀疑对象，容易破坏真实博弈。

6.2 改为更上层的风格分流：不指定“怀疑谁”，只指定“怎么思考和发言”。默认支持四类角色专属风格：

- `conservative`：保守派，先观察再站边，重视信息边界。
- `aggressive`：激进派，主动制造讨论焦点，推动归票。
- `skeptical`：质疑派，拆解逻辑、票型和前后矛盾。
- `coordinator`：协调派，整理多人发言，收束讨论方向。

实际注入的 plan 使用角色专属 key，例如：

```text
wolf_conservative
wolf_aggressive
wolf_skeptical
wolf_coordinator
```

配置层新增 `plan_assignment`，用于 A/B 验证：

```yaml
plan_assignment:
  enabled: true
  mode: role_random      # role_cycle / role_random
  seed: 20260602
  role_plans:
    wolf:
      - wolf_conservative
      - wolf_aggressive
      - wolf_skeptical
      - wolf_coordinator
```

规则：

- `players[].plan` 手写时优先生效，不被自动分流覆盖。
- 未手写 plan 的玩家，在角色分配完成后按真实角色分配角色专属 plan。
- `role_cycle` 按配置顺序轮转。
- `role_random` 使用 seed 打乱后轮转，方便复现实验。

CLI 可临时覆盖同一份配置的分流模式，方便做 A/B：

```bash
uv run llm-werewolf --config configs/human-6p-demo.yaml --plan_assignment off
uv run llm-werewolf --config configs/human-6p-demo.yaml --plan_assignment role_cycle
uv run llm-werewolf --config configs/human-6p-demo.yaml --plan_assignment role_random --plan_assignment_seed 20260602
```

## 公开事实边界加严（2026-06-02）

人机混战实测发现，部分 Agent 会把没有公开发生过的信息写成事实，例如第一轮白天凭空说“某玩家跳女巫并救了某人”。这不是信息泄露，而是模型根据狼人杀常见叙事进行过度补全，会污染公开发言和后续投票意向。

本次修复把约束放在两个位置：

- 运行时白天公开发言上下文：`EngineContexts.public_speech_information_boundary()` 明确要求只把公开对话记忆中出现过的跳身份、验人、用药、刀口等写成事实；如果只是推测，必须使用“我怀疑 / 我推测 / 可能”等表述。
- 赛后 bad case：`PromptBadCaseChecker` 检测“公开事实无支撑”发言，例如在没有前置公开支撑时声称“2号跳女巫救了3号”，用于复盘和 prompt 调优定位。

该修复不禁止玩家主动跳身份，也不禁止利用自己的私密信息制定策略；限制的是 public_speech 不能把未公开来源包装成“已经有人公开声明/已经发生”的事实。

## 本局角色池边界加严（2026-06-03）

6.3 人机/全 Agent 对局复盘发现，6 人局角色配置为 `Werewolf x2 + Seer x1 + Witch x1 + Villager x2`，不存在守卫；但部分 Agent 仍会在平安夜发言中提到“守卫守中”或“守护线”。根因不是角色分配错误，而是旧角色策略卡里存在狼人杀通用话术，同时“本局角色池”此前主要在白天阶段上下文里出现，没有稳定进入 Agent 开局系统 prompt 和工作记忆。

本次修复把角色池边界作为运行时固定约束：

- `agent_team/agents/factory.py` 在角色分配完成后统计真实角色池，并传入 `build_system_prompt()`。
- `factory.build_system_prompt()` 将 `EngineContexts.role_pool_note()` 追加到系统 prompt 末尾，确保它压住前面的角色策略卡与 active Skill。
- `AgentScopeWerewolfAgent` 保存 `role_counts`，保证真实 backend prompt 与本地 `chat_history` 镜像一致。
- `RuntimeMemoryManager.on_game_start()` 将同一份角色池写入 `WorkingMemory` 常驻区，tag 为 `role_pool`，priority 为 `8`；`WorkingMemory.get_context()` 单独渲染为 `【本局固定信息】`，不再混入 `【稳定经验】`。
- `EngineContexts.role_pool_note()` 增加兜底规则：如果长期策略、经验或示例提到未出现在本局角色池的身份，本局忽略这些身份。

同时收紧 per-role 小包与 legacy v2 角色卡中的泛化话术：

- 村民平安夜策略改为先核对本局角色池；如果本局没有守卫，不要解释成守卫守中。
- 狼人、狼王、白狼平安夜策略改为只有本局角色池存在守卫时才讨论守护线，否则围绕刀口线、身份线和女巫用药空间推演。
- 狼王示例中“女巫/守卫仍存活”改为“女巫或本局实际存在的防守神职仍存活”。

验证：

```bash
uv run pytest tests/agent_team/test_factory_configure.py tests/game_runtime/test_prompt_manager.py tests/strategy/test_prompt_registry.py tests/strategy/test_role_prompt_registry.py tests/strategy/test_role_prompts.py -q --no-cov
```

结果：`38 passed`。新增回归断言系统 prompt 与工作记忆均包含 `【本局角色池】`，且 6 人局角色池中不出现 `Guard x`。

## v2_role_strategy 改动说明

本次 v2 Prompt 改写将原本较短的身份描述升级为“角色策略卡”。这是一次基于评分标准和角色设计目标的初始策略化改写，尚未基于真实对局 bad case 完成闭环调优。

当前角色策略卡的权威位置为 `strategy/prompts/roles/<role>/<version>/`（经 `role_prompt_registry.py` 加载）；legacy `prompts/v2/` 仅作参考。

当前 AgentScope 运行主线不再直接拼接 `RolePrompts.BASE_PROMPT`。角色名映射、plan 解析和最终系统 prompt 构建统一由 `src/llm_werewolf/game_runtime/prompts/manager.py` 中的 `PromptManager` 提供；`agent_team/factory.py` 与 `agent_team/agents/agentscope_agent.py` 只调用该入口。为避免运行时初始化阶段循环导入，`PromptManager` 对 `strategy.role_prompts` 使用懒加载。

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

对局结束后由 `evaluation/post_game/` 自动运行（`interface/cli/runtime/finalize_run.py` 触发），**不修改运行时 Prompt**，仅产出 JSON/Markdown：

| 产物                                                         | 说明                                                            |
| ------------------------------------------------------------ | --------------------------------------------------------------- |
| `vote_swing_report.md` / `vote_swing_summary.json`           | 投票意向摇摆统计                                                |
| `camp_persuasion_report.md` / `camp_persuasion_summary.json` | **阵营匹配**后的正向说服评分                                    |
| `post_game_analysis.json` / `post_game_report.md`            | LLM 复盘（有 API 时）                                           |
| `prompt_proposals.json`                                      | Prompt 补丁提案（`apply_policy: json_only_no_runtime_replace`） |
| `post_game_manifest.json`                                    | 本局赛后流水线索引                                              |
| `version_manifest.json`                                      | 当前轮次实际版本摘要，记录 Prompt、Skill、memory、模型配置      |
| `prompt_version_diff.json` / `new_prompt_version.txt`        | 自进化采纳后生成的 Prompt 版本差异与下一版版本号                |

运行时仅使用 **v2+**。常规运行从 `strategy/prompts/<version>/` 加载；自进化生成版可从 `artifacts/prompt_versions/<generated_prompt_version>/` 追溯。Prompt 提案默认只写 JSON，不直接替换运行时 Prompt；被采纳后才进入下一轮版本链。

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
