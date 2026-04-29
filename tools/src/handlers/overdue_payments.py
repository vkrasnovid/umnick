from __future__ import annotations

from uuid import UUID
from datetime import date

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import OverduePaymentsParams, ToolResponse


async def handle_overdue_payments(
    params: OverduePaymentsParams,
    tenant_id: str,
    session: AsyncSession,
) -> ToolResponse:
    """Получить список просроченных платежей."""
    try:
        tid = UUID(tenant_id)
    except ValueError:
        return ToolResponse(success=False, error="Invalid tenant_id")

    today = date.today()

    result = await session.execute(
        sa_text("""
            SELECT i.id, i.number, i.date, i.due_date, i.amount, i.balance,
                   i.paid_amount, i.status,
                   cp.name AS counterparty_name, cp.id AS counterparty_id,
                   (CURRENT_DATE - i.due_date) AS days_overdue
            FROM umnick.invoices i
            JOIN umnick.counterparties cp ON cp.id = i.counterparty_id AND cp.tenant_id = :tenant_id
            WHERE i.tenant_id = :tenant_id
              AND i.status IN ('unpaid', 'partial')
              AND i.due_date < CURRENT_DATE - CAST(:days_overdue_min AS integer)
              AND (CAST(:counterparty_id AS uuid) IS NULL OR i.counterparty_id = CAST(:counterparty_id AS uuid))
              AND (CAST(:threshold_amount AS numeric) IS NULL OR i.balance >= CAST(:threshold_amount AS numeric))
            ORDER BY i.due_date ASC
            LIMIT :limit
        """),
        {
            "tenant_id": tid,
            "days_overdue_min": params.days_overdue_min,
            "counterparty_id": params.counterparty_id,
            "threshold_amount": params.threshold_amount,
            "limit": params.limit,
        },
    )
    rows = result.mappings().all()

    overdue_invoices = []
    total_overdue_sum = 0.0

    for row in rows:
        balance = float(row["balance"] or 0)
        total_overdue_sum += balance
        overdue_invoices.append({
            "invoice_number": row["number"],
            "counterparty": row["counterparty_name"],
            "amount": float(row["amount"]),
            "balance": balance,
            "due_date": str(row["due_date"]) if row["due_date"] else None,
            "days_overdue": row["days_overdue"] or 0,
        })

    return ToolResponse(data={
        "summary": {
            "total_overdue_count": len(overdue_invoices),
            "total_overdue_sum": total_overdue_sum,
            "currency": "RUB",
        },
        "overdue_invoices": overdue_invoices,
    })
