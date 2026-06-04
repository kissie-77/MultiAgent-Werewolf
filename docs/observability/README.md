# Observability 模块

> **模块**：observability
> **状态**：active
> **最后更新**：2026-06-02
> **关联代码**：`src/llm_werewolf/observability/`
> **关联测试**：`tests/observability/`、`tests/evaluation/signals/`

---

## 是什么

第七板块 **运维可观测层**：从 run 产物、evaluation 质量信号与运行时日志生成告警，经去重分发后写入审计文件，可选 Webhook。

| 板块 | 分工 |
|------|------|
| `evaluation` | 赛后质量审计（checkers、PostGame） |
| `observability` | 发现异常 + 告警 + 批量巡检 |
| `interface` | 挂载 hook（对局结束、API 会话、CLI、watch） |

**适用场景**：比赛/离线跑局后的产物巡检；**不依赖** Prometheus、飞书、Sentry 等线上设施。

## 监控什么（9 项规则）

| 类别 | 规则 code | 简要说明 |
|------|-----------|----------|
| 对局 | `run_failed` | `run_meta.status=failed` |
| PostGame | `post_game_failed` | 流水线/步骤失败 |
| 事件 | `error_events_per_run` | `events.jsonl` ERROR 过多 |
| 质量 | `checker_critical` | 信息泄漏等 CRITICAL |
| PostGame | `llm_replay_failed` | LLM 复盘 mode=failed |
| 事件 | `vote_timeout_per_run` | 投票超时 ERROR 过多 |
| 决策 | `structured_invoke_gave_up` | 结构化调用放弃 |
| LLM | `provider_429_burst` | 429 / 限流 |
| Agent | `agent_fallback_per_run` | 发言/投票/记忆等 fallback 降级 |

运行时 LLM/fallback 信号写入 `<run_dir>/provider_events.jsonl`（见 [DESIGN.md](./DESIGN.md)）。

## 快速开始

```bash
# 批量扫盘（默认不写 Webhook，只生成 artifacts/alerts/alerts.json）
uv run werewolf-watch --since 24h

# 需要推送时再开
export OBS_ALERT_WEBHOOK_URL=https://example.com/hook
uv run werewolf-watch --since 24h --push=True

# API 就绪探测（本地）
curl http://127.0.0.1:8000/ready
```

## 单场 run 关键产物

| 文件 | 内容 |
|------|------|
| `run_meta.json` | `post_game_status`、`alert_count` |
| `provider_events.jsonl` | 429 / structured_invoke / fallback 日志事件 |
| `alert_report.json` | 本场触发的告警列表 |
| `artifacts/alerts/alerts.jsonl` | 全局告警审计 |

## 文档

| 文档 | 内容 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 架构、规则、挂载点、配置 |
| [ROADMAP.md](./ROADMAP.md) | Phase 1–3 进度 |

## 相关

- 基线评估：[监控预警现状与不足分析](../reports/监控预警现状与不足分析.md)
- 配置：`configs/observability.yaml`、环境变量 `OBS_ALERT_*`
- 信号层：`evaluation/signals/`（`scan_run_dir`、`load_post_game_signals`）
