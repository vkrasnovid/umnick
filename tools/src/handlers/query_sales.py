from __future__ import annotations

from uuid import UUID
from datetime import date, timedelta

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import QuerySalesParams, ToolResponse


async def handle_query_sales(
    params: QuerySalesParams,
    tenant_id: str,
    session: AsyncSession,
) -> ToolResponse:
    """Анализ продаж за период."""
    try:
        tid = UUID(tenant_id)
    except ValueError:
        return ToolResponse(success=False, error="Invalid tenant_id")

    period_start = date.today() - timedelta(days=params.period_days)

    # Сводка
    summary_result = await session.execute(
        sa_text("""
            SELECT
                COALESCE(SUM(amount), 0) AS total_revenue,
                COUNT(*) AS total_orders,
                CASE WHEN COUNT(*) > 0 THEN SUM(amount) / COUNT(*) ELSE 0 END AS avg_order_value
            FROM umnick.orders
            WHERE tenant_id = :tenant_id
              AND date >= :period_start
              AND status NOT IN ('cancelled', 'draft')
              AND (:counterparty_id IS NULL OR counterparty_id = :counterparty_id::uuid)
        """),
        {
            "tenant_id": tid,
            "period_start": period_start,
            "counterparty_id": params.counterparty_id,
        },
    )
    summary_row = summary_result.mappings().first()

    # По контрагентам
    by_cp_result = await session.execute(
        sa_text("""
            SELECT
                cp.name,
                COALESCE(SUM(o.amount), 0) AS revenue,
                COUNT(*) AS orders_count
            FROM umnick.orders o
            JOIN umnick.counterparties cp ON cp.id = o.counterparty_id AND cp.tenant_id = :tenant_id
            WHERE o.tenant_id = :tenant_id
              AND o.date >= :period_start
              AND o.status NOT IN ('cancelled', 'draft')
              AND (:counterparty_id IS NULL OR o.counterparty_id = :counterparty_id::uuid)
            GROUP BY cp.name
            ORDER BY revenue DESC
            LIMIT 20
        """),
        {
            "tenant_id": tid,
            "period_start": period_start,
            "counterparty_id": params.counterparty_id,
        },
    )
    by_counterparty = [
        {
            "name": row["name"],
            "revenue": float(row["revenue"]),
            "orders_count": row["orders_count"],
        }
        for row in by_cp_result.mappings().all()
    ]

    # Данные для графика
    chart_data = []
    if params.include_chart_data:
        # Выбираем по дням
        chart_result = await session.execute(
            sa_text("""
                SELECT date, SUM(amount) AS revenue, COUNT(*) AS orders
                FROM umnick.orders
                WHERE tenant_id = :tenant_id
                  AND date >= :period_start
                  AND status NOT IN ('cancelled', 'draft')
                  AND (:counterparty_id IS NULL OR counterparty_id = :counterparty_id::uuid)
                GROUP BY date
                ORDER BY date
            """),
            {
                "tenant_id": tid,
                "period_start": period_start,
                "counterparty_id": params.counterparty_id,
            },
        )
        chart_data = [
            {
                "period": str(row["date"]),
                "revenue": float(row["revenue"]),
                "orders": row["orders"],
            }
            for row in chart_result.mappings().all()
        ]

    return ToolResponse(data={
        "summary": {
            "total_revenue": float(summary_row["total_revenue"]) if summary_row else 0,
            "total_orders": summary_row["total_orders"] if summary_row else 0,
            "avg_order_value": float(summary_row["avg_order_value"]) if summary_row else 0,
            "currency": "RUB",
        },
        "by_counterparty": by_counterparty,
        "chart_data": chart_data,
    })
