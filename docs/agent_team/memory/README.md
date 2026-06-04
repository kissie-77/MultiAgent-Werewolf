# Memory 子模块

> **模块**：agent_team / memory
> **状态**：active
> **最后更新**：2026-05-23
> **关联代码**：`src/llm_werewolf/agent_team/memory/`
> **关联测试**：`tests/agent_team/test_*memory*`、`tests/game_runtime/test_memory_*`
> **Agent Skill**：`.agents/skills/generated/agent-team/`

## 职责

运行时四层记忆编排：工作 / 情景 / 语义 / 程序记忆的生命周期、决策上下文组装、**信念矩阵驱动的 Skill 注入**与局后权重更新入口。

- **WorkingMemory** — 短期上下文，按轮压缩（可插拔 `LLMCompressor`）
- **EpisodicMemory** — 关键事件与玩家 POV 查询（含全局查询 API）
- **SemanticMemory** — 长期策略卡片 + 运行时读 `skills/<role>/<version>/*.md`
- **ProceduralMemory** — 角色计划与固定规则摘要
- **RuntimeMemoryManager** — 统一调度（兼容别名 `MemoryManager`）

## 不负责

- 游戏规则与事件写入（`game_runtime`）
- Prompt 策略正文（`strategy`）
- 赛后 Skill 生成与 Coach  enrich（`evaluation/post_game`）
- 向量检索 / ReMe（已下线，语义记忆走 Skill MD）

## 目录映射

| 代码路径 | 内容 |
|----------|------|
| `memory/runtime_memory_manager.py` | 运行时记忆调度主类 |
| `memory/working_memory.py` | 工作记忆、轮次压缩 |
| `memory/episodic_memory.py` | 情景记忆、全局/POV 查询 |
| `memory/semantic_memory.py` | 策略卡片、Skill 加载、合并去重 |
| `memory/procedural_memory.py` | 程序记忆、计划摘要 |
| `memory/llm_compressor.py` | 外部 LLM 压缩 + 重试降级 |
| `memory/config.py` | 转发 `game_runtime.config.MemoryConfig` |
| `agent_team/skills/<role>/<version>/` | 语义记忆运行时来源（evaluation 写入） |

## 依赖关系

- **可依赖**：`game_runtime`（事件、配置）、`strategy`（PromptManager）、`skill_support.skill_loader`
- **被依赖**：`agent_team/agents/factory.py`、Bridge 决策上下文组装
- **与 Coach 边界**：运行时 manager 只做收集与注入；经验提炼与 episode enrich 在 `evaluation/post_game/coach`

## 文档

| 文档 | 用途 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 四层架构、生命周期、与 Coach 分层、LLM 压缩容错（**单一真相**） |
| [ROADMAP.md](./ROADMAP.md) | 进度与待办 |

历史专题原文：[architecture/memory/](../../architecture/memory/)

上级模块：[agent_team/README.md](../README.md)

## 快速入口

```python
from llm_werewolf.agent_team.memory import RuntimeMemoryManager, MemoryConfig

manager = RuntimeMemoryManager(event_logger=logger, role="wolf", player_id="player_2")
manager.on_game_start("wolf")
manager.on_round_end(1)
manager.on_game_end(won=True)
```

```bash
uv run --with "pytest>=8.2" pytest -o addopts='' tests/agent_team/test_memory_manager.py tests/agent_team/test_working_memory.py -q
```
