from __future__ import annotations

from uuid import UUID

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import Client360Params, ToolResponse


async def handle_client_360(
    params: Client360Params,
    tenant_id: str,
    session: AsyncSession,
) -> ToolResponse:
    """Полная карточка клиента 360°."""
    try:
        tid = UUID(tenant_id)
    except ValueError:
        return ToolResponse(success=False, error="Invalid tenant_id")

    # 1. Контрагент
    cp_result = await session.execute(
        sa_text("""
            SELECT *
            FROM umnick.counterparties
            WHERE tenant_id = :tenant_id
              AND (CAST(:counterparty_id AS uuid) IS NULL OR id = CAST(:counterparty_id AS uuid))
              AND (CAST(:inn AS text) IS NULL OR inn = CAST(:inn AS text))
              AND (CAST(:name_query AS text) IS NULL OR name ILIKE '%' || CAST(:name_query AS text) || '%')
            LIMIT 1
        """),
        {
            "tenant_id": tid,
            "counterparty_id": params.counterparty_id,
            "inn": params.inn,
            "name_query": params.name_query,
        },
    )
    cp = cp_result.mappings().first()
    if not cp:
        return ToolResponse(success=False, error="Контрагент не найден")

    cp_id = cp["id"]

    # 2. Активные договоры
    contracts_result = await session.execute(
        sa_text("""
            SELECT *
            FROM umnick.contracts
            WHERE tenant_id = :tenant_id AND counterparty_id = :cp_id AND status = 'active'
            ORDER BY date_start DESC
        """),
        {"tenant_id": tid, "cp_id": cp_id},
    )
    contracts = [dict(row) for row in contracts_result.mappings().all()]

    # 3. Просроченные счета
    overdue_result = await session.execute(
        sa_text("""
            SELECT COUNT(*) AS overdue_count, COALESCE(SUM(balance), 0) AS total_overdue
            FROM umnick.invoices
            WHERE tenant_id = :tenant_id
              AND counterparty_id = :cp_id
              AND status IN ('unpaid', 'partial')
              AND due_date < CURRENT_DATE
        """),
        {"tenant_id": tid, "cp_id": cp_id},
    )
    overdue = overdue_result.mappings().first()

    # 4. Последние заказы
    orders_result = await session.execute(
        sa_text("""
            SELECT number, date, amount, status
            FROM umnick.orders
            WHERE tenant_id = :tenant_id AND counterparty_id = :cp_id
            ORDER BY date DESC
            LIMIT 10
        """),
        {"tenant_id": tid, "cp_id": cp_id},
    )
    orders = [dict(row) for row in orders_result.mappings().all()]

    # 5. Продажи за 30 дней
    sales_result = await session.execute(
        sa_text("""
            SELECT COALESCE(SUM(amount), 0) AS sales_30d
            FROM umnick.orders
            WHERE tenant_id = :tenant_id
              AND counterparty_id = :cp_id
              AND date >= CURRENT_DATE - 30
              AND status NOT IN ('cancelled', 'draft')
        """),
        {"tenant_id": tid, "cp_id": cp_id},
    )
    sales_30d = sales_result.scalar() or 0

    return ToolResponse(data={
        "counterparty": {
            "id": str(cp["id"]),
            "name": cp["name"],
            "full_name": cp.get("full_name"),
            "inn": cp.get("inn"),
            "kpp": cp.get("kpp"),
            "ogrn": cp.get("ogrn"),
            "status": cp["status"],
            "segment": cp.get("segment"),
            "phone": cp.get("phone"),
            "email": cp.get("email"),
            "is_client": cp.get("is_client", False),
            "is_supplier": cp.get("is_supplier", False),
        },
        "contracts_active": [
            {
                "id": str(c["id"]),
                "number": c["number"],
                "date_start": str(c["date_start"]) if c.get("date_start") else None,
                "date_end": str(c["date_end"]) if c.get("date_end") else None,
                "amount": float(c["amount"]),
                "currency": c.get("currency", "RUB"),
                "utilization_sum": float(c["utilization_sum"]),
                "utilization_pct": float(c["utilization_pct"]),
                "status": c["status"],
            }
            for c in contracts
        ],
        "overdue_summary": {
            "overdue_count": overdue["overdue_count"] if overdue else 0,
            "total_overdue": float(overdue["total_overdue"]) if overdue else 0,
        },
        "recent_orders": orders,
        "sales_30d": float(sales_30d),
    })
