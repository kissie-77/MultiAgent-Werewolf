# MultiAgent-Werewolf 🐺

基于多 Agent 的狼人杀博弈系统：自建规则引擎 + AgentScope 结构化决策 + 信息隔离与离线评测。

其他语言: [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md)

## 分支说明

| 分支 | 用途 |
|------|------|
| **`lvyihan_test`** | **当前集成开发分支**（推荐 clone 与日常开发） |
| `main` | 稳定基线 |

```bash
git clone -b lvyihan_test https://github.com/LBP97541135/MultiAgent-Werewolf.git
cd MultiAgent-Werewolf
uv sync
```

## 快速开始

```bash
cp .env.example .env   # 填入 OPENAI_API_KEY 等

# 无 API（demo 代理）
uv run llm-werewolf configs/demo-6.yaml

# 真实 API（6 人，省 token）
uv run llm-werewolf configs/llm-6p-openai.yaml

# AgentScope 12 人局
uv run llm-werewolf configs/llm-12p-agentscope.yaml

# TUI
uv run llm-werewolf-tui configs/demo.yaml

# 离线评测（无 API）
uv run werewolf-eval --help
```

## 项目架构

详见 [docs/arch.md](docs/arch.md)、[docs/project-structure.md](docs/project-structure.md)、[docs/README.md](docs/README.md)。

```
src/llm_werewolf/
├── cli.py / tui.py / eval_cli.py   # 应用入口
├── agents/                         # BaseAgent、create_agent、PromptAgentMixin
├── integration/                    # AgentScopeWerewolfAgent、message 适配
├── adapter/                        # InformationHub、Bridge、factory、prompts.py
├── core/
│   ├── prompts/                    # PromptManager、identity/system、ActionSelector
│   ├── engine/                     # 阶段 Mixin
│   ├── roles/                      # catalog、registry、implementation 路径
│   ├── night_scheduler.py          # 夜间顺序：狼票结算后再女巫
│   ├── role_night_plans.py         # 核心角色夜间 LLM 规划
│   ├── phase_interaction.py        # 引擎 → Hub 门面
│   └── events + event_visibility   # 事件与可见性
├── evaluation/                     # werewolf-eval
└── ui/                             # TUI / Console 展示
```

**提示词双轨（并存，逐步收敛）**

- **Catalog 轨**：`core/prompts` + `RoleDefinition.implementation` + `bind_role()`
- **AgentScope 轨**：`adapter/prompts.py` + `factory` / `bind_agentscope_roles()`

**依赖方向**：`core` 不依赖 `adapter` 实现细节；`roles` 经 `phase_interaction` 调 LLM，不直接 import Hub。

## 当前进度

- [x] 异步 GameEngine + 20+ 角色 + YAML 配置
- [x] AgentScope 适配（`integration/` + `adapter/`）
- [x] 信息隔离（`Event.visible_to` + `InformationHub`）
- [x] 夜间技能调度（`NightSkillScheduler` / `role_night_plans`）
- [x] 角色目录 `ROLE_CATALOG` + `core/prompts` 中文选目标
- [x] 离线评测 CLI（`werewolf-eval`）
- [ ] 扩展狼人角色全部迁入 `role_night_plans`
- [ ] Web 观战 / 信念矩阵（远期）

## 致谢

- [AgentScope](https://github.com/agentscope-ai/agentscope)
- [werewolf_kills_agentscope](https://github.com/muranUSTB/werewolf_kills_agentscope)

## License

MIT

## Conventions

- **Commit**: [Conventional Commits](https://www.conventionalcommits.org/) — 见 [docs/workflow.md](docs/workflow.md)
- **ADR**: [docs/adr/](docs/adr/)
- **Roadmap**: [docs/roadmap.md](docs/roadmap.md)
