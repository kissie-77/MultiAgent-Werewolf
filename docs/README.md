# 文档导航

`docs/` 按**模块三件套**组织（见 [DOC_TEMPLATE.md](./DOC_TEMPLATE.md)）。历史分区 `memory/`、`reports/`、`archive/` 仍保留作参考。

## 模块文档（README · DESIGN · ROADMAP）

| 模块 | 入口 |
|------|------|
| game_runtime | [README](./game_runtime/README.md) · [DESIGN](./game_runtime/DESIGN.md) · [ROADMAP](./game_runtime/ROADMAP.md) |
| agent_team | [README](./agent_team/README.md) · [DESIGN](./agent_team/DESIGN.md) · [ROADMAP](./agent_team/ROADMAP.md) |
| strategy | [README](./strategy/README.md) · [DESIGN](./strategy/DESIGN.md) · [ROADMAP](./strategy/ROADMAP.md) |
| evaluation | [README](./evaluation/README.md) · [DESIGN](./evaluation/DESIGN.md) · [ROADMAP](./evaluation/ROADMAP.md) |
| interface | [README](./interface/README.md) · [DESIGN](./interface/DESIGN.md) · [ROADMAP](./interface/ROADMAP.md) |
| ui | [README](./ui/README.md) · [DESIGN](./ui/DESIGN.md) · [ROADMAP](./ui/ROADMAP.md) |
| frontend | [README](./frontend/README.md) · [DESIGN](./frontend/DESIGN.md) · [ROADMAP](./frontend/ROADMAP.md) |
| architecture | [工程结构整理方案](./architecture/工程结构整理方案.md) · [信念矩阵功能设计](./architecture/信念矩阵功能设计.md) |

## 其他目录

| 目录 | 用途 |
|------|------|
| `architecture/` | 跨模块工程方案 |
| `memory/` | 记忆板块历史记录 |
| `evaluation/` 内 legacy | `PostGame产物地图.md` 等，结论以 DESIGN 为准 |
| `reports/` | 专项报告、排查过程稿 |
| `archive/` | 已归档文档 |

## 写作规范

- 统一模板：[DOC_TEMPLATE.md](./DOC_TEMPLATE.md)
- 新结论写入模块 `DESIGN.md`，进度写入 `ROADMAP.md`
- 根目录 [前端规划.md](./archive/前端规划.md)：Web 14 页与 API 对接（frontend 模块）
