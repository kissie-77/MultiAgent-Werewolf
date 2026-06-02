# Strategy 模块

> **模块**：strategy
> **状态**：active
> **最后更新**：2026-05-26
> **关联代码**：`src/llm_werewolf/strategy/`
> **关联测试**：`tests/strategy/`

## 职责

策略与契约层：Prompt 管理（**按身份分包、按版本目录**）、结构化决策 schema、信念矩阵、投票意向模型、阶段输出契约。为 Agent 和引擎提供统一的策略语言和决策格式。

## 不负责

- Agent 执行与记忆管理（见 `agent_team`）
- 游戏规则与状态管理（见 `game_runtime`）
- 赛后评测与 Skill 生成（见 `evaluation`）

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `strategy/prompts/roles/<role>/<version>/` | 每身份 Prompt 小包（`role.yaml` + `manifest.yaml`） |
| `strategy/prompts/shared/agent_base.md` | 各身份共用的 Agent 骨架模板 |
| `strategy/role_prompt_registry.py` | 加载 per-role 包、复制进化版本、解析最新版本 |
| `strategy/role_version_manifest.py` | 运行时版本 manifest：每身份 prompt/skill 版本映射 |
| `strategy/prompt_registry.py` | **Legacy**：旧 v2 整包变量 registry（测试/迁移参考） |
| `strategy/role_prompts.py` | 角色提示词：`GamePrompts` / `PlanStrategies`；7 核心角色从 registry 水合 |
| `strategy/decisions.py` | 结构化决策模型 |
| `strategy/belief_*.py` | 信念矩阵 |
| `strategy/vote_intention.py` | 投票意向 |
| `strategy/phase_outputs.py` | 阶段输出契约 |

## 版本控制（概要）

- **Prompt**：`prompts/roles/<prompt_role_key>/<version>/role.yaml`
- **Skill**（运行时加载在 `agent_team/skills/`）：`<role>/<skill_version>/*.md`
- **默认行为**：未在 manifest 中 pin 的身份 → 自动使用磁盘上**最新版本**（`v2` > `v1`）
- **显式 pin**：进化 round、`version_manifest.json` 中的 `prompt_versions` / `skill_versions`
- 详见 [吕祎晗-提示词版本与变量设计.md](../architecture/吕祎晗-提示词版本与变量设计.md)

## 依赖关系

- **可依赖**：无（纯策略与契约层，不依赖其他业务模块）
- **被依赖**：`game_runtime`、`agent_team`、`evaluation`、`interface`

## 文档索引

| 文档 | 用途 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 稳定设计与接口契约 |
| [ROADMAP.md](./ROADMAP.md) | 开发进度与计划 |

## 快速入口

```python
from llm_werewolf.strategy.role_prompt_registry import get_role_card, build_role_strategy_prompt
from llm_werewolf.strategy.role_version_manifest import RoleVersionManifest, get_active_manifest
from llm_werewolf.strategy.decisions import SpeechDecision, VoteIntentionDecision
from llm_werewolf.strategy import RolePrompts, GamePrompts, PlanStrategies
```
