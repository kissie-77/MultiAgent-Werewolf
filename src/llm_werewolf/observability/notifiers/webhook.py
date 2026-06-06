"""通用 JSON Webhook 通知器。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from urllib import error, request
import asyncio
import logging

from llm_werewolf.observability.notifiers.base import AlertNotifier

if TYPE_CHECKING:
    from llm_werewolf.observability.core.models import AlertEvent

logger = logging.getLogger(__name__)


def _post_sync(url: str, body: bytes, timeout: float) -> int:
    """在线程池中执行的同步 HTTP POST，返回状态码。"""
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        return int(resp.status)


class WebhookNotifier(AlertNotifier):
    def __init__(self, url: str, *, timeout_seconds: float = 10.0) -> None:
        self._url = url
        self._timeout = timeout_seconds

    async def notify(self, events: list[AlertEvent]) -> None:
        if not events:
            return
        payload: dict[str, Any] = {
            "schema": "werewolf_alert_batch_v1",
            "count": len(events),
            "alerts": [event.model_dump(mode="json") for event in events],
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            status = await asyncio.to_thread(_post_sync, self._url, body, self._timeout)
            if status >= 400:
                logger.warning("Webhook returned HTTP %s", status)
        except error.URLError as exc:
            logger.warning("Webhook notify failed: %s", exc)
        except Exception as exc:
            logger.warning("Webhook unexpected error: %s", exc)
