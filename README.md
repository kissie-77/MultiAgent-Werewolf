# MultiAgent-Werewolf 🐺

基于多 Agent 协作框架的狼人杀智能体博弈系统。

## 项目简介

本项目构建一个多智能体协作/对抗的狼人杀博弈系统。每个 Agent 根据其扮演角色（狼人、预言家、女巫等）拥有独立的目标、策略与行动空间，在信息隔离的约束下进行推理、发言与决策。

**技术路线**：AgentScope 作为 Agent 执行底座 + 自建 GameEngine 管理游戏逻辑

**参考项目**：
- [LLMWereWolf](https://github.com/Mai0313/LLMWereWolf) — 游戏引擎架构（Mixin 模式）
- [werewolf_kills_agentscope](https://github.com/muranUSTB/werewolf_kills_agentscope) — AgentScope 用法 + 提示词设计

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

players:
  - name: Player1
    model: your-model-name        # 如 qwen3.5-plus, deepseek-chat, gpt-4o 等
    base_url: https://your-api-url/v1
    api_key_env: YOUR_API_KEY     # 你的 API 密钥
  # ... 6-20 个玩家
```

支持任何兼容 OpenAI Chat Completions 格式的 API（DeepSeek、SiliconFlow、小米、通义千问等）。

### 运行游戏

```bash
# 控制台模式（纯文本日志，推荐开发测试用）
uv run python src/llm_werewolf/cli.py --config configs/my_game.yaml

# TUI 模式（交互式终端界面）
uv run werewolf-tui configs/my_game.yaml

# Demo 模式（不需要 API，用随机 Agent 测试）
uv run werewolf configs/demo.yaml
```

## 项目架构

```
src/llm_werewolf/
├── cli.py                 # 控制台模式入口
├── tui.py                 # TUI 模式入口
├── ai/                    # Agent 系统（后续将替换为 AgentScope）
│   └── agents.py
├── core/                  # 核心游戏逻辑
│   ├── engine/            # 游戏引擎（Mixin 拆分）
│   │   ├── game_engine.py      # 主引擎
│   │   ├── base.py             # 主循环
│   │   ├── night_phase.py      # 夜晚阶段
│   │   ├── day_phase.py        # 白天讨论
│   │   ├── voting_phase.py     # 投票阶段
│   │   ├── death_handler.py    # 死亡处理
│   │   └── action_processor.py # 行动处理
│   ├── actions/           # 行动系统
│   ├── roles/             # 角色实现（20+ 角色）
│   ├── config/            # 配置系统
│   └── types/             # 类型定义
└── ui/                    # TUI 界面
```

## 当前进度

- [x] 游戏引擎核心流程（异步化改造完成）
- [x] 多模型支持（OpenAI/Anthropic/DeepSeek/Ollama）
- [x] 20+ 角色系统
- [x] YAML 配置
- [x] Demo 模式验证
- [ ] AgentScope 接入
- [ ] 信息隔离层（ObservationBuilder）
- [ ] 结构化日志（JSON 事件流）
- [ ] Web 前端观战 UI
- [ ] 评测与复盘体系

## 团队分工

| 成员 | 负责模块 |
|------|----------|
| A | AgentScope 接入 + 适配层 |
| B | GameEngine 改造 + 异步化 |
| C | 前端 + API + 日志 |

## 致谢

- [LLMWereWolf](https://github.com/Mai0313/LLMWereWolf) — 游戏引擎基础
- [AgentScope](https://github.com/agentscope-ai/agentscope) — Agent 执行框架
- [werewolf_kills_agentscope](https://github.com/muranUSTB/werewolf_kills_agentscope) — 提示词设计参考

## License

MIT
