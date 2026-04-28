from __future__ import annotations

"""
Celery задачи для Proactive Engine:
- check_due_watchers — проверка watchers по расписанию
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from celery_app import celery_app
from logging_setup import get_logger, setup_logging
from watcher import compute_alert_hash, should_send_alert, render_message

setup_logging("umnick-engine")
logger = get_logger(__name__)

# Use sync SQLAlchemy for Celery tasks (Celery is sync)
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sync_engine = create_engine(
    settings.database_url_sync,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)
SyncSession = sessionmaker(bind=sync_engine)


def _execute_tool(tool_name: str, tool_params: dict, tenant_id: str) -> dict:
    """Выполнить tool через прямой SQL-запрос (имитация вызова Tool Runtime).

    В реальной системе здесь был бы HTTP-вызов к Tool Runtime сервису.
    Для MVP — прямой SQL.
    """
    # Маппинг tool → handler
    handlers = {
        "get_overdue_payments": _query_overdue_payments,
        "query_sales": _query_sales,
        "get_client_activity": _query_client_activity,
        "list_active_clients": _query_active_clients,
    }

    handler = handlers.get(tool_name)
    if not handler:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

    try:
        return handler(tool_params, tenant_id)
    except Exception as e:
        logger.error("Tool execution error", tool=tool_name, error=str(e))
        return {"success": False, "error": str(e)}


def _query_overdue_payments(params: dict, tenant_id: str) -> dict:
    """Проверка просроченных платежей (для watcher)."""
    session = SyncSession()
    try:
        tid = uuid.UUID(tenant_id)
        days_overdue_min = params.get("days_overdue_min", 1)
        limit = params.get("limit", 50)
        threshold = params.get("threshold_amount")

        result = session.execute(
            text("""
                SELECT COUNT(*) AS total, COALESCE(SUM(balance), 0) AS total_sum
                FROM umnick.invoices
                WHERE tenant_id = :tid
                  AND status IN ('unpaid', 'partial')
                  AND due_date < CURRENT_DATE - :days::integer
                  AND (:threshold IS NULL OR balance >= :threshold::numeric)
            """),
            {"tid": tid, "days": days_overdue_min, "threshold": threshold},
        )
        row = result.fetchone()

        return {
            "success": True,
            "data": {
                "summary": {
                    "total_overdue_count": row[0] or 0,
                    "total_overdue_sum": float(row[1] or 0),
                    "currency": "RUB",
                }
            },
        }
    finally:
        session.close()


def _query_sales(params: dict, tenant_id: str) -> dict:
    """Запрос продаж (для watcher revenue drop)."""
    session = SyncSession()
    try:
        tid = uuid.UUID(tenant_id)
        period_days = params.get("period_days", 14)

        result = session.execute(
            text("""
                SELECT
                    date_trunc('week', date) AS week_start,
                    SUM(amount) AS revenue,
                    COUNT(*) AS orders
                FROM umnick.orders
                WHERE tenant_id = :tid
                  AND date >= CURRENT_DATE - :days::integer
                  AND status NOT IN ('cancelled', 'draft')
                GROUP BY date_trunc('week', date)
                ORDER BY week_start DESC
                LIMIT 2
            """),
            {"tid": tid, "days": period_days},
        )
        rows = result.fetchall()

        chart_data = [
            {"period": str(r[0]), "revenue": float(r[1] or 0), "orders": r[2] or 0}
            for r in rows
        ]

        return {
            "success": True,
            "data": {
                "chart_data": chart_data,
            },
        }
    finally:
        session.close()


def _query_client_activity(params: dict, tenant_id: str) -> dict:
    """Запрос активности клиента."""
    session = SyncSession()
    try:
        tid = uuid.UUID(tenant_id)
        return {"success": True, "data": {"activity": []}}
    finally:
        session.close()


def _query_active_clients(params: dict, tenant_id: str) -> dict:
    """Запрос активных клиентов."""
    session = SyncSession()
    try:
        tid = uuid.UUID(tenant_id)
        return {"success": True, "data": {"clients": []}}
    finally:
        session.close()


def _evaluate_condition(condition: str, tool_response: dict) -> bool:
    """Оценка условия watcher'a на основе ответа tool.

    Преобразует dot-нотацию (data.key.subkey) в доступ к словарю
    и безопасно eval'ит выражение.
    """
    try:
        data = tool_response.get("data", {})
        result = _safe_eval(condition, {"data": data})
        return bool(result)
    except Exception as e:
        logger.error("Condition evaluation error", condition=condition, error=str(e))
        return False


def _safe_eval(expr: str, context: dict) -> Any:
    """Безопасная эвалюация выражения с поддержкой dot-нотации.

    data.key.subkey → data["key"]["subkey"]
    Поддерживает: >, <, >=, <=, ==, !=, and, or, not, len(), int, float
    """
    import re

    # Заменяем Jinja2-подобные конструкции
    expr = expr.replace(" is defined", "").replace(" | length", "_length_")

    # Преобразуем dot-нотацию: data.key.subkey → data["key"]["subkey"]
    # Ищем последовательности: буква.буква.буква или data.буква.буква
    def _replace_dot_access(match):
        full_match = match.group(0)
        parts = full_match.split(".")
        # First part is the variable name (e.g., "data")
        result = parts[0]
        for p in parts[1:]:
            # Clean the part from trailing operators or brackets
            clean = re.sub(r'[>\s<>=!&|()\[\]]', '', p).strip()
            if clean:
                result += f'["{clean}"]'
            else:
                result += "." + p
        return result

    # Match patterns like data.something or data.a.b (word.word or word.word.word)
    # But NOT len(data) or similar function calls
    converted = re.sub(r'(?<![a-zA-Z_])[a-zA-Z_]+\.\w+(\.\w+)*', _replace_dot_access, expr)

    allowed_names = {
        "__builtins__": {},
        "True": True,
        "False": False,
        "None": None,
        "len": len,
        "int": int,
        "float": float,
        "min": min,
        "max": max,
        "any": any,
        "all": all,
    }

    local_vars = dict(context)
    for key, value in context.items():
        local_vars[key] = value

    try:
        return eval(converted, allowed_names, local_vars)
    except Exception:
        # Fallback: iterate the context dict directly
        if "data" in context:
            d = context["data"]
            for key in expr.split(".")[1:]:
                clean = re.sub(r'[^\w]', '', key)
                if isinstance(d, dict):
                    d = d.get(clean, 0)
                else:
                    d = 0
            # Now d should be the final value, check if > 0
            if isinstance(d, (int, float)):
                # Check if the original expression contained a comparison
                for op in [" > 0", " >= 1", " > 0", "!= 0"]:
                    if op in expr:
                        return d > 0
                return bool(d)
            elif isinstance(d, bool):
                return d
        return False


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def check_due_watchers(self):
    """Проверить, какие watchers нужно запустить по расписанию."""
    from croniter import croniter
    from datetime import datetime as dt

    now = dt.now(timezone.utc)
    checked = 0
    triggered = 0
    alerts_sent = 0

    session = SyncSession()
    try:
        # Выбираем все включённые watchers, не в snooze
        result = session.execute(
            text("""
                SELECT id, tenant_id, name, schedule, tool_name, tool_params,
                       condition, message_template, recipients, priority,
                       last_run_at, last_alert_hash, snooze_until
                FROM umnick.watchers
                WHERE enabled = TRUE
                  AND (snooze_until IS NULL OR snooze_until < :now::timestamptz)
            """),
            {"now": now},
        )
        watchers = result.fetchall()

        for w in watchers:
            checked += 1
            watcher_id = w[0]
            tenant_id = w[1]
            watcher_name = w[2]
            schedule = w[3]
            tool_name = w[4]
            tool_params = w[5] or {}
            condition = w[6]
            message_template = w[7]
            recipients = w[8] or []
            last_run_at = w[10]
            last_alert_hash = w[11]
            snooze_until = w[12]

            # Проверяем расписание
            try:
                if last_run_at:
                    base = last_run_at.replace(tzinfo=timezone.utc)
                else:
                    base = now
                cron = croniter(schedule, base)
                next_run = cron.get_next(dt)
                if next_run > now:
                    continue
            except (ValueError, KeyError) as e:
                logger.warning("Invalid cron for watcher", name=watcher_name, error=str(e))
                continue

            triggered += 1

            # Выполняем tool
            tool_response = _execute_tool(tool_name, tool_params, str(tenant_id))
            if not tool_response.get("success"):
                logger.warning("Tool failed for watcher", name=watcher_name,
                               error=tool_response.get("error"))
                continue

            # Оцениваем условие
            condition_met = _evaluate_condition(condition, tool_response)
            if not condition_met:
                logger.debug("Condition not met for watcher", name=watcher_name)
                # Обновляем last_run_at
                session.execute(
                    text("UPDATE umnick.watchers SET last_run_at = :now WHERE id = :id"),
                    {"now": now, "id": watcher_id},
                )
                session.commit()
                continue

            # Дедупликация
            alert_hash = compute_alert_hash(tool_name, tool_params, tool_response)
            if not should_send_alert(tool_response, alert_hash, last_alert_hash, snooze_until):
                continue

            # Рендерим сообщение
            message = render_message(message_template, tool_response.get("data", {}))

            # Отправляем алерт (в MVP — логируем)
            logger.info(
                "ALERT triggered",
                watcher=watcher_name,
                tenant_id=str(tenant_id),
                recipients=recipients,
                message_preview=message[:200],
            )

            # Обновляем watcher в БД
            session.execute(
                text("""
                    UPDATE umnick.watchers
                    SET last_run_at = :now, last_alert_hash = :hash_val,
                        last_alert_at = :now, alert_count = alert_count + 1
                    WHERE id = :id
                """),
                {"now": now, "hash_val": alert_hash, "id": watcher_id},
            )
            session.commit()
            alerts_sent += 1

    except Exception as e:
        logger.error("Watcher check error", error=str(e))
        session.rollback()
    finally:
        session.close()

    logger.info(
        "Watcher check completed",
        checked=checked,
        triggered=triggered,
        alerts_sent=alerts_sent,
    )
    return {"checked": checked, "triggered": triggered, "alerts_sent": alerts_sent}
