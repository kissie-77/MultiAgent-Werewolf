# Observability 模块

> **模块**：observability
> **状态**：active
> **最后更新**：2026-06-02
> **关联代码**：`src/llm_werewolf/observability/`
> **关联测试**：`tests/observability/`

---

## 是什么

第七板块 **运维可观测层**：从 run 产物与 evaluation 质量信号生成告警，经去重分发后写入审计文件并可选推送 Webhook。

与 `evaluation` 分离：`evaluation` 负责赛后质量审计；`observability` 负责**发现 + 通知**。

## 快速开始

```bash
# 扫描 artifacts 并写 alerts.json（可选 Webhook）
export OBS_ALERT_WEBHOOK_URL=https://example.com/hook   # 可选
uv run werewolf-watch --since 24h

# API 就绪探测
curl http://127.0.0.1:8000/ready
```

## 文档

| 文档 | 内容 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 架构、规则、挂载点 |
| [ROADMAP.md](./ROADMAP.md) | Phase 1–3 进度 |

## 相关

- 基线评估：[监控预警现状与不足分析](../reports/监控预警现状与不足分析.md)
- 配置示例：`configs/observability.yaml`
