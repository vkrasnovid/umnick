from __future__ import annotations

from uuid import UUID

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import FindContractsParams, ToolResponse


async def handle_find_contracts(
    params: FindContractsParams,
    tenant_id: str,
    session: AsyncSession,
) -> ToolResponse:
    """Поиск договоров по различным критериям."""
    try:
        tid = UUID(tenant_id)
    except ValueError:
        return ToolResponse(success=False, error="Invalid tenant_id")

    result = await session.execute(
        sa_text("""
            SELECT c.id, c.number, c.date_start, c.date_end, c.amount,
                   c.currency, c.utilization_sum, c.utilization_pct, c.status,
                   c.contract_type,
                   cp.name AS counterparty_name
            FROM umnick.contracts c
            LEFT JOIN umnick.counterparties cp ON cp.id = c.counterparty_id AND cp.tenant_id = :tenant_id
            WHERE c.tenant_id = :tenant_id
              AND (:query IS NULL
                   OR c.number ILIKE '%' || :query || '%'
                   OR cp.name ILIKE '%' || :query || '%')
              AND (:status IS NULL OR c.status = :status)
              AND (:counterparty_id IS NULL OR c.counterparty_id = :counterparty_id::uuid)
              AND (:expiring_soon_days IS NULL
                   OR (c.date_end IS NOT NULL
                       AND c.date_end BETWEEN CURRENT_DATE AND CURRENT_DATE + :expiring_soon_days::integer))
              AND (:min_amount IS NULL OR c.amount >= :min_amount::numeric)
            ORDER BY c.date_start DESC
            LIMIT :limit
        """),
        {
            "tenant_id": tid,
            "query": params.query,
            "status": params.status,
            "counterparty_id": params.counterparty_id,
            "expiring_soon_days": params.expiring_soon_days,
            "min_amount": params.min_amount,
            "limit": params.limit,
        },
    )
    rows = result.mappings().all()

    contracts = [
        {
            "id": str(row["id"]),
            "number": row["number"],
            "counterparty": row["counterparty_name"],
            "date_start": str(row["date_start"]) if row["date_start"] else None,
            "date_end": str(row["date_end"]) if row["date_end"] else None,
            "amount": float(row["amount"]),
            "currency": row["currency"],
            "utilization_sum": float(row["utilization_sum"]),
            "utilization_pct": float(row["utilization_pct"]),
            "status": row["status"],
            "contract_type": row["contract_type"],
        }
        for row in rows
    ]

    return ToolResponse(data={"contracts": contracts, "total": len(contracts)})
