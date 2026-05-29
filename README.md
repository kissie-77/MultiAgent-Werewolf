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

3. 编辑 `configs/my_game.yaml` 与 `.env`（YAML 里用 `api_key_env` / `model_env` 引用环境变量名，密钥与接入点 ID 只写进 `.env`）：

```yaml
language: en-US

players:
  - name: Player1
    model: your-model-name        # 或直接写 model_env: ARK_EP（Doubao）
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

### 对局模式（命令行参数）

`llm-werewolf` 与 `werewolf-tui` 支持以下可选参数（缺省时行为与原来完全一致）：

| 参数 | 作用 | 默认 |
|------|------|------|
| `--human_seat 1`（或 `1,3`） | 指定 1-based 座位为**人类玩家**（可多座位） | 无（纯 Agent 局） |
| `--players N` | 覆盖**总座位数（含人类）**，范围 6–20 | 沿用 YAML 名单 |
| `--badge_flow` / `--nobadge_flow` | 开 / 关**警长·警徽流** | 关 |

```bash
# 纯 LLM 对战
uv run llm-werewolf --config configs/llm-6p-deepseek.yaml

# 人机对战：你坐 1 号，其余 5 个 AI 当对手
uv run llm-werewolf --config configs/llm-6p-deepseek.yaml --human_seat 1

# 离线人机对战（无需 API Key，对手为 demo 机器人）；并开警徽流、扩到 9 人
uv run llm-werewolf --config configs/human-6p-demo.yaml --players 9 --badge_flow
```

人类玩家只需输入：**选人/投票→座位号**，**是否→`1`/`0`**，**发言→中文**，**女巫→`救` 或 `毒 3`**。

> Windows 本机运行前请前置 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`（GBK 控制台渲染 emoji 的兼容问题）。
> API Key 仅 LLM 玩家需要（写入 `.env`）；`human` / `demo` 座位无需 Key。详见
> [docs/reports/人机对战与命令行模式.md](docs/reports/人机对战与命令行模式.md)。

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
- [x] 人机对战 / 可配置人数 / 警徽流（命令行参数，详见 [docs/reports/人机对战与命令行模式.md](docs/reports/人机对战与命令行模式.md)）
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

## 仓库说明

- `src/`：项目源码，按六大板块组织
- `tests/`：自动化测试
- `configs/`：对局与模型配置
- `scripts/`：辅助脚本
- `docs/`：设计、记录、评测与归档文档，目录说明见 [docs/README.md](docs/README.md)
- `artifacts/`：本地运行产物与数据目录，不纳入版本管理
- `artifacts/runs/`：单局对战与赛后分析产物
- `artifacts/data/`：本地数据目录
- `.tmp/`：本地临时文件目录，不纳入版本管理
- `.venv/`、`.uv-cache/`、`.pytest_cache/`、`.agents/`、`.claude/`：本地开发/工具环境目录

## Conventions

- **Commit**: Use [Conventional Commits](https://www.conventionalcommits.org/) format. See [docs/archive/workflow.md](docs/archive/workflow.md).
- **ADR**: For cross-module/interface/performance decisions, write a 5-minute ADR. See [docs/archive/adr/](docs/archive/adr/).
- **Architecture**: See [docs/architecture/工程架构重构计划.md](docs/architecture/工程架构重构计划.md).
- **Roadmap**: See [docs/archive/roadmap.md](docs/archive/roadmap.md).
