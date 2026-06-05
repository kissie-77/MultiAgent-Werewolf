# MultiAgent-Werewolf 🐺

基于多 Agent 协作框架的狼人杀智能体博弈系统。

## 项目简介

本项目构建一个多智能体协作/对抗的狼人杀博弈系统。每个 Agent 根据其扮演角色（狼人、预言家、女巫等）拥有独立的目标、策略与行动空间，在信息隔离的约束下进行推理、发言与决策。

**技术路线**：AgentScope 作为 Agent 执行底座 + 自建 GameEngine 管理游戏逻辑

## 快速开始

### 前提

| 工具 | 版本 | 安装 |
|------|------|------|
| [uv](https://docs.astral.sh/uv/) | ≥ 0.4 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python | 3.10+ | 由 uv 自动管理（无需手动安装） |

### 一键初始化（推荐）

```bash
git clone https://github.com/kissie-77/MultiAgent-Werewolf.git
cd MultiAgent-Werewolf

make setup          # 安装依赖 + 创建 .env + 配置 pre-commit
```

`make setup` 会自动完成：安装 `dev` + `test` 依赖组、复制 `.env.example → .env`、安装 pre-commit hooks。

> **不喜欢 Makefile？** 等价命令：
> ```bash
> uv sync --group dev --group test   # 安装依赖
> cp .env.example .env               # 创建配置文件
> ```

### 配置 API

编辑 `.env` 填入密钥，再复制/编辑对局配置：

```bash
cp configs/example.yaml configs/my_game.yaml
# 编辑 configs/my_game.yaml 与 .env
```

YAML 里用 `api_key_env` / `model_env` 引用环境变量名，密钥只写进 `.env`：

```yaml
language: en-US

players:
  - name: Player1
    model: your-model-name        # 或 model_env: ARK_EP（Doubao）
    base_url: https://your-api-url/v1
    api_key_env: OPENAI_API_KEY   # 对应 .env 中的变量名
  # ... 6-20 个玩家
```

支持任何兼容 OpenAI Chat Completions 格式的 API（DeepSeek、SiliconFlow、通义千问等）。

### 运行游戏

```bash
make demo                         # Demo 模式（无需 API Key，6 人随机 Agent）
make demo9                        # Demo 模式（9 人 + 警徽流）

uv run werewolf configs/my_game.yaml          # 使用自定义配置
uv run llm-werewolf --config configs/llm-6p-deepseek.yaml  # LLM 对战
```

### 对局模式（命令行参数）

`llm-werewolf` 与 `werewolf-tui` 支持以下可选参数（缺省时行为与原来完全一致）：

| 参数                              | 作用                                        | 默认              |
| --------------------------------- | ------------------------------------------- | ----------------- |
| `--human_seat 1`（或 `1,3`）      | 指定 1-based 座位为**人类玩家**（可多座位） | 无（纯 Agent 局） |
| `--players N`                     | 覆盖**总座位数（含人类）**，范围 6–20       | 沿用 YAML 名单    |
| `--badge_flow` / `--nobadge_flow` | 开 / 关**警长·警徽流**                      | 关                |

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
> [docs/reports/人机对战与命令行模式.md](docs/reports/%E4%BA%BA%E6%9C%BA%E5%AF%B9%E6%88%98%E4%B8%8E%E5%91%BD%E4%BB%A4%E8%A1%8C%E6%A8%A1%E5%BC%8F.md)。

## 生产部署（Docker Compose）

```
[浏览器] → nginx:80 → /api/* → uvicorn:8000 (FastAPI)
                     → /*    → React SPA 静态文件
```

```bash
cp .env.example .env        # 填入 API Key 和 OBS_ALERT_WEBHOOK_URL
make docker-up              # 构建镜像并后台启动
# 等待健康检查通过后访问 http://localhost
make docker-logs            # 查看日志
make docker-down            # 停止
```

**关键环境变量**（写入 `.env`）：

| 变量 | 说明 | 示例 |
|------|------|------|
| `OPENAI_API_KEY` / `ARK_API_KEY` | LLM 接入密钥 | `sk-...` |
| `OBS_ALERT_WEBHOOK_URL` | 告警推送地址（可选） | `https://open.feishu.cn/...` |
| `OBS_ALERT_MIN_SEVERITY` | 最低告警级别 | `warning`（默认） |
| `WEB_PORT` | 前端监听端口 | `80`（默认） |

> 告警链路：游戏异常 → `AlertDispatcher` → `WebhookNotifier` → Webhook URL（飞书/钉钉/Slack 均可）

## 开发工作流

```bash
# 测试
make test            # 完整测试（含覆盖率，与 CI 保持一致）
make test-fast       # 快速测试（无覆盖率，并行加速，适合本地迭代）
make test-file f=tests/game_runtime/test_voting_context.py   # 单文件测试

# 代码质量
make lint            # ruff 检查
make fmt             # ruff 格式化 + 自动修复
make check           # lint + test-fast（提交前检查）

# 其他
make help            # 查看所有可用命令
```

> **使用 `poe`**（`poethepoet` 已内置在 dev 依赖中）：
> ```bash
> uv run poe test-fast     # 等价于 make test-fast
> uv run poe lint          # 等价于 make lint
> ```

## 项目架构

```
src/llm_werewolf/
├── game_runtime/          # 狼人杀规则、角色、动作、状态、引擎与配置
├── agent_team/            # AgentScope Agent、消息路由、信息隔离、LLM 调用封装
├── strategy/              # 角色 Prompt、结构化决策、阶段输出契约、投票意向
├── interface/             # CLI 入口（cli/）+ FastAPI（api/）
├── ui/                    # 控制台 Rich 展示（ConsolePresenter）
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
- [x] 人机对战 / 可配置人数 / 警徽流（命令行参数，详见 [docs/reports/人机对战与命令行模式.md](docs/reports/%E4%BA%BA%E6%9C%BA%E5%AF%B9%E6%88%98%E4%B8%8E%E5%91%BD%E4%BB%A4%E8%A1%8C%E6%A8%A1%E5%BC%8F.md)）
- [ ] 结构化日志（JSON 事件流）
- [ ] Web 前端观战 UI
- [x] 评测与复盘（vote intention / swing 分析）
- [x] 女巫 / 守卫毒奶规则与死亡链（915 项自动化测试）

## 团队分工

| 成员 | 负责模块                       |
| ---- | ------------------------------ |
| A    | AgentScope 接入 + `agent_team` |
| B    | GameEngine 改造 + 异步化       |
| C    | 前端 + API + 日志              |

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
- **Architecture**: See [docs/architecture/工程架构重构计划.md](docs/architecture/%E5%B7%A5%E7%A8%8B%E6%9E%B6%E6%9E%84%E9%87%8D%E6%9E%84%E8%AE%A1%E5%88%92.md).
- **Roadmap**: See [docs/archive/roadmap.md](docs/archive/roadmap.md).
