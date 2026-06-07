# 贡献与本地约定

## 配置单一真源

| 类型 | 位置 | 说明 |
|------|------|------|
| LLM API Key | 仓库根 `.env` | 后端与 Settings API 唯一写入点 |
| 密钥模板 | 根 `.env.example` | 勿在 `frontend/` 再维护一份 |
| Vite 开发变量 | `frontend/.env.development` | 仅 `VITE_*`（如 `VITE_API_PROXY`） |
| 本机覆盖 | `frontend/.env.local` | gitignore，可选 |

## 一键本地全栈

| 平台 | 命令 |
|------|------|
| Windows | 仓库根目录 `.\dev.ps1` |
| macOS / Linux | 仓库根目录 `./dev.sh` 或 `make dev` |
| 分开启动 | `make dev-api` + `make dev-web`（两个终端） |

默认后端端口 **8010**，前端代理见 `frontend/.env.development`。

## 文档放哪

| 内容 | 路径 |
|------|------|
| 项目总览与快速启动 | `README.md` |
| 前端开发/排错 | `docs/frontend/DEV.md` |
| 模块设计 | `docs/<module>/README.md` |
| `frontend/README.md` | 仅指针，不写长文 |

## 提交前检查

```bash
make check          # 后端 lint + test
cd frontend && npm run lint && npm test
```

勿提交：`.env`、`.cursor/`、`.github/reports/`、本地 API 明文文件。
