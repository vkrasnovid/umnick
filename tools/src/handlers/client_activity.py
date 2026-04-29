from __future__ import annotations

from uuid import UUID
from datetime import date, timedelta

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import ClientActivityParams, ToolResponse


async def handle_client_activity(
    params: ClientActivityParams,
    tenant_id: str,
    session: AsyncSession,
) -> ToolResponse:
    """Получить активность клиента за период."""
    try:
        tid = UUID(tenant_id)
    except ValueError:
        return ToolResponse(success=False, error="Invalid tenant_id")

    period_start = date.today() - timedelta(days=params.period_days)

    # Получаем контрагента
    cp_result = await session.execute(
        sa_text("""
            SELECT id, name, inn, status
            FROM umnick.counterparties
            WHERE tenant_id = :tenant_id
              AND (CAST(:counterparty_id AS uuid) IS NULL OR id = CAST(:counterparty_id AS uuid))
              AND (CAST(:inn AS text) IS NULL OR inn = CAST(:inn AS text))
            LIMIT 1
        """),
        {
            "tenant_id": tid,
            "counterparty_id": params.counterparty_id,
            "inn": params.inn,
        },
    )
    cp = cp_result.mappings().first()
    if not cp:
        return ToolResponse(success=False, error="Контрагент не найден")

    cp_id = cp["id"]

    # Сводка активности
    summary_result = await session.execute(
        sa_text("""
            SELECT
                (SELECT COUNT(*) FROM umnick.orders
                 WHERE tenant_id = :tenant_id
                   AND counterparty_id = :cp_id
                   AND date >= :period_start) AS total_orders,
                (SELECT COUNT(*) FROM umnick.invoices
                 WHERE tenant_id = :tenant_id
                   AND counterparty_id = :cp_id
                   AND date >= :period_start) AS total_invoices,
                (SELECT COALESCE(SUM(amount), 0) FROM umnick.payments
                 WHERE tenant_id = :tenant_id
                   AND counterparty_id = :cp_id
                   AND date >= :period_start
                   AND direction = 'incoming') AS total_payments_in,
                (SELECT COALESCE(SUM(amount), 0) FROM umnick.payments
                 WHERE tenant_id = :tenant_id
                   AND counterparty_id = :cp_id
                   AND date >= :period_start
                   AND direction = 'outgoing') AS total_payments_out
        """),
        {
            "tenant_id": tid,
            "cp_id": cp_id,
            "period_start": period_start,
        },
    )
    summary_row = summary_result.mappings().first()

    activity_data = {
        "counterparty": {
            "id": str(cp["id"]),
            "name": cp["name"],
            "inn": cp.get("inn"),
            "status": cp["status"],
        },
        "period": {
            "from": period_start.isoformat(),
            "to": date.today().isoformat(),
        },
        "activity_summary": {
            "total_orders": summary_row["total_orders"] if summary_row else 0,
            "total_invoices": summary_row["total_invoices"] if summary_row else 0,
            "total_payments_in": float(summary_row["total_payments_in"]) if summary_row else 0,
            "total_payments_out": float(summary_row["total_payments_out"]) if summary_row else 0,
        },
    }

    # Заказы
    if params.include_orders:
        orders_result = await session.execute(
            sa_text("""
                SELECT number, date, amount, status
                FROM umnick.orders
                WHERE tenant_id = :tenant_id
                  AND counterparty_id = :cp_id
                  AND date >= :period_start
                ORDER BY date DESC
                LIMIT 20
            """),
            {"tenant_id": tid, "cp_id": cp_id, "period_start": period_start},
        )
        activity_data["orders"] = [
            dict(row) for row in orders_result.mappings().all()
        ]

    # Счета
    if params.include_invoices:
        invoices_result = await session.execute(
            sa_text("""
                SELECT number, date, due_date, amount, balance, status
                FROM umnick.invoices
                WHERE tenant_id = :tenant_id
                  AND counterparty_id = :cp_id
                  AND date >= :period_start
                ORDER BY date DESC
                LIMIT 20
            """),
            {"tenant_id": tid, "cp_id": cp_id, "period_start": period_start},
        )
        activity_data["invoices"] = [
            dict(row) for row in invoices_result.mappings().all()
        ]

    # Платежи
    if params.include_payments:
        payments_result = await session.execute(
            sa_text("""
                SELECT number, date, amount, direction, payment_type
                FROM umnick.payments
                WHERE tenant_id = :tenant_id
                  AND counterparty_id = :cp_id
                  AND date >= :period_start
                ORDER BY date DESC
                LIMIT 20
            """),
            {"tenant_id": tid, "cp_id": cp_id, "period_start": period_start},
        )
        activity_data["payments"] = [
            dict(row) for row in payments_result.mappings().all()
        ]

    return ToolResponse(data=activity_data)
