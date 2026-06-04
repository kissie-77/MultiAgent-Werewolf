# Agent Team 开发进度

> **模块**：agent_team
> **状态**：active
> **最后更新**：2026-05-23

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| AgentScope 接入 | ✅ Done | WerewolfAgent, ReAct, Prompt |
| Skill 按版本目录加载 | ✅ Done | `skills/<role>/<version>/`；默认 latest |
| 记忆四层 + RuntimeMemoryManager | ✅ Done | 见 [memory/ROADMAP.md](./memory/ROADMAP.md) |
| Skill 写回消费 | 🔄 In Progress | evaluation 门控写库；when_to_use 合并 +0.15；稀疏 bump |
| 信念驱动 Skill 注入 | ✅ Done | 信念矩阵匹配 + 自动 belief_signals |

## 已完成

- [x] AgentScopeWerewolfAgent, DemoAgent, bridge.py
- [x] InformationHub, RuntimeMemoryManager, skill_loader
- [x] 消费 evaluation 稀疏 bump + 场景合并写库（详见 [skills/README.md](../../src/llm_werewolf/agent_team/skills/README.md)）

## 进行中

- [ ] Skill 写回闭环证明

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-05-23 | 信念驱动 Skill 注入（唯一方式）；12p 对局 4/4 回匹配测试 |
| 2026-06-04 | Skill 写库：when_to_use 相似合并 +0.15、稀疏 bump；文档见 evaluation/DESIGN §10 |
| 2026-06-02 | 文档三件套归位；RuntimeMemoryManager 命名同步 |
| 2026-05-26 | memory 三件套；Per-role Skill 版本目录 |
| 2026-05-23 | ROADMAP 补全 |
