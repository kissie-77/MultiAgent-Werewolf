# 文档索引

阅读顺序建议：**本页 → [arch.md](./arch.md) → [project-governance.md](./project-governance.md)**

## 核心文档（维护中）

| 文档 | 用途 |
|------|------|
| [arch.md](./arch.md) | 分层架构、引擎 Mixin、夜间调度、信息隔离（1–2 屏概览） |
| [project-governance.md](./project-governance.md) | 职责边界、阶段归属、**Event 可见性表**（Review 权威） |
| [project-structure.md](./project-structure.md) | 目录树与新建文件规则 |
| [project-master-plan.md](./project-master-plan.md) | 核心重构阶段与验收 DoD |
| [roadmap.md](./roadmap.md) | 对外迭代与远期功能 |
| [workflow.md](./workflow.md) | 开发/运行工作流 |

## 适配与决策

| 文档 | 用途 |
|------|------|
| [adr/](./adr/) | 架构决策记录（Mixin、异步、评测、夜间调度等） |
| [adr/0005-night-skill-scheduler.md](./adr/0005-night-skill-scheduler.md) | 夜间技能顺序与女巫刀口依赖 |
| [LOCAL_ONLY-serial-agent-calls.md](./LOCAL_ONLY-serial-agent-calls.md) | 本地 API 限流（`serial_calls.py` 不入库） |

## 代码入口对照

| 功能 | 入口 |
|------|------|
| 控制台对局 | `src/llm_werewolf/cli.py` |
| TUI 对局 | `src/llm_werewolf/tui.py` |
| 离线评测 | `src/llm_werewolf/eval_cli.py` |
| 游戏引擎 | `src/llm_werewolf/core/engine/game_engine.py` |
| Agent / MsgHub | `src/llm_werewolf/adapter/information_hub.py` |
| 夜间顺序 | `src/llm_werewolf/core/night_scheduler.py` |
| 核心角色夜间决策 | `src/llm_werewolf/core/role_night_plans.py` |
| 事件可见性默认规则 | `src/llm_werewolf/core/event_visibility.py` |

## 历史文档

| 文档 | 说明 |
|------|------|
| [architecture-improvement.md](./architecture-improvement.md) | 早期迁移记录（只读参考，以 governance / master-plan 为准） |
