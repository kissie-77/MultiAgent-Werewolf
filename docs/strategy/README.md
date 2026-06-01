# Strategy 模块

> **模块**：strategy
> **状态**：active
> **最后更新**：2026-05-24
> **关联代码**：`src/llm_werewolf/strategy/`
> **关联测试**：`tests/strategy/`

## 职责

策略与契约层：Prompt 管理（版本化外置文件）、结构化决策 schema、信念矩阵、投票意向模型、阶段输出契约。为 Agent 和引擎提供统一的策略语言和决策格式。

## 不负责

- Agent 执行与记忆管理（见 `agent_team`）
- 游戏规则与状态管理（见 `game_runtime`）
- 赛后评测与 Skill 生成（见 `evaluation`）

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `strategy/prompts/` | 外置 Prompt 文件：v2 版本目录（角色卡片、基础模板、变量配置、清单） |
| `strategy/prompt_registry.py` | Prompt 注册中心：版本化管理、变量加载、角色卡片读取 |
| `strategy/role_prompts.py` | 角色提示词：从 prompt_registry 注入各角色策略 |
| `strategy/decisions.py` | 结构化决策模型：SpeechDecision、SeatChoiceDecision、VoteIntentionDecision 等 |
| `strategy/belief_state.py` | 信念状态：B1/B2/狼队 W 面板定义 |
| `strategy/belief_format.py` | 信念格式化：信念矩阵输出格式 |
| `strategy/belief_updater.py` | 信念更新：信念状态更新逻辑 |
| `strategy/vote_intention.py` | 投票意向：意向追踪、快照、锚点 |
| `strategy/wolf_camp_mind.py` | 狼队心智：狼人阵营内部信息同步 |
| `strategy/phase_outputs.py` | 阶段输出：白天/黑夜/圆桌阶段输出契约 |
| `strategy/evaluation_outputs.py` | 评测输出：与 evaluation 模块的接口 |

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
from llm_werewolf.strategy import RolePrompts, GamePrompts, PlanStrategies
from llm_werewolf.strategy.decisions import SpeechDecision, VoteIntentionDecision
from llm_werewolf.strategy.prompt_registry import PromptRegistry
```
