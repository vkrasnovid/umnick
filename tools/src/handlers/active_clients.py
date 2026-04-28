from __future__ import annotations

from uuid import UUID

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import ActiveClientsParams, ToolResponse


async def handle_active_clients(
    params: ActiveClientsParams,
    tenant_id: str,
    session: AsyncSession,
) -> ToolResponse:
    """Список активных клиентов с ключевыми метриками."""
    try:
        tid = UUID(tenant_id)
    except ValueError:
        return ToolResponse(success=False, error="Invalid tenant_id")

    result = await session.execute(
        sa_text("""
            WITH active_cp AS (
                SELECT id, name, inn, segment, status, phone, email,
                       is_client, is_buyer
                FROM umnick.counterparties
                WHERE tenant_id = :tenant_id
                  AND status = 'active'
                  AND (:segment IS NULL OR segment = :segment)
            ),
            cp_metrics AS (
                SELECT
                    ac.id,
                    ac.name,
                    ac.inn,
                    ac.segment,
                    ac.phone,
                    ac.email,
                    COALESCE(s30.sales_30d, 0) AS revenue_30d,
                    COALESCE(od.overdue_count, 0) AS overdue_count,
                    COALESCE(od.overdue_sum, 0) AS overdue_sum,
                    COALESCE(oc.order_count, 0) AS order_count_90d
                FROM active_cp ac
                LEFT JOIN (
                    SELECT counterparty_id,
                           COUNT(*) AS order_count
                    FROM umnick.orders
                    WHERE tenant_id = :tenant_id
                      AND date >= CURRENT_DATE - 90
                      AND status NOT IN ('cancelled', 'draft')
                    GROUP BY counterparty_id
                ) oc ON oc.counterparty_id = ac.id
                LEFT JOIN (
                    SELECT counterparty_id,
                           SUM(amount) AS sales_30d
                    FROM umnick.orders
                    WHERE tenant_id = :tenant_id
                      AND date >= CURRENT_DATE - 30
                      AND status NOT IN ('cancelled', 'draft')
                    GROUP BY counterparty_id
                ) s30 ON s30.counterparty_id = ac.id
                LEFT JOIN (
                    SELECT counterparty_id,
                           COUNT(*) AS overdue_count,
                           COALESCE(SUM(balance), 0) AS overdue_sum
                    FROM umnick.invoices
                    WHERE tenant_id = :tenant_id
                      AND status IN ('unpaid', 'partial')
                      AND due_date < CURRENT_DATE
                    GROUP BY counterparty_id
                ) od ON od.counterparty_id = ac.id
                WHERE (:has_overdue IS NULL
                       OR (:has_overdue = TRUE AND od.overdue_count > 0))
                  AND (:min_revenue_30d IS NULL
                       OR COALESCE(s30.sales_30d, 0) >= :min_revenue_30d::numeric)
            )
            SELECT *
            FROM cp_metrics
            ORDER BY
                CASE WHEN :sort_by = 'revenue' THEN revenue_30d END DESC,
                CASE WHEN :sort_by = 'name' THEN name END ASC,
                CASE WHEN :sort_by = 'overdue' THEN overdue_sum END DESC
            LIMIT :limit
        """),
        {
            "tenant_id": tid,
            "segment": params.segment,
            "has_overdue": params.has_overdue,
            "min_revenue_30d": params.min_revenue_30d,
            "limit": params.limit,
            "sort_by": params.sort_by,
        },
    )
    rows = result.mappings().all()

    clients = [
        {
            "id": str(row["id"]),
            "name": row["name"],
            "inn": row.get("inn"),
            "segment": row.get("segment"),
            "phone": row.get("phone"),
            "email": row.get("email"),
            "revenue_30d": float(row["revenue_30d"]),
            "overdue_count": row["overdue_count"],
            "overdue_sum": float(row["overdue_sum"]),
            "order_count_90d": row["order_count_90d"],
        }
        for row in rows
    ]

    return ToolResponse(data={"clients": clients, "total": len(clients)})
