from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class ToolResponse(BaseModel):
    success: bool = True
    data: Any = None
    error: str | None = None


class ContractUtilizationParams(BaseModel):
    contract_id: str | None = Field(None, description="ID договора")
    counterparty_id: str | None = Field(None, description="ID контрагента")
    contract_number: str | None = Field(None, description="Номер договора")


class OverduePaymentsParams(BaseModel):
    days_overdue_min: int = Field(1, ge=0, description="Минимальное количество дней просрочки")
    limit: int = Field(20, ge=1, le=100, description="Максимум результатов")
    counterparty_id: str | None = None
    threshold_amount: float | None = Field(None, ge=0, description="Минимальная сумма просрочки")


class ClientActivityParams(BaseModel):
    counterparty_id: str | None = None
    inn: str | None = None
    period_days: int = Field(30, ge=1, le=365)
    include_invoices: bool = True
    include_payments: bool = True
    include_orders: bool = True


class QuerySalesParams(BaseModel):
    period_days: int = Field(30, ge=1, le=365)
    granularity: str = Field("day", pattern=r"^(day|week|month)$")
    counterparty_id: str | None = None
    include_chart_data: bool = False


class FindContractsParams(BaseModel):
    query: str | None = None
    status: str | None = Field(None, pattern=r"^(active|closed|suspended)$")
    counterparty_id: str | None = None
    expiring_soon_days: int | None = None
    min_amount: float | None = Field(None, ge=0)
    limit: int = Field(20, ge=1, le=50)


class Client360Params(BaseModel):
    counterparty_id: str | None = None
    inn: str | None = None
    name_query: str | None = None


class ActiveClientsParams(BaseModel):
    segment: str | None = Field(None, pattern=r"^(vip|wholesale|retail)$")
    has_overdue: bool | None = None
    min_revenue_30d: float | None = Field(None, ge=0)
    limit: int = Field(20, ge=1, le=50)
    sort_by: str = Field("revenue", pattern=r"^(revenue|name|overdue)$")
