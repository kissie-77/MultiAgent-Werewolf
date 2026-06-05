"""Webhook notifier E2E 测试：验证 HTTP payload 端到端可达。"""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

import pytest

from llm_werewolf.observability.core.config import ObservabilityConfig
from llm_werewolf.observability.core.dispatcher import AlertDispatcher
from llm_werewolf.observability.core.models import AlertEvent, AlertSeverity
from llm_werewolf.observability.notifiers.webhook import WebhookNotifier


# ── 轻量级 mock HTTP 服务器 ────────────────────────────────────────────────

class _CaptureHandler(BaseHTTPRequestHandler):
    """记录所有 POST 请求到类变量。"""

    received: ClassVar[list[dict]] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            _CaptureHandler.received.append(json.loads(body.decode("utf-8")))
        except json.JSONDecodeError:
            _CaptureHandler.received.append({"_raw": body.decode("utf-8", errors="replace")})
        self.send_response(200)
        self.end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        """关闭默认日志输出，避免测试噪声。"""


class _MockWebhookServer:
    """可通过 with 语句使用的 mock HTTP server，在独立线程运行。"""

    def __init__(self) -> None:
        _CaptureHandler.received = []
        self._server = HTTPServer(("127.0.0.1", 0), _CaptureHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    @property
    def received(self) -> list[dict]:
        return _CaptureHandler.received

    def __enter__(self) -> _MockWebhookServer:
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._server.shutdown()


# ── 测试 ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_notifier_delivers_payload() -> None:
    """WebhookNotifier 应将 AlertEvent 以正确的 JSON schema 投递到 HTTP 端点。"""
    with _MockWebhookServer() as server:
        notifier = WebhookNotifier(server.url, timeout_seconds=5.0)
        event = AlertEvent(
            run_id="run-e2e-001",
            source="test",
            severity=AlertSeverity.WARNING,
            code="test_alert",
            message="E2E 测试告警",
        )

        await notifier.notify([event])

        # 等待 mock server 处理（通常 <1ms，留 100ms 余量）
        await asyncio.sleep(0.1)

    assert len(server.received) == 1, "应收到 1 次 HTTP POST"
    payload = server.received[0]
    assert payload["schema"] == "werewolf_alert_batch_v1"
    assert payload["count"] == 1
    assert payload["alerts"][0]["code"] == "test_alert"
    assert payload["alerts"][0]["run_id"] == "run-e2e-001"


@pytest.mark.asyncio
async def test_webhook_notifier_skips_empty_events() -> None:
    """空事件列表不应触发 HTTP 请求。"""
    with _MockWebhookServer() as server:
        notifier = WebhookNotifier(server.url, timeout_seconds=5.0)
        await notifier.notify([])
        await asyncio.sleep(0.05)

    assert len(server.received) == 0, "空事件不应产生 HTTP 请求"


@pytest.mark.asyncio
async def test_webhook_notifier_handles_server_error_gracefully() -> None:
    """Webhook 目标返回 5xx 时应记录警告，不抛出异常。"""

    class _ErrorHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            self.send_response(500)
            self.end_headers()

        def log_message(self, fmt: str, *args: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), _ErrorHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}"

    notifier = WebhookNotifier(url, timeout_seconds=5.0)
    event = AlertEvent(
        run_id="run-x",
        source="test",
        severity=AlertSeverity.ERROR,
        code="test_500",
        message="服务器错误",
    )

    # 不应抛出异常
    await notifier.notify([event])
    server.shutdown()


@pytest.mark.asyncio
async def test_dispatcher_full_chain_delivers_to_webhook(tmp_path) -> None:
    """完整链路：AlertDispatcher → WebhookNotifier → mock HTTP server。"""
    with _MockWebhookServer() as server:
        config = ObservabilityConfig.from_env(alerts_dir=tmp_path / "alerts")
        notifier = WebhookNotifier(server.url, timeout_seconds=5.0)
        dispatcher = AlertDispatcher(config, notifiers=[notifier])

        event = AlertEvent(
            run_id="run-chain-001",
            source="session",
            severity=AlertSeverity.ERROR,
            code="run_failed",
            message="对局异常终止",
        )

        accepted = await dispatcher.emit([event], run_dir=tmp_path / "run-chain-001")
        await asyncio.sleep(0.1)

    assert len(accepted) == 1
    assert len(server.received) == 1
    payload = server.received[0]
    assert payload["alerts"][0]["code"] == "run_failed"
    assert payload["alerts"][0]["severity"] == "error"
