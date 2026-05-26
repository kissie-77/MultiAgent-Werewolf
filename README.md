# MultiAgent-Werewolf 🐺

基于多 Agent 协作框架的狼人杀智能体博弈系统。

## 项目简介

本项目构建一个多智能体协作/对抗的狼人杀博弈系统。每个 Agent 根据其扮演角色（狼人、预言家、女巫等）拥有独立的目标、策略与行动空间，在信息隔离的约束下进行推理、发言与决策。

**技术路线**：AgentScope 作为 Agent 执行底座 + 自建 GameEngine 管理游戏逻辑

## 快速开始

### 环境要求

- Python 3.10+
- uv 包管理器

### 安装

```bash
git clone https://github.com/kissie-77/MultiAgent-Werewolf.git
cd MultiAgent-Werewolf

# 安装依赖
uv sync
```

### 配置 API

1. 复制环境变量模板并填入密钥：

```bash
cp .env.example .env
```

2. 复制对局配置：

```bash
cp configs/example.yaml configs/my_game.yaml
```

3. 编辑 `configs/my_game.yaml` 与 `.env`（YAML 里用 `api_key_env` 引用环境变量名）：

```yaml
language: en-US

players:
  - name: Player1
    model: your-model-name        # 如 qwen3.5-plus, deepseek-chat, gpt-4o 等
    base_url: https://your-api-url/v1
    api_key_env: OPENAI_API_KEY     # 对应 .env 中的变量名
  # ... 6-20 个玩家
```

支持任何兼容 OpenAI Chat Completions 格式的 API（DeepSeek、SiliconFlow、小米、通义千问等）。

### 运行游戏

```bash
# 控制台模式（纯文本日志，推荐开发测试用）
uv run python -m llm_werewolf.interface.cli --config configs/my_game.yaml

# TUI 模式（交互式终端界面）
uv run werewolf-tui configs/my_game.yaml

# Demo 模式（不需要 API，用随机 Agent 测试）
uv run werewolf configs/demo.yaml
```

## 项目架构

```
src/llm_werewolf/
├── game_runtime/          # 狼人杀规则、角色、动作、状态、引擎与配置
├── agent_team/            # AgentScope Agent、消息路由、信息隔离、LLM 调用封装
├── strategy/              # 角色 Prompt、结构化决策、阶段输出契约、投票意向
├── interface/             # CLI / TUI / 评测入口与模式选择
├── ui/                    # TUI 界面与展示组件
└── evaluation/            # 对局评测、日志记录、复盘分析
```

## 当前进度

- [x] 游戏引擎核心流程（异步化改造完成）
- [x] 多模型支持（OpenAI/Anthropic/DeepSeek/Ollama）
- [x] 20+ 角色系统
- [x] YAML 配置
- [x] Demo 模式验证
- [x] AgentScope 接入（ReAct + agent_team + InformationHub）
- [x] 阶段内 AI 经 PhaseInteraction / InformationHub 统一调度
- [ ] 结构化日志（JSON 事件流）
- [ ] Web 前端观战 UI
- [x] 评测与复盘（vote intention / swing 分析）

## 团队分工

| 成员 | 负责模块 |
|------|----------|
| A | AgentScope 接入 + `agent_team` |
| B | GameEngine 改造 + 异步化 |
| C | 前端 + API + 日志 |

## 致谢

- [AgentScope](https://github.com/agentscope-ai/agentscope) — Agent 执行框架

## License

MIT

## Conventions

- **Commit**: Use [Conventional Commits](https://www.conventionalcommits.org/) format. See [docs/archive/workflow.md](docs/archive/workflow.md).
- **ADR**: For cross-module/interface/performance decisions, write a 5-minute ADR. See [docs/archive/adr/](docs/archive/adr/).
- **Architecture**: See [docs/工程架构重构计划.md](docs/工程架构重构计划.md).
- **Roadmap**: See [docs/archive/roadmap.md](docs/archive/roadmap.md).
