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

1. 复制示例配置文件：
```bash
cp configs/example.yaml configs/my_game.yaml
```

2. 编辑 `configs/my_game.yaml`，填入你的 API 信息：
```yaml
language: en-US

player_roster:
  count: 12
  mode: all_agent
  llm_template:
    name_prefix: Player
    model: your-model-name        # 如 qwen3.5-plus, deepseek-chat, gpt-4o 等
    base_url: https://your-api-url/v1
    api_key_env: YOUR_API_KEY_ENV # 保存 API Key 的环境变量名
  # count 支持 6-20；也可以用 CLI --num_players 覆盖
```

支持任何兼容 OpenAI Chat Completions 格式的 API（DeepSeek、SiliconFlow、小米、通义千问等）。

### Shell / CLI 运行方式

Shell/CLI 模式会在终端里输出完整游戏进程，适合开发、调试和后台观察 Agent 原始动作。人机对战时，真人玩家也在同一个 shell 里输入。

#### Demo 对局（不需要 API）

```powershell
uv run python -m llm_werewolf.interface.cli --config configs/demo.yaml
```

也可以使用脚本别名：

```powershell
uv run werewolf --config configs/demo.yaml
```

#### DeepSeek 纯 LLM 对局

```powershell
cd D:\AI_werewolf\MultiAgent-Werewolf-add-skill-files-20260525
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uv run python -m llm_werewolf.interface.cli --participation=all_agent --rules=badge_flow --num_players=12 --enable_sheriff=True --show_agent_raw=True
```

也可以显式指定配置文件：

```powershell
uv run python -m llm_werewolf.interface.cli --config configs/llm-12p-deepseek.yaml --num_players=9 --enable_sheriff=False
```

#### DeepSeek 人机对战

```powershell
cd D:\AI_werewolf\MultiAgent-Werewolf-add-skill-files-20260525
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uv run python -m llm_werewolf.interface.cli --participation=human_mixed --rules=badge_flow --num_players=9 --enable_sheriff=True --show_agent_raw=True
```

Shell 人机对战中，真人玩家只需要两类输入：

- 技能、目标、投票：输入数字，例如 `1`
- 白天发言：输入纯文字，例如 `我先听大家发言，暂时观察站边变化。`

如需中止对局，按 `Ctrl+C`。对局结束或不再需要时，可以清掉当前终端中的 Key：

```powershell
Remove-Item Env:DEEPSEEK_API_KEY
```

#### 豆包 / 火山方舟纯 LLM 对局

项目已提供旧式固定人数豆包配置：

- `configs/llm-6p-doubao.yaml`
- `configs/llm-9p-doubao.yaml`

运行 6 人豆包对局：

```powershell
$env:ARK_API_KEY="你的火山方舟 API Key"
uv run python -m llm_werewolf.interface.cli --config configs/llm-6p-doubao.yaml
```

运行 9 人豆包对局：

```powershell
$env:ARK_API_KEY="你的火山方舟 API Key"
uv run python -m llm_werewolf.interface.cli --config configs/llm-9p-doubao.yaml
```

豆包配置目前仍是固定 `players:` 写法，不建议搭配 `--num_players` 使用；如需自由人数，后续应迁移为 `player_roster` 模板配置。

### TUI 运行方式

TUI 模式会打开交互式终端界面。当前设计是默认先进入设置页；命令行参数只作为设置页默认值，不会直接绕过确认开局。

#### TUI Demo 对局（不需要 API）

```powershell
uv run python -m llm_werewolf.interface.tui --config configs/demo.yaml
```

也可以使用脚本别名：

```powershell
uv run werewolf-tui --config configs/demo.yaml
```

#### TUI DeepSeek 纯 LLM 对局

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uv run python -m llm_werewolf.interface.tui --participation=all_agent --rules=badge_flow --num_players=12 --enable_sheriff=True --show_agent_raw=True
```

进入 TUI 设置页后确认模式、人数、警徽流和原始输出选项，再开始游戏。

#### TUI DeepSeek 人机对战

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uv run python -m llm_werewolf.interface.tui --participation=human_mixed --rules=badge_flow --num_players=9 --enable_sheriff=True --show_agent_raw=True
```

TUI 人机对战中，真人玩家在游戏页底部输入栏操作：

- 技能、目标、投票：输入数字并回车
- 白天发言：输入纯文字并回车

例如女巫阶段会显示 `女巫行动：1=使用解药，2=使用毒药，3=不行动`，直接输入对应数字即可。

#### TUI 豆包对局

```powershell
$env:ARK_API_KEY="你的火山方舟 API Key"
uv run python -m llm_werewolf.interface.tui --config configs/llm-6p-doubao.yaml
```

或：

```powershell
$env:ARK_API_KEY="你的火山方舟 API Key"
uv run python -m llm_werewolf.interface.tui --config configs/llm-9p-doubao.yaml
```

### 开局参数说明

常用参数在 Shell/CLI 和 TUI 中都可使用：

- `--participation=all_agent`：纯 LLM 对局。
- `--participation=human_mixed`：1 名真人 + 多名 LLM。
- `--rules=badge_flow`：使用带警徽流的推荐规则入口。
- `--num_players=<6-20>`：覆盖 `player_roster.count`，动态选择对局人数。
- `--enable_sheriff=True`：启用警长/警徽流。
- `--enable_sheriff=False`：跳过警长选举。
- `--show_agent_raw=True`：显示 AgentScope 原始输出，包括 Agent thinking、动作选择和发言内容，适合后台观察。
- `--config configs/xxx.yaml`：直接使用指定配置文件。

DeepSeek 的人机配置和全 LLM 配置都使用 `player_roster` 模板，因此支持 `--num_players`。旧式 `players:` 明细配置仍然可用，但不能用 `--num_players` 临时改人数；需要改成 `player_roster` 才支持动态人数。

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
- [x] AgentScope 接入（ReAct + InformationHub + 适配层）
- [x] 阶段内 AI 经 PhaseInteraction / InformationHub 统一调度
- [ ] 结构化日志（JSON 事件流）
- [ ] Web 前端观战 UI
- [x] 评测与复盘（vote intention / swing 分析）

## 团队分工

| 成员 | 负责模块 |
|------|----------|
| A | AgentScope 接入 + 适配层 |
| B | GameEngine 改造 + 异步化 |
| C | 前端 + API + 日志 |

## 致谢

- [AgentScope](https://github.com/agentscope-ai/agentscope) — Agent 执行框架

## License

MIT

## Conventions

- **Commit**: Use [Conventional Commits](https://www.conventionalcommits.org/) format. See [docs/workflow.md](docs/workflow.md).
- **ADR**: For cross-module/interface/performance decisions, write a 5-minute ADR. See [docs/adr/](docs/adr/).
- **CHANGELOG**: Auto-generated by git-cliff. Do not hand-edit.
- **Roadmap**: See [docs/roadmap.md](docs/roadmap.md).
