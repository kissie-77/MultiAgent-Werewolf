# MultiAgent-Werewolf 🐺

基于多 Agent 协作框架的狼人杀智能体博弈系统。

[![CI](https://github.com/kissie-77/MultiAgent-Werewolf/actions/workflows/test.yml/badge.svg)](https://github.com/kissie-77/MultiAgent-Werewolf/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 项目简介

本项目构建一个多智能体协作/对抗的狼人杀博弈系统。每个 Agent 根据其扮演角色（狼人、预言家、女巫等）拥有独立的目标、策略与行动空间，在信息隔离的约束下进行推理、发言与决策。

**技术路线**：AgentScope 作为 Agent 执行底座 + 自建 GameEngine 管理游戏逻辑

**核心特性**：

- 🎭 **20+ 角色系统**：支持标准板子与自定义板子（4/6/8/12/16 人）
- 🧠 **多层记忆系统**：工作记忆、情景记忆、语义记忆、程序记忆
- 📊 **信念矩阵**：一阶/二阶信念追踪，支持信念模式识别与信号检测
- 🗳️ **投票意向追踪**：Foaster 风格的投票意向复盘与说服分析
- 🌐 **Web 全栈**：FastAPI + React/Three.js + SSE 实时直播 + 人机对战
- 🚀 **并行多栈（fleet）**：同时开多局，支持批量评测
- 📝 **结构化日志**：JSONL 事件流 + SSE 推送 + 赛后复盘视图
- 🔊 **音频系统**：BGM + 事件音效，增强沉浸感
- 📦 **Docker 部署**：一键生产部署，含健康检查与告警
- 🔬 **多模型评测**：同一局内混排 8 种模型、3 个服务商，统一事件协议与评分口径
- 🔄 **Prompt/Skill 自进化**：A/B 实验验证 Wolf Benefit +35.7%、MVP +9.3%

## 快速开始

以下流程适用于 **Python CLI 模式**和 **Web 全栈开发**。

### 1. 环境自检

先检查本机是否满足所有开发前提：

```bash
# macOS / Linux（或 Git Bash）
make check-env

# Windows PowerShell
.\scripts\check-env.ps1

# 仅检查后端（跳过 Node.js）
.\scripts\check-env.ps1 -SkipFrontend
```

脚本会检测以下工具是否存在、版本是否达标，并对缺失工具给出安装指引：

| 工具                          | 版本       | 用途                                    |
| ----------------------------- | ---------- | --------------------------------------- |
| Python                        | ≥ 3.10    | 运行后端游戏引擎                        |
| [uv](https://docs.astral.sh/uv/) | ≥ 0.4     | Python 依赖管理（uv 会自动获取 Python） |
| Node.js                       | ≥ 18      | 前端 React 开发（仅全栈开发需要）       |
| npm                           | 随 Node.js | 前端依赖安装                            |
| Docker（可选）                | 20+        | 生产部署                                |

### 2. 一键初始化

```bash
make setup
```

`make setup` 会依次完成：

1. **安装 Python 依赖**（`uv sync --group dev --group test`）
2. **创建 `.env` 配置文件**（从 `.env.example` 复制，首次需要）
3. **安装 pre-commit hooks**（代码质量自动检查）
4. **安装前端依赖**（检测到 Node.js 时自动执行 `npm install`）

> **Windows 用户注意**：如果本机没有 `make`，可以使用 Git Bash（`winget install Git.Git`），或手动执行：
>
> ```powershell
> uv sync --group dev --group test
> if (-not (Test-Path .env)) { Copy-Item .env.example .env }
> cd frontend; npm install; cd ..
> ```

### 3. 启动开发

**全栈开发（Web 界面 + 后端）**：

```powershell
# Windows PowerShell（仓库根目录）
.\dev.ps1

# 打开浏览器
.\dev.ps1 -OpenBrowser

# 仅后端或仅前端
.\dev.ps1 -BackendOnly
.\dev.ps1 -FrontendOnly
```

```bash
# macOS / Linux（仓库根目录）
./dev.sh

# 或
make dev
```

默认端口：后端 `8010`，前端 `5173`（Vite 被占用时自动顺延）。

**CLI 模式（无需前端）**：

```bash
make demo                         # 6 人 Demo（无需 API Key）
make demo9                        # 9 人 + 警徽流

uv run werewolf configs/my_game.yaml          # 自定义配置
uv run llm-werewolf --config configs/llm-6p-deepseek.yaml  # LLM 对战
```

**Docker 部署**：

```bash
cp .env.example .env              # 填入 API Key
make docker-up                    # 构建并启动
# → 访问 http://localhost
```

### 对局模式（命令行参数）

`llm-werewolf` 与 `werewolf-tui` 支持以下可选参数（缺省时行为与原来完全一致）：

| 参数                                  | 作用                                              | 默认              |
| ------------------------------------- | ------------------------------------------------- | ----------------- |
| `--human_seat 1`（或 `1,3`）      | 指定 1-based 座位为**人类玩家**（可多座位） | 无（纯 Agent 局） |
| `--players N`                       | 覆盖**总座位数（含人类）**，范围 6–20      | 沿用 YAML 名单    |
| `--badge_flow` / `--nobadge_flow` | 开 / 关**警长·警徽流**                     | 关                |

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

## 全栈开发

Web 联调默认端口：**后端 `8010`**，**前端 `5173`**。

### 手动分步启动（两个终端）

**终端 1 — 后端**

```bash
OBS_READY_REQUIRE_LLM=0 uv run werewolf-api --port 8010
```

**终端 2 — 前端**

```bash
cd frontend && npm install && npm run dev
```

更多排查见 [docs/frontend/DEV.md](docs/frontend/DEV.md) 和 [docs/reports/前后端打通与人机对战-2026-06-06.md](docs/reports/前后端打通与人机对战-2026-06-06.md)。

## 并行多栈（fleet）：同时开多局

一条命令拉起 N 套（后端 + 前端）各自独立端口，用于并行开局（批量评测 / 多个真人各自一局）。

```bash
# 拉起 2 套后端(8010/8011) + 2 套前端(5173/5174)；Ctrl-C 全部停止
DEEPSEEK_API_KEY=sk-xxx uv run werewolf-fleet up --backends 2

# 仅后端（评测用，不起 vite）
uv run werewolf-fleet up --backends 4 --frontends 0

# 批量开局：把 20 局分发到 4 个后端，并发 4、相邻启动错峰 1.5s（抗 429）
uv run werewolf-fleet batch --config llm-6p-deepseek --count 20 --backends 4 --concurrency 4 --stagger 1.5
```

- 每个后端进程拿到 `WEREWOLF_INSTANCE_TAG=iN`，`run_id` 形如 `6p-deepseek-<ts>-iN`，多后端共享 `artifacts/runs/` 不会撞车（单后端同秒双开也已修，靠目录存在性计数器兜底）。
- 每个前端通过 `VITE_API_PROXY` 指向自己的后端；人机对战把 `http://localhost:<fe_port>/` 分给各真人即可。
- 日志：`artifacts/fleet/<stamp>/backend-iN.log` / `frontend-iN.log`；批量汇总 `artifacts/fleet/<stamp>/batch_summary.json`。
- **限流提示**：所有后端共用同一个 LLM key，规模大时用 `--concurrency` / `--stagger` 错峰，避免 429。

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

| 变量                                 | 说明                 | 示例                           |
| ------------------------------------ | -------------------- | ------------------------------ |
| `OPENAI_API_KEY` / `ARK_API_KEY` | LLM 接入密钥         | `sk-...`                     |
| `OBS_ALERT_WEBHOOK_URL`            | 告警推送地址（可选） | `https://open.feishu.cn/...` |
| `OBS_ALERT_MIN_SEVERITY`           | 最低告警级别         | `warning`（默认）            |
| `WEB_PORT`                         | 前端监听端口         | `80`（默认）                 |

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
>
> ```bash
> uv run poe test-fast     # 等价于 make test-fast
> uv run poe lint          # 等价于 make lint
> ```

## 项目架构

项目采用“规则引擎 / Agent 执行 / 策略资产 / 接口与评测”分层，核心目标是让狼人杀规则、LLM 调用、Prompt/Skill 版本和赛后评测彼此解耦。

```
src/llm_werewolf/
├── game_runtime/          # 规则引擎：角色、夜间行动、死亡链、投票、胜负与事件
├── agent_team/            # Agent 执行层：AgentScope、InformationHub、信息隔离、记忆、Skill 注入
├── strategy/              # 策略契约层：Prompt 包、结构化输出 schema、信念矩阵、投票意向
├── evaluation/            # 评测闭环：赛后评分、复盘、Skill 抽取、版本进化与 leaderboard
├── interface/             # 入口层：CLI、FastAPI、fleet 多进程调度
├── observability/         # 健康检查、告警规则、Webhook 通知
└── ui/                    # CLI/Rich 展示组件
```

### 运行链路

1. `interface` 读取 YAML 配置，解析座位、角色、模型、Prompt/Skill 版本。
2. `game_runtime` 创建 `GameEngine`，按昼夜阶段推进规则，并通过事件流记录状态变化。
3. `agent_team` 为每个座位装配 AgentScope Agent，`InformationHub` 按可见性分发公开/私密信息。
4. `strategy` 为发言、投票、夜间行动等阶段提供角色 Prompt、结构化决策 schema 和信念矩阵上下文。
5. Agent 输出经 `WerewolfAdapterBridge` 解析为 `SpeechDecision`、`SeatChoiceDecision`、`WitchNightDecision` 等结构化决策，再回写到引擎。
6. 对局结束后，`evaluation` 读取事件、票型、发言和信念变化，生成评分、复盘、Skill 候选和版本对比数据。

### Prompt 与 Skill 版本体系

- 角色 Prompt：`src/llm_werewolf/strategy/prompts/roles/<role>/<version>/`
- 阶段 Prompt：`src/llm_werewolf/strategy/prompts/phase/<version>/`
- Plan 策略：`src/llm_werewolf/strategy/prompts/plans/<version>/`
- Skill 卡片：`src/llm_werewolf/agent_team/skills/<role>/<version>/*.md`
- 运行时版本映射由 `RoleVersionManifest` 管理，可以按角色分别 pin prompt 和 skill 版本。
- 未显式 pin 的角色默认解析磁盘上的最新版本；正式实验建议在配置或实验脚本中显式指定版本，避免新增目录影响基线。

### 模块边界

| 模块             | 职责                                                 | 不负责                   |
| ---------------- | ---------------------------------------------------- | ------------------------ |
| `game_runtime` | 狼人杀规则、阶段推进、状态与事件                     | LLM 调用、Prompt 设计    |
| `agent_team`   | Agent 创建、信息隔离、记忆、Skill 注入、LLM 调用适配 | 规则判定、赛后评分       |
| `strategy`     | Prompt 资产、结构化决策契约、信念矩阵、投票意向      | Agent 生命周期、游戏状态 |
| `evaluation`   | 复盘、评分、Skill 生成、版本进化实验                 | 实时对局推进             |
| `interface`    | CLI/API/fleet 装配入口                               | 核心规则和策略实现       |
| `frontend`     | React 观战、人机对战、回放与配置界面                 | 后端规则执行             |

更完整的模块文档见 [docs/README.md](docs/README.md)。

## 当前进度

- [X] 游戏引擎核心流程（异步化改造完成）
- [X] 多模型支持（OpenAI/Anthropic/DeepSeek/Ollama/Doubao/Kimi/Gemini）
- [X] 20+ 角色系统（含标准板子 4/6/8/12/16 人）
- [X] YAML 配置（对局、角色板子、模型提供商）
- [X] Demo 模式验证（无需 API Key）
- [X] AgentScope 接入（ReAct + agent_team + InformationHub）
- [X] 阶段内 AI 经 PhaseInteraction / InformationHub 统一调度
- [X] 人机对战 / 可配置人数 / 警徽流（命令行参数，详见 [docs/reports/人机对战与命令行模式.md](docs/reports/%E4%BA%BA%E6%9C%BA%E5%AF%B9%E6%88%98%E4%B8%8E%E5%91%BD%E4%BB%A4%E8%A1%8C%E6%A8%A1%E5%BC%8F.md)）
- [X] 结构化日志（JSONL 事件流 + SSE 推送 + log_views 赛后复盘视图）
- [X] Web 前端观战 UI / 人机对战（FastAPI + React/Three.js + SSE 实时直播 + 座位输入，详见上方「本地全栈开发」）
- [X] 评测与复盘（vote intention / swing 分析 / 反事实推演 / MVP 评分）
- [X] 女巫 / 守卫毒奶规则与死亡链（182 项自动化测试）
- [X] 多层记忆系统（工作记忆 / 情景记忆 / 语义记忆 / 程序记忆）
- [X] 信念矩阵（一阶/二阶信念 / 信念模式识别 / 信号检测）
- [X] 投票意向追踪（Foaster 风格复盘）
- [X] 音频系统（BGM + 事件音效）
- [X] 并行多栈 fleet（批量评测 / 多局并发）
- [X] 监控预警（健康检查 / Webhook 告警）
- [X] Prompt 自动进化与 A/B 对比实验（Wolf Benefit +35.7%、MVP +9.3%；Prophet+Witch MVP +20.4%）

## 实验验证

### 多模型 8P 对局评测

8 局标准 8 人局（7 局多模型混排 + 1 局同模型基线），覆盖 8 种模型、3 个服务商（Ark / OpenAI / SiliconFlow）：

| 指标 | 结果 |
|---|---|
| 完成对局 | 8 |
| 好人胜利 / 狼人胜利 | 4 / 4 |
| 平均 Benefit | 27.61 |
| 平均 MVP | 63.33 |
| 平均 Alert 数 | 2.25 |

**结论**：多模型混排未让某一阵营系统性失衡；平台可在同一博弈环境中公平对抗评测，并识别"败方高贡献玩家"。详见 [multi_model_8p_report.md](../multi_model_8p_report.md)。

### Prompt/Skill 自进化 A/B 对比

固定目标角色、5 局有效样本、异常重跑、输局保留：

| 测试组 | 版本 | 胜率 | 平均 Benefit | 平均 MVP |
|---|---|---|---|---|
| Wolf | v1 | 80.0% | 30.05 | 65.48 |
| Wolf | v2 | 40.0% | **40.79 (+35.7%)** | **71.56 (+9.3%)** |
| Prophet+Witch | v1 | 60.0% | 42.48 | 62.64 |
| Prophet+Witch | v2 | 40.0% | 38.57 | **75.40 (+20.4%)** |

**结论**：v2 从"角色原则"升级为"局面触发策略"，显著提升过程评分；平台形成"经验沉淀 → 策略调用 → 指标提升 → 继续迭代"的自进化闭环。详见 [prompt_skill_ab_report.md](../prompt_skill_ab_report.md)。

## 团队分工

| 成员 | 负责模块                                              |
| ---- | ----------------------------------------------------- |
| A    | AgentScope 接入 +`agent_team` + 记忆系统 + 信念矩阵 |
| B    | GameEngine 改造 + 异步化 + 角色系统 + 规则引擎        |
| C    | 前端 + API + 结构化日志 + 音频系统 + fleet 并行       |

> 注：具体分工可能随项目迭代调整，详见各模块 `docs/*/ROADMAP.md`。

## 致谢

- [AgentScope](https://github.com/agentscope-ai/agentscope) — Agent 执行框架

## License

MIT

## 仓库说明

- `src/`：后端源码，按 `game_runtime`、`agent_team`、`strategy`、`evaluation`、`interface`、`observability` 等模块组织。
- `frontend/`：React/Vite 前端，用于观战、人机对战、回放和配置管理。
- `tests/`：自动化测试（182 项），覆盖规则、策略、评测、接口、观测等模块。
- `configs/`：对局、角色板子、模型提供商与本地演示配置（含标准 4/6/8/12/16 人板子）。
- `scripts/`：实验、回填、连通性检查、版本整理等辅助脚本。
- `docs/`：设计、Roadmap、专题报告与归档文档，目录说明见 [docs/README.md](docs/README.md)。
- `artifacts/`、`outputs/`：本地运行、实验和赛后分析产物，不建议纳入版本管理。
- `.env`：本地 API Key 和 endpoint，只在本机保存，不提交。
- `.tmp/`、`.venv/`、`.uv-cache/`、`.uv-python/`、`.pytest_cache/`、`__pycache__/`：本地临时、依赖、缓存目录，不纳入版本管理。

## Conventions

- **Commit**: Use [Conventional Commits](https://www.conventionalcommits.org/) format. See [docs/archive/workflow.md](docs/archive/workflow.md).
- **ADR**: For cross-module/interface/performance decisions, write a 5-minute ADR. See [docs/archive/adr/](docs/archive/adr/).
- **Architecture**: See [docs/architecture/工程架构重构计划.md](docs/architecture/%E5%B7%A5%E7%A8%8B%E6%9E%B6%E6%9E%84%E9%87%8D%E6%9E%84%E8%AE%A1%E5%88%92.md).
- **Roadmap**: See [docs/archive/roadmap.md](docs/archive/roadmap.md).
