"""通用 JSON Webhook 通知器。"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib import error, request

from llm_werewolf.observability.models import AlertEvent
from llm_werewolf.observability.notifiers.base import AlertNotifier

logger = logging.getLogger(__name__)


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
        req = request.Request(
            self._url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status >= 400:
                    logger.warning("Webhook returned HTTP %s", resp.status)
        except error.URLError as exc:
            logger.warning("Webhook notify failed: %s", exc)
