# 文档导航

`docs/` 按**模块三件套**组织（见 [DOC_TEMPLATE.md](./DOC_TEMPLATE.md)）。历史分区 `reports/`、`archive/` 仍保留作参考。

## 模块文档（README · DESIGN · ROADMAP）

| 模块 | 入口 |
|------|------|
| game_runtime | [README](./game_runtime/README.md) · [DESIGN](./game_runtime/DESIGN.md) · [ROADMAP](./game_runtime/ROADMAP.md) |
| agent_team | [README](./agent_team/README.md) · [DESIGN](./agent_team/DESIGN.md) · [ROADMAP](./agent_team/ROADMAP.md) · [memory](./agent_team/memory/) |
| strategy | [README](./strategy/README.md) · [DESIGN](./strategy/DESIGN.md) · [ROADMAP](./strategy/ROADMAP.md) |
| evaluation | [README](./evaluation/README.md) · [DESIGN](./evaluation/DESIGN.md) · [ROADMAP](./evaluation/ROADMAP.md) |
| interface | [README](./interface/README.md) · [DESIGN](./interface/DESIGN.md) · [ROADMAP](./interface/ROADMAP.md) |
| observability | [README](./observability/README.md) · [DESIGN](./observability/DESIGN.md) · [ROADMAP](./observability/ROADMAP.md) |
| ui | [README](./ui/README.md) · [DESIGN](./ui/DESIGN.md) · [ROADMAP](./ui/ROADMAP.md) |
| frontend | [README](./frontend/README.md) · [DESIGN](./frontend/DESIGN.md) · [ROADMAP](./frontend/ROADMAP.md) |
| architecture | [Evaluation 历史专题](./architecture/evaluation/) · [Memory 历史专题](./architecture/memory/) · [提示词与 Skill 版本控制](./architecture/吕祎晗-提示词版本与变量设计.md) · [工程结构整理方案](./architecture/工程结构整理方案.md) · [信念矩阵功能设计](./architecture/信念矩阵功能设计.md) |

## 其他目录

| 目录 | 用途 |
|------|------|
| `architecture/` | 跨模块方案；evaluation / memory 历史专题见 `architecture/evaluation/`、`architecture/memory/` |
| `agent_team/memory/` | 记忆子模块三件套（README · DESIGN · ROADMAP） |
| `evaluation/` | **仅** README · DESIGN · ROADMAP 三件套 |
| `reports/` | 专项报告、排查过程稿 |
| `archive/` | 已归档文档 |

## 写作规范

- 统一模板：[DOC_TEMPLATE.md](./DOC_TEMPLATE.md)
- 新结论写入模块 `DESIGN.md`，进度写入 `ROADMAP.md`
- 子模块文档：`evaluation/`、`agent_team/memory/` 各仅保留三件套；历史专题见 `architecture/evaluation/`、`architecture/memory/`
- 根目录 [前端规划.md](./archive/前端规划.md)：Web 14 页与 API 对接（frontend 模块）

## 运维与验证

| 脚本 | 用途 |
|------|------|
| `scripts/test_ark_connectivity.py` | 校验 `.env` 中 `ARK_API_KEY` + `ARK_EP` 是否可用（Doubao） |
| `uv run werewolf configs/llm-12p-doubao.yaml` | 12 人标准 LLM 对局（CLI） |
| `uv run werewolf-api` | Web API（前端对接目标，`:8000`） |
| `uv run werewolf-watch --since 24h` | 扫描 run 产物并生成/推送告警 |
