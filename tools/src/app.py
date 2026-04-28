from __future__ import annotations

"""
Tool Runtime — FastAPI приложение для выполнения 7 business tools.
Все tools read-only, работают через параметризованные SQL-запросы.
"""

from uuid import UUID

from fastapi import FastAPI, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_session
from schemas import (
    ContractUtilizationParams, OverduePaymentsParams,
    ClientActivityParams, QuerySalesParams, FindContractsParams,
    Client360Params, ActiveClientsParams, ToolResponse,
)
from handlers import (
    handle_contract_utilization,
    handle_overdue_payments,
    handle_client_activity,
    handle_query_sales,
    handle_find_contracts,
    handle_client_360,
    handle_active_clients,
)

app = FastAPI(
    title="Умник — Tool Runtime",
    description="Tool Library — бизнес-логика для AI-агента",
    version="1.0.0",
)


async def get_tenant_id(x_tenant_id: str = Header(..., alias="X-Tenant-Id")) -> str:
    """Извлечение tenant_id из заголовка."""
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-Id header required")
    # Validate UUID format
    try:
        UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant_id format")
    return x_tenant_id


@app.get("/tools/get_contract_utilization")
async def get_contract_utilization(
    contract_id: str | None = None,
    counterparty_id: str | None = None,
    contract_number: str | None = None,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> ToolResponse:
    params = ContractUtilizationParams(
        contract_id=contract_id,
        counterparty_id=counterparty_id,
        contract_number=contract_number,
    )
    return await handle_contract_utilization(params, tenant_id, session)


@app.get("/tools/get_overdue_payments")
async def get_overdue_payments(
    days_overdue_min: int = 1,
    limit: int = 20,
    counterparty_id: str | None = None,
    threshold_amount: float | None = None,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> ToolResponse:
    params = OverduePaymentsParams(
        days_overdue_min=days_overdue_min,
        limit=limit,
        counterparty_id=counterparty_id,
        threshold_amount=threshold_amount,
    )
    return await handle_overdue_payments(params, tenant_id, session)


@app.get("/tools/get_client_activity")
async def get_client_activity(
    counterparty_id: str | None = None,
    inn: str | None = None,
    period_days: int = 30,
    include_invoices: bool = True,
    include_payments: bool = True,
    include_orders: bool = True,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> ToolResponse:
    params = ClientActivityParams(
        counterparty_id=counterparty_id,
        inn=inn,
        period_days=period_days,
        include_invoices=include_invoices,
        include_payments=include_payments,
        include_orders=include_orders,
    )
    return await handle_client_activity(params, tenant_id, session)


@app.get("/tools/query_sales")
async def query_sales(
    period_days: int = 30,
    granularity: str = "day",
    counterparty_id: str | None = None,
    include_chart_data: bool = False,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> ToolResponse:
    params = QuerySalesParams(
        period_days=period_days,
        granularity=granularity,
        counterparty_id=counterparty_id,
        include_chart_data=include_chart_data,
    )
    return await handle_query_sales(params, tenant_id, session)


@app.get("/tools/find_contracts")
async def find_contracts(
    query: str | None = None,
    status: str | None = None,
    counterparty_id: str | None = None,
    expiring_soon_days: int | None = None,
    min_amount: float | None = None,
    limit: int = 20,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> ToolResponse:
    params = FindContractsParams(
        query=query,
        status=status,
        counterparty_id=counterparty_id,
        expiring_soon_days=expiring_soon_days,
        min_amount=min_amount,
        limit=limit,
    )
    return await handle_find_contracts(params, tenant_id, session)


@app.get("/tools/get_client_360")
async def get_client_360(
    counterparty_id: str | None = None,
    inn: str | None = None,
    name_query: str | None = None,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> ToolResponse:
    params = Client360Params(
        counterparty_id=counterparty_id,
        inn=inn,
        name_query=name_query,
    )
    return await handle_client_360(params, tenant_id, session)


@app.get("/tools/list_active_clients")
async def list_active_clients(
    segment: str | None = None,
    has_overdue: bool | None = None,
    min_revenue_30d: float | None = None,
    limit: int = 20,
    sort_by: str = "revenue",
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> ToolResponse:
    params = ActiveClientsParams(
        segment=segment,
        has_overdue=has_overdue,
        min_revenue_30d=min_revenue_30d,
        limit=limit,
        sort_by=sort_by,
    )
    return await handle_active_clients(params, tenant_id, session)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tool-runtime"}
