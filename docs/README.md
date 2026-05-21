# 文档索引

阅读顺序建议：**本页 → [arch.md](./arch.md) → [project-governance.md](./project-governance.md)**

## 分支与仓库

- 日常开发与联调请使用 Git 分支 **`lvyihan_test`**（与 `main` 并列，集成分支为单提交历史）。
- 仓库：`https://github.com/LBP97541135/MultiAgent-Werewolf`

## 核心文档（维护中）

| 文档 | 用途 |
|------|------|
| [arch.md](./arch.md) | 分层架构、引擎 Mixin、夜间调度、信息隔离 |
| [project-governance.md](./project-governance.md) | 职责边界、阶段归属、**Event 可见性表** |
| [project-structure.md](./project-structure.md) | 目录树与新建文件规则 |
| [project-master-plan.md](./project-master-plan.md) | 重构阶段与验收 DoD |
| [roadmap.md](./roadmap.md) | 对外迭代与远期功能 |
| [workflow.md](./workflow.md) | 开发/运行工作流 |

## 适配与决策

| 文档 | 用途 |
|------|------|
| [adr/](./adr/) | 架构决策记录 |
| [adr/0005-night-skill-scheduler.md](./adr/0005-night-skill-scheduler.md) | 夜间技能顺序与女巫刀口 |
| [LOCAL_ONLY-serial-agent-calls.md](./LOCAL_ONLY-serial-agent-calls.md) | 本地 API 限流（`adapter/serial_calls.py`） |

## 代码入口对照

| 功能 | 入口 |
|------|------|
| 控制台对局 | `src/llm_werewolf/cli.py` |
| TUI 对局 | `src/llm_werewolf/tui.py` |
| 离线评测 | `src/llm_werewolf/eval_cli.py`（`werewolf-eval`） |
| 游戏引擎 | `src/llm_werewolf/core/engine/game_engine.py` |
| 创建玩家 | `src/llm_werewolf/agents/base.py` → `create_agent()` |
| AgentScope 实现 | `src/llm_werewolf/integration/agentscope.py` |
| 统一中文 Prompt | `src/llm_werewolf/core/prompts/manager.py` |
| 角色注册表 | `src/llm_werewolf/core/roles/catalog.py`、`registry.py` |
| MsgHub / Bridge | `adapter/information_hub.py`、`adapter/bridge.py` |
| AgentScope 绑定 | `adapter/setup.py` → `bind_agentscope_roles()` |
| 夜间顺序 | `core/night_scheduler.py`、`core/role_night_plans.py` |
| 事件可见性 | `core/event_visibility.py` |

## 配置样例

| 文件 | 说明 |
|------|------|
| `configs/demo-6.yaml` | 6 人 demo，无需 API |
| `configs/llm-6p-openai.yaml` | 6 人真实 API 联调 |
| `configs/llm-12p-agentscope.yaml` | 12 人 AgentScope |

## 历史文档

| 文档 | 说明 |
|------|------|
| [architecture-improvement.md](./architecture-improvement.md) | 早期迁移记录（只读；`ActionSelector` 表述见该文脚注） |
