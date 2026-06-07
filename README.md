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

## 本地全栈开发（前端 + 后端）

Web 联调时前后端分开起：后端跑 FastAPI（默认 `:8000`，本仓库联调用 `:8010`），前端跑 Vite 开发服务器并把 `/api` 代理到后端。

**1) 启动后端 API**

```bash
# 仓库根目录；注入有效 LLM Key（仅 AI 座位需要），端口 8010
DEEPSEEK_API_KEY=sk-xxxx OBS_READY_REQUIRE_LLM=0 uv run werewolf-api --port 8010
```

- `DEEPSEEK_API_KEY`：AI 座位调用 LLM 用的密钥（也可写进 `.env`）；纯 demo 观战可省略。
- `OBS_READY_REQUIRE_LLM=0`：让 `/ready` 不强制校验 LLM，没真 Key 时也能通过就绪检查。
- 健康检查：`GET http://localhost:8010/health` → `{"status":"ok"}`；`GET /ready` → `{"status":"ready"}`。

**2) 启动前端**

```bash
cd frontend
npm install                                     # 首次
VITE_API_PROXY=http://localhost:8010 npm run dev
```

- `VITE_API_PROXY` 必须指向后端端口；Vite 把 `/api`、`/ready` 代理过去（见 `frontend/vite.config.ts`），缺省指向 `:8000`。
- Vite 默认开在 `http://localhost:5173`（端口被占用时自动顺延，以终端打印为准）。

**3) 进入游戏**

浏览器打开 Vite 打印的地址 →「进入盘面」：

- **观战（god 视角）**：直接看 6 个 AI 互相博弈（白天发言 / 黑夜狼聊 / 投票全程，SSE 实时下行）。
- **人机对战（座位视角）**：在开局设置里选模式 + 座位；开局后带 `player_token` 跳到座位视图，URL 形如
  `/game?run_id=<id>&view=seat&seat=<N>&token=<player_token>`，轮到你时弹层让你发言 / 投票 / 用药。

> 端口一致性：后端用哪个端口，前端 `VITE_API_PROXY` 就填哪个，否则 `/api` 转发 404。
> 密钥安全：AI 座位的 Key 只在服务端环境变量里（不进前端、不进请求体）；座位令牌 `seat{N}-{run_id}` 仅防误操作。

前后端打通与人机对战的完整说明见 [docs/reports/前后端打通与人机对战-2026-06-06.md](docs/reports/前后端打通与人机对战-2026-06-06.md)。

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
- [x] Web 前端观战 UI / 人机对战（FastAPI + React/Three.js + SSE 实时直播 + 座位输入，详见上方「本地全栈开发」）
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
- `项目评分报告.md`：模块评分、问题核实与修复状态（2026-06-05）
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
