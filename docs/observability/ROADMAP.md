# Observability 路线图

> **模块**：observability
> **状态**：active
> **最后更新**：2026-06-05
> **关联代码**：`src/llm_werewolf/observability/`

---

## Phase 1 — 可发现 + 可通知（MVP） ✅

- [x] `observability/` 脚手架 + 架构边界测试（第七板块）
- [x] `evaluation/signals/`（`scan_run_dir`、`load_post_game_signals`）
- [x] `RunArtifactCollector` + **9 项**规则 + 去重 `AlertDispatcher`
- [x] `WebhookNotifier`（`OBS_ALERT_WEBHOOK_URL`；YAML `${VAR}` 展开）
- [x] `werewolf-watch` CLI（默认 `--push=False`）
- [x] `finalize_run` / `game_sessions` hook + `run_meta.post_game_status`
- [x] `GET /ready`（artifacts 可写、可选 ARK key）
- [x] 运行时日志采集：`provider_events.jsonl`（429、structured_invoke、**agent fallback**）
- [x] CLI / API 对局挂载 `attach_run_log_handler`
- [x] 文档三件套 + `configs/observability.yaml`
- [x] `WebhookNotifier.notify` 改用 `asyncio.to_thread` 避免阻塞事件循环
- [x] Webhook E2E 测试（`tests/observability/test_webhook_notifier.py`）：payload 验证、空事件跳过、服务端 500 容错、Dispatcher 链路集成
- [x] 目录重组：根目录 5 个 `.py` 归入 `core/` 子包（config/dispatcher/health/models/runtime_log）

## Phase 2 — 质量门禁 + 指标

- [ ] 在线 checker 子集 → 每场 `run_quality.json`
- [ ] 可选 `GET /metrics`（JSON / Prometheus text）
- [ ] CI：`werewolf-watch --since 24h --fail-on-critical`
- [ ] `FeishuNotifier`
- [ ] `agent_team` 统一 fallback 打点（覆盖无 warning 的静默降级）

## Phase 3 — 生产级（按需，比赛项目可跳过）

- [ ] Logfire / OpenTelemetry 导出
- [ ] Sentry 未捕获异常
- [ ] Grafana 仪表盘
- [ ] 429 熔断与排队
