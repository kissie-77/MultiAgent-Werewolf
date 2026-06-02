# Strategy 设计

> **模块**：strategy
> **状态**：active
> **最后更新**：2026-05-26
> **关联代码**：`src/llm_werewolf/strategy/`

## 1. 目标

提供统一的策略语言和决策契约：Prompt **按身份分包、按版本目录**管理，结构化决策 schema、信念矩阵、投票意向模型。作为 Agent 和引擎之间的策略层，不依赖任何业务模块。

## 2. 范围

### 做

- 管理角色 Prompt（外置 YAML + 共享 Markdown 模板，**per-role 版本目录**）
- 维护 `RoleVersionManifest`（每身份 prompt/skill 版本，默认解析最新）
- 定义结构化决策模型（Pydantic BaseModel）
- 管理信念矩阵、投票意向、阶段输出契约

### 不做

- 不执行 Agent 决策（归 `agent_team`）
- 不管理游戏状态（归 `game_runtime`）
- 不生成赛后 Skill MD（归 `evaluation`；strategy 只提供版本 manifest 契约）

## 3. Prompt 系统（per-role 小包）

### 3.1 目录结构

```text
strategy/prompts/
  shared/
    agent_base.md                 # 共用模板（{number} {role_name} {role_instruction} …）
  roles/
    wolf/
      v1/
        role.yaml
        manifest.yaml
      v2/                         # 进化或人工 bump 后新版本
        role.yaml
        manifest.yaml
    prophet/
      v1/
        ...
    ...（22 个 prompt_role_key）
```

进化生成的新包默认写入 `artifacts/prompt_roles/<role>/<version>/`，与内置 `prompts/roles/` 合并检索；**取各根目录下该身份的最高版本号**。

### 3.2 加载 API

| 入口 | 说明 |
|------|------|
| `get_role_card(role_key, version)` | 读取指定版本的 `role.yaml`，渲染结构化字段 |
| `build_role_strategy_prompt(seat, role_key, plan, prompt_version=…)` | 模板 + 角色卡拼成系统 prompt |
| `list_prompt_versions(role_key)` | 枚举所有可用 prompt 版本 |
| `resolve_latest_prompt_version(role_key)` | 解析最新版本（无目录时 fallback `v1`） |
| `copy_role_prompt_package(role, base, new, output_root=…)` | 进化：复制包并 bump 版本 |

运行时由 `PromptManager` / `factory.build_system_prompt` 调用；版本来自 `RoleVersionManifest.prompt_version_for(role_key)`。

### 3.3 角色卡片结构（`role.yaml`）

- `role_name` / `role_instruction`
- `core_principles` / `phase_strategies` / `forbidden_actions` / `examples`
- 运行时仍渲染为「长期规则 / 阶段策略 / 禁止项 / 示例」段落注入 `agent_base.md`

`plan` 不写在角色卡 YAML 中，而是在构建 Agent prompt 时通过 `{plan}` 注入。配置层可使用：

- `default_plan`：所有未手写 plan 玩家使用的默认策略计划
- `players[].plan`：单个玩家手写 plan，优先级最高
- `plan_assignment`：角色分配完成后，为未手写 plan 的玩家按真实角色自动分配角色专属风格 plan

### 3.4 提示词注入流程

```text
set_active_manifest(RoleVersionManifest)
    → PromptManager.build_role_strategy_prompt(...)
        → manifest.prompt_version_for(role)   # 未 pin → 最新版本
        → role_prompt_registry.get_role_card + agent_base.md
    → factory 可选拼接 skill_loader（见 agent_team）
    → Agent 接收完整 sys_prompt
```

### 3.5 Legacy v2 整包（只读参考）

`strategy/prompts/v2/` + `prompt_registry.py` 保留给旧测试与迁移脚本；**运行时主路径不再依赖 v2 变量 id**。新改动请只改 per-role 小包。

## 4. RoleVersionManifest

```python
@dataclass
class RoleVersionManifest:
    default_prompt_version: str = "latest"   # 无目录时的 fallback
    default_skill_version: str = "latest"
    prompt_versions: dict[str, str] = {}     # 显式 pin：role_key → vN
    skill_versions: dict[str, str] = {}
```

| 方法 | 行为 |
|------|------|
| `prompt_version_for(role)` | 有 pin 用 pin；否则扫描 `prompts/roles/<role>/` 与 `artifacts/prompt_roles/` 取**最新** |
| `skill_version_for(role)` | 有 pin 用 pin；否则扫描 `agent_team/skills/<role>/` 取**最新** |
| `with_prompt_version(role, v)` | 进化后更新单身份 pin |

Bootstrap 时执行 `scripts/bootstrap_role_prompt_packages.py` 从 legacy v2 拆出 22 身份 `v1/` 初始包。

## 5. 结构化决策模型

（与旧版相同，略）

| 模型 | 说明 |
|------|------|
| SpeechDecision | 圆桌发言 |
| SeatChoiceDecision | 选座 |
| VoteIntentionDecision | 投票意向 |
| MindStateDecision | 信念矩阵 |

## 6. 信念矩阵 / 投票意向 / 阶段输出

见旧版 §5–§7；实现文件未因版本控制改动而变化。

## 7. 接口与扩展点

| 入口 | 说明 |
|------|------|
| `RoleVersionManifest` | 全局 active manifest（`set_active_manifest` / `get_active_manifest`） |
| `PromptManager` | 构建 AgentScope 系统 prompt（per-role 版本） |
| `RolePrompts` / `GamePrompts` | 流程文案与 plan 策略 |

## 8. 相关文档

- [ROADMAP.md](./ROADMAP.md)
- [Prompt 调优记录](../architecture/prompt_tuning.md)
- [提示词版本与变量设计](../architecture/吕祎晗-提示词版本与变量设计.md)
- [evaluation/DESIGN.md §12](../evaluation/DESIGN.md)（备查：[自进化闭环协议](../architecture/evaluation/自进化闭环协议.md)）
