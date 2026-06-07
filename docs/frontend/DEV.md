# 前端本地开发

## 环境文件（单一真源）

| 文件 | 用途 | 是否提交 |
|------|------|----------|
| 仓库根 `.env` | 后端 LLM API Key（`ARK_API_KEY`、`DEEPSEEK_API_KEY` 等） | 否（gitignore） |
| 根 `.env.example` | 后端密钥模板 | 是 |
| `frontend/.env.development` | Vite 开发变量（`VITE_API_PROXY`） | 是 |
| `frontend/.env.local` | 本机覆盖（可选） | 否 |

**不要把 LLM 密钥写进 `frontend/`**；开局页「枢纽引擎」通过 `POST /api/v1/settings/api-keys` 写入根目录 `.env`。

## 启动

**一键（推荐）**

```powershell
# Windows — 必须在仓库根目录执行
.\dev.ps1
.\dev.ps1 -OpenBrowser          # 启动后打开浏览器
.\dev.ps1 -BackendOnly          # 仅 API（新窗口）
.\dev.ps1 -FrontendOnly         # 仅 Vite（API 已在 8010 时）
.\dev.ps1 -ApiPort 8020         # 非默认端口（需同步改 .env.development）
```

```bash
# macOS / Linux — 必须在仓库根目录执行
./dev.sh
API_PORT=8020 ./dev.sh
# 或 make dev
```

**手动（两个终端）**

```bash
# 终端 1 — 仓库根目录
OBS_READY_REQUIRE_LLM=0 uv run werewolf-api --port 8010

# 终端 2
cd frontend && npm install && npm run dev
```

浏览器打开 Vite 打印的地址（通常 `http://localhost:5173`）。

## 代理与端口

- `vite.config.ts` 将 `/api`、`/ready` 代理到 `VITE_API_PROXY`。
- 默认：`frontend/.env.development` → `http://127.0.0.1:8010`。
- 后端与前端端口必须一致，否则设置弹窗会出现 `Internal Server Error`（实为代理连不上后端）。

## 常用命令

```bash
cd frontend
npm run dev      # 开发
npm run build    # 生产构建
npm run lint     # tsc --noEmit
npm test         # vitest
```

## 目录约定

| 路径 | 说明 |
|------|------|
| `src/api/client.ts` | HTTP 客户端 |
| `src/lib/*` | 映射器、reducer、配置（活跃代码） |
| `src/components/` | UI 组件 |
| `src/pages/` | 路由页面 |

`src/services/` 已废弃，勿再新增；逻辑统一放在 `src/lib/`。

## 设置 API 故障排查

| 现象 | 处理 |
|------|------|
| `ModuleNotFoundError: llm_werewolf` | 根目录 `make setup` 或 `uv sync --group dev --group test`；一键脚本已设 `PYTHONPATH=src` |
| `settings/providers` 500 | 确认后端 `8010` 已启动；`curl http://127.0.0.1:8010/health` |
| 设置保存失败 | 确认根 `.env` 可写；本地需 loopback 访问或配置 `WEREWOLF_SETTINGS_TOKEN` |
| 模型下拉为空 | 在设置弹窗写入对应供应商 Key；豆包需 `ARK_API_KEY` + `ARK_EP` |

模型展示名：在根 `.env` 设置 `ARK_EP_DISPLAY` 等，见根 `.env.example`。
