# Observability 路线图

> **模块**：observability
> **状态**：active
> **最后更新**：2026-06-02
> **关联代码**：`src/llm_werewolf/observability/`

---

## Phase 1 — 可发现 + 可通知（MVP） ✅

- [x] `observability/` 脚手架 + 架构边界测试
- [x] `evaluation/signals/`（`scan_run_dir`、`load_post_game_signals`）
- [x] `RunArtifactCollector` + 8 项规则 + 去重 `AlertDispatcher`
- [x] `WebhookNotifier`（`OBS_ALERT_WEBHOOK_URL`）
- [x] `werewolf-watch` CLI
- [x] `finalize_run` / `game_sessions` hook + `run_meta.post_game_status`
- [x] `GET /ready`
- [x] 文档三件套 + `configs/observability.yaml`

## Phase 2 — 质量门禁 + 指标

- [x] 运行时 429 / structured_invoke 日志采集（`provider_events.jsonl`）
- [ ] 在线 checker 子集 → `run_quality.json`
- [ ] 可选 `GET /metrics`（JSON / Prometheus text）
- [ ] CI：`werewolf-watch --since 24h --fail-on-critical`
- [ ] `FeishuNotifier`

## Phase 3 — 生产级（按需）

- [ ] Logfire / OpenTelemetry 导出
- [ ] Sentry 未捕获异常
- [ ] Grafana 仪表盘
- [ ] 429 熔断与队列
