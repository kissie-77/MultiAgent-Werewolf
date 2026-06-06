# Game Runtime 模块

> **模块**：game_runtime
> **状态**：active
> **最后更新**：2026-06-05
> **关联代码**：`src/llm_werewolf/game_runtime/`
> **关联测试**：`tests/game_runtime/`

## 职责

狼人杀游戏规则与引擎核心层：角色定义、状态管理、阶段推进（白天/黑夜/投票）、事件系统、胜负判定、配置管理。

## 不负责

- Agent 决策与执行（见 `agent_team`）
- Prompt 与策略提示词（见 `strategy`）
- 赛后评测与复盘（见 `evaluation`）
- CLI/TUI 入口与装配（见 `interface`）

## 模块目录结构

```
game_runtime/
├── __init__.py
├── actions/                 # 角色动作（村民 / 狼人）
├── config/                  # GameConfig、预设、玩家配置
├── engine/                  # GameEngine Mixin 架构
├── events/                  # 事件定义、可见性、格式化
├── i18n/                    # 本地化（Locale）
├── interaction/             # PhaseInteraction（引擎 ↔ Agent）
├── prompts/                 # 游戏内提示词管理
├── registries/              # 动作 / 角色 / 夜间计划注册
├── roles/                   # 角色定义与 catalog
├── rules/                   # 胜负判定、死亡技能常量
├── scheduling/              # 夜间行动调度器
├── state/                   # GameState、Player、序列化
├── support/                 # 配置加载、座位、观察、环境
└── types/                   # 枚举、协议、模型
```

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `game_runtime/engine/` | GameEngine（Mixin）：白天、黑夜、投票、警长、死亡处理 |
| `game_runtime/state/` | GameState、Player、序列化 |
| `game_runtime/roles/` | 角色定义：预言家、女巫、猎人、守卫、狼人等 |
| `game_runtime/actions/` | 村民动作、狼人动作 |
| `game_runtime/events/` | 事件定义、可见性控制、格式化输出 |
| `game_runtime/config/` | 人数预设、记忆配置、玩家配置 |
| `game_runtime/prompts/` | 身份提示、阶段提示、动作提示 |
| `game_runtime/registries/` | 动作注册、角色注册、夜间计划 |
| `game_runtime/types/` | GamePhase、Camp、协议与模型 |
| `game_runtime/rules/` | VictoryChecker、DEATH_ABILITY_ROLE_NAMES |
| `game_runtime/scheduling/` | NightSkillScheduler |
| `game_runtime/interaction/` | PhaseInteraction、PhaseInteractionHub |
| `game_runtime/i18n/` | Locale 多语言消息 |
| `game_runtime/support/` | load_config、座位解析、ObservationBuilder、env |

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
from llm_werewolf.game_runtime import GameEngine, GameConfig, GameState, Player
from llm_werewolf.game_runtime.interaction import PhaseInteraction
from llm_werewolf.game_runtime.rules import VictoryChecker
from llm_werewolf.game_runtime.support import load_config
```
