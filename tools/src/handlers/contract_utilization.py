from __future__ import annotations

from uuid import UUID

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import ContractUtilizationParams, ToolResponse


async def handle_contract_utilization(
    params: ContractUtilizationParams,
    tenant_id: str,
    session: AsyncSession,
) -> ToolResponse:
    """Получить статус исполнения договора."""
    try:
        tid = UUID(tenant_id)
    except ValueError:
        return ToolResponse(success=False, error="Invalid tenant_id")

    result = await session.execute(
        sa_text("""
            WITH target AS (
                SELECT id, tenant_id, number, counterparty_id, date_start, date_end,
                       amount, currency, utilization_sum, utilization_pct, status
                FROM umnick.contracts
                WHERE tenant_id = :tenant_id
                  AND (:contract_id IS NULL OR id = :contract_id::uuid)
                  AND (:counterparty_id IS NULL OR counterparty_id = :counterparty_id::uuid)
                  AND (:contract_number IS NULL OR number ILIKE '%' || :contract_number || '%')
                LIMIT 1
            )
            SELECT c.id, c.number, c.date_start, c.date_end, c.amount,
                   c.currency, c.utilization_sum, c.utilization_pct, c.status,
                   cp.name AS counterparty_name,
                   (c.amount - c.utilization_sum) AS remaining
            FROM target c
            LEFT JOIN umnick.counterparties cp ON cp.id = c.counterparty_id AND cp.tenant_id = :tenant_id
        """),
        {
            "tenant_id": tid,
            "contract_id": params.contract_id,
            "counterparty_id": params.counterparty_id,
            "contract_number": params.contract_number,
        },
    )
    row = result.mappings().first()
    if not row:
        return ToolResponse(success=False, error="Договор не найден")

    contract_data = {
        "id": str(row["id"]),
        "number": row["number"],
        "counterparty": row["counterparty_name"],
        "date_start": str(row["date_start"]) if row["date_start"] else None,
        "date_end": str(row["date_end"]) if row["date_end"] else None,
        "amount": float(row["amount"]),
        "currency": row["currency"],
        "utilization_sum": float(row["utilization_sum"]),
        "utilization_pct": float(row["utilization_pct"]),
        "remaining": float(row["remaining"]),
        "status": row["status"],
    }

    return ToolResponse(data={"contract": contract_data, "recent_invoices": []})
