# Agent Team 模块

> **模块**：agent_team
> **状态**：active
> **最后更新**：2026-06-05
> **关联代码**：`src/llm_werewolf/agent_team/`
> **关联测试**：`tests/agent_team/`
> **Agent Skill**：`.agents/skills/generated/agent-team/`

## 职责

Agent 执行层：AgentScope 接入、消息路由、信息隔离、记忆管理、**信念匹配 Skill 注入**（私密决策前 refresh）、结构化决策调用。

## 不负责

- 游戏规则与阶段推进（见 `game_runtime`）
- Prompt 策略与决策 schema（见 `strategy`）
- 赛后评测与 Skill 生成（见 `evaluation`）
- CLI/TUI 入口与装配（见 `interface`）

## 模块目录结构

```
agent_team/
├── __init__.py
├── agents/                  # Agent 实现与工厂
│   ├── agentscope_agent.py
│   ├── base.py
│   ├── demo_policy.py
│   ├── factory.py
│   ├── fast_react_agent.py
│   ├── human_interactive_agent.py
│   └── mixin.py
├── bridge/                  # LLM 输出 ↔ 引擎适配层
│   ├── adapter.py           # WerewolfAdapterBridge（原 bridge.py）
│   ├── parsing.py
│   └── prompts.py
├── communication/           # 消息路由与 InformationHub
├── invocation/              # 结构化 LLM 调用
├── memory/                  # 四层记忆 + RuntimeMemoryManager
└── skill_support/           # Skill MD 加载
```

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `agent_team/agents/` | AgentScopeWerewolfAgent、BaseAgent、DemoAgent、工厂函数 |
| `agent_team/bridge/` | 统一适配层：结构化输出解析、座位决策、Agent 调用 |
| `agent_team/communication/` | InformationHub、MessageRouter、Message 定义 |
| `agent_team/invocation/` | serial_calls、structured_invoke |
| `agent_team/memory/` | RuntimeMemoryManager、Working/Episodic/Semantic/Procedural |
| `agent_team/skill_support/` | skill_loader（`skills/<role>/<version>/`） |
| `agent_team/skills/` | Skill 库：按角色 + 版本分目录的 MD 卡片 |

## 依赖关系

- **可依赖**：`game_runtime.types`、`game_runtime.config`、`game_runtime.prompts`、`strategy`
- **被依赖**：`evaluation`（读 Skill 产物）、`interface`（装配 Agent）

## 文档索引

| 文档 | 用途 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 稳定设计与接口契约 |
| [ROADMAP.md](./ROADMAP.md) | 开发进度与计划 |
| [memory/](./memory/) | 四层记忆子模块（README · DESIGN · ROADMAP） |

## 快速入口

```python
from llm_werewolf.agent_team import (
    AgentScopeWerewolfAgent,
    create_agent,
    create_react_agent,
    configure_agents_for_players,
)
from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.agent_team.communication.information_hub import InformationHub
```
