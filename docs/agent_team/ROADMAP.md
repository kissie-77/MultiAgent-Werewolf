# Agent Team 开发进度

> **模块**：agent_team
> **状态**：active
> **最后更新**：2026-05-26

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| AgentScope 接入 | ✅ Done | WerewolfAgent, ReAct, Prompt |
| Skill 按版本目录加载 | ✅ Done | `skills/<role>/<version>/`；默认 latest |
| 记忆四层 + RuntimeMemoryManager | ✅ Done | 见 [memory/ROADMAP.md](./memory/ROADMAP.md) |
| Skill 写回消费 | 🔄 In Progress | evaluation 门控双写 + bump 版本 |

## 已完成

- [x] AgentScopeWerewolfAgent, DemoAgent, bridge.py
- [x] InformationHub, RuntimeMemoryManager, skill_loader

## 进行中

- [ ] Skill 写回闭环证明

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-06-02 | 文档三件套归位；RuntimeMemoryManager 命名同步 |
| 2026-05-26 | memory 三件套；Per-role Skill 版本目录 |
| 2026-05-23 | ROADMAP 补全 |
