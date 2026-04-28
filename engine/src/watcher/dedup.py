from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


def compute_alert_hash(watcher_tool_name: str, tool_params: dict, tool_response: dict) -> str:
    """Вычислить SHA256 хэш тела алерта для дедупликации."""
    content = {
        "tool": watcher_tool_name,
        "params": tool_params,
        "summary": tool_response.get("data", {}).get("summary", {}),
    }
    return hashlib.sha256(
        json.dumps(content, sort_keys=True).encode()
    ).hexdigest()


def should_send_alert(
    tool_response: dict,
    current_hash: str,
    last_alert_hash: str | None,
    snooze_until: datetime | None,
) -> bool:
    """
    Определить, нужно ли отправлять алерт.

    Returns True если:
    1. Хэш алерта отличается от предыдущего (нет дедупликации)
    2. Не в режиме snooze
    """
    # Дедупликация
    if last_alert_hash and last_alert_hash == current_hash:
        logger.debug("Alert deduplicated — hash matches last alert")
        return False

    # Проверка snooze
    if snooze_until and snooze_until > datetime.now(timezone.utc):
        logger.debug("Alert skipped — watcher is snoozed until %s", snooze_until)
        return False

    return True
