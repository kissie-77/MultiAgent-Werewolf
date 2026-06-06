# Strategy 模块

> **模块**：strategy
> **状态**：active
> **最后更新**：2026-06-05
> **关联代码**：`src/llm_werewolf/strategy/`
> **关联测试**：`tests/strategy/`

## 职责

策略与契约层：Prompt 管理（**按身份分包、按版本目录**）、结构化决策 schema、信念矩阵、投票意向模型、阶段输出契约。为 Agent 和引擎提供统一的策略语言和决策格式。

## 不负责

- Agent 执行与记忆管理（见 `agent_team`）
- 游戏规则与状态管理（见 `game_runtime`）
- 赛后评测与 Skill 生成（见 `evaluation`）

## 模块目录结构

```
strategy/
├── __init__.py              # 对外导出 GamePrompts / PlanStrategies / RolePrompts
├── belief/                  # 信念矩阵
│   ├── format.py            # 信念格式化、Skill 信号检测
│   ├── state.py             # BeliefState / BeliefLog
│   └── updater.py           # 信念更新与合并
├── contracts/               # 结构化决策契约
│   ├── decisions.py         # SpeechDecision / WitchNightDecision 等
│   ├── phase_outputs.py     # ActionPhase / 阶段指令
│   └── evaluation_outputs.py
├── registry/                # Prompt 加载与版本管理（Python）
│   ├── phase_prompt_registry.py
│   ├── role_prompt_registry.py
│   ├── role_prompts.py      # GamePrompts / PlanStrategies facade
│   ├── role_version_manifest.py
│   └── prompt_yaml_utils.py
├── voting/                  # 投票意向
│   ├── intention.py
│   └── seat.py
├── wolf/                    # 狼人私有战术雷达（W-G / W-E，按座位隔离）
│   ├── camp_mind.py         # WolfCampMindModel、init_wolf_camp_minds、merge
│   └── team.py
└── prompts/                 # Prompt 资产（YAML / Markdown，非 Python）
    ├── roles/<role>/<version>/
    ├── phase/<version>/
    ├── plans/<version>/
    └── shared/agent_base.md
```

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `strategy/prompts/roles/<role>/<version>/` | 每身份 Prompt 小包（`role.yaml` + `manifest.yaml`） |
| `strategy/prompts/shared/agent_base.md` | 各身份共用的 Agent 骨架模板 |
| `strategy/registry/role_prompt_registry.py` | 加载 per-role 包、复制进化版本、解析最新版本 |
| `strategy/registry/role_version_manifest.py` | 运行时版本 manifest：每身份 prompt/skill 版本映射 |
| `strategy/registry/prompt_yaml_utils.py` | 角色卡 YAML 解析辅助 |
| `strategy/registry/phase_prompt_registry.py` | 加载 GamePrompts / PlanStrategies / seat_actions 外置包 |
| `strategy/prompts/phase/<version>/` | 流程文案（GamePrompts、`seat_actions.yaml`） |
| `strategy/prompts/plans/<version>/` | Plan 策略（`plans.yaml`） |
| `strategy/registry/role_prompts.py` | 兼容入口：`GamePrompts` / `PlanStrategies` / `RolePrompts` 水合 facade |
| `strategy/contracts/decisions.py` | 结构化决策模型 |
| `strategy/belief/` | 信念矩阵 |
| `strategy/voting/intention.py` | 投票意向 |
| `strategy/contracts/phase_outputs.py` | 阶段输出契约 |

## 版本控制（概要）

- **Prompt（角色）**：`prompts/roles/<prompt_role_key>/<version>/role.yaml`
- **Prompt（流程）**：`prompts/phase/<version>/prompts.yaml`
- **Plan**：`prompts/plans/<version>/plans.yaml`
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
from llm_werewolf.strategy.registry.role_prompt_registry import get_role_card, build_role_strategy_prompt
from llm_werewolf.strategy.registry.role_version_manifest import RoleVersionManifest, get_active_manifest
from llm_werewolf.strategy.contracts.decisions import SpeechDecision, VoteIntentionDecision
from llm_werewolf.strategy import RolePrompts, GamePrompts, PlanStrategies

# 子包聚合导出（可选）
from llm_werewolf.strategy.belief import BeliefState, ensure_agent_belief_state
from llm_werewolf.strategy.voting import VoteIntentionTracker
from llm_werewolf.strategy.wolf import WolfCampMindModel
```
