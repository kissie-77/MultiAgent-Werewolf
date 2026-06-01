# Agent Team 模块

> **模块**：agent_team
> **状态**：active
> **最后更新**：2026-05-24
> **关联代码**：`src/llm_werewolf/agent_team/`
> **关联测试**：`tests/agent_team/`
> **Agent Skill**：`.agents/skills/generated/agent-team/`

## 职责

Agent 执行层：AgentScope 接入、消息路由、信息隔离、记忆管理、Skill 读取、结构化决策调用。负责将游戏引擎的阶段指令转化为 Agent 的发言和决策。

## 不负责

- 游戏规则与阶段推进（见 `game_runtime`）
- Prompt 策略与决策 schema（见 `strategy`）
- 赛后评测与 Skill 生成（见 `evaluation`）
- CLI/TUI 入口与装配（见 `interface`）

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `agent_team/agents/` | Agent 实现：AgentScopeWerewolfAgent、BaseAgent、DemoAgent、PromptAgentMixin、工厂函数 |
| `agent_team/communication/` | 通信系统：InformationHub、MessageRouter、Message 定义 |
| `agent_team/invocation/` | 结构化调用：serial_calls、structured_invoke |
| `agent_team/memory/` | 记忆系统：WorkingMemory、SemanticMemory、EpisodicMemory、ProceduralMemory、MemoryManager、LLMCompressor |
| `agent_team/skill_support/` | Skill 读取：skill_loader、skill_markdown |
| `agent_team/skills/` | Skill 产物目录：按角色分类的赛后 Skill 文件 |
| `agent_team/bridge.py` | 统一适配层：LLM 输出解析、Agent 调用、决策转换 |
| `agent_team/fast_react_agent.py` | 快速 ReAct Agent 实现 |

## 依赖关系

- **可依赖**：`game_runtime.types`、`game_runtime.config`、`game_runtime.prompts`、`strategy`
- **被依赖**：`evaluation`（读 Skill 产物）、`interface`（装配 Agent）

## 文档索引

| 文档 | 用途 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 稳定设计与接口契约 |
| [ROADMAP.md](./ROADMAP.md) | 开发进度与计划 |

## 快速入口

```python
from llm_werewolf.agent_team import (
    AgentScopeWerewolfAgent,
    create_agent,
    create_react_agent,
    configure_agents_for_players,
)
```
