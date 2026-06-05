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
| `reports/` | 专项报告、排查过程稿；工程质量本轮记录见 [修复记录](./reports/工程代码质量修复记录-2026-06-04.md) 与 [总体计划](./reports/工程代码质量修复总体计划.md) |
| `archive/` | 已归档文档 |
| 仓库根目录 | [项目评分报告.md](../项目评分报告.md)（模块评分、问题核实与修复状态，2026-06-05） |

## 写作规范

- 统一模板：[DOC_TEMPLATE.md](./DOC_TEMPLATE.md)
- 新结论写入模块 `DESIGN.md`，进度写入 `ROADMAP.md`
- 子模块文档：`evaluation/`、`agent_team/memory/` 各仅保留三件套；历史专题见 `architecture/evaluation/`、`architecture/memory/`
- **后端文档范围**：`game_runtime`、`agent_team`、`strategy`、`evaluation`、`interface`、`observability` 及 `architecture/` 下非 UI 专题
- **前端文档**：`frontend/` 三件套与 API 健壮性（retry、局中状态保留）见 [frontend/README.md](./frontend/README.md)
- 工程质量与修复脉络见 [reports/工程代码质量修复记录-2026-06-04.md](./reports/工程代码质量修复记录-2026-06-04.md) §三（2026-06-02）与 §六（2026-06-05 评分报告批次）
- 赛后 LLM 提示词外置：`src/llm_werewolf/evaluation/prompts/`（`replay/v1`、`coach/v1`），加载器见 `evaluation/registry/post_game_prompt_registry.py`

## 运维与验证

| 脚本 / CLI | 用途 |
|------|------|
| `uv run werewolf` | 交互式正式对局入口 |
| `uv run werewolf --participation human_mixed --rules extended_roles --players 18 --human_seat 8` | 18 人人机扩展局示例 |
| `uv run werewolf configs/llm-12p-kimi.yaml` | 12 人 Kimi/VibeAPI LLM 对局（CLI） |
| `scripts/test_ark_connectivity.py` | 校验 `.env` 中 `ARK_API_KEY` + `ARK_EP` 是否可用（Doubao/ARK 专用） |
| `uv run werewolf-api` | Web API（前端对接目标，`:8000`）；`GET /health`、`GET /ready` |
| `uv run werewolf-watch --since 24h` | 扫描 run 产物并生成告警摘要（默认不 push Webhook） |

告警与监控设计见 [observability/README.md](./observability/README.md)。
