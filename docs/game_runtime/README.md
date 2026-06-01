# Game Runtime 模块

> **模块**：game_runtime
> **状态**：active
> **最后更新**：2026-05-24
> **关联代码**：`src/llm_werewolf/game_runtime/`
> **关联测试**：`tests/game_runtime/`

## 职责

狼人杀游戏规则与引擎核心层：角色定义、状态管理、阶段推进（白天/黑夜/投票）、事件系统、胜负判定、配置管理。

## 不负责

- Agent 决策与执行（见 `agent_team`）
- Prompt 与策略提示词（见 `strategy`）
- 赛后评测与复盘（见 `evaluation`）
- CLI/TUI 入口与装配（见 `interface`）

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `game_runtime/engine/` | 主引擎 GameEngine（Mixin 架构）：白天、黑夜、投票、警长选举、死亡处理 |
| `game_runtime/state/` | 游戏状态 GameState、玩家 Player、序列化 |
| `game_runtime/roles/` | 角色定义：预言家、女巫、猎人、守卫、狼人、狼王等 |
| `game_runtime/actions/` | 角色动作：村民动作、狼人动作 |
| `game_runtime/events/` | 事件系统：事件定义、可见性控制、格式化输出 |
| `game_runtime/config/` | 游戏配置：人数预设、记忆配置、玩家配置 |
| `game_runtime/prompts/` | 游戏内提示词：身份提示、阶段提示、动作提示 |
| `game_runtime/registries/` | 注册中心：动作注册、角色注册、夜间计划 |
| `game_runtime/types/` | 类型定义：游戏阶段等 |
| `game_runtime/victory.py` | 胜负判定逻辑 |
| `game_runtime/night_scheduler.py` | 夜间行动调度器 |
| `game_runtime/phase_interaction.py` | 阶段交互逻辑 |
| `game_runtime/death_abilities.py` | 死亡技能处理 |

## 依赖关系

- **可依赖**：`strategy`（稳定 DTO / 决策契约）
- **被依赖**：`agent_team`、`evaluation`、`interface`、`ui`

## 文档索引

| 文档 | 用途 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 稳定设计与接口契约 |
| [ROADMAP.md](./ROADMAP.md) | 开发进度与计划 |

## 快速入口

```python
from llm_werewolf.game_runtime import GameEngine, GameState, GameConfig, Player, GamePhase
```
