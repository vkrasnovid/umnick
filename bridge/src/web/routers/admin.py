from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, text, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from logging_setup import get_logger
from messages_ru import (
    TENANT_ID_REQUIRED, TENANT_NOT_FOUND, SYNC_TRIGGERED,
    SYNC_CONNECTION_OK, SYNC_CONNECTION_FAILED, SYNC_LOG_EMPTY,
    NOT_FOUND,
)
from middleware import verify_admin_token
from models import Tenant, SyncLog, Watcher
from odata import ODataClient, ODataConnectionParams
from tasks import _run_sync_for_tenant
from models.models import Counterparty, Contract, Order, Invoice, Payment, Product, Employee

logger = get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _ensure_tenant_id(tenant_id: str | None = Header(None, alias="X-Tenant-Id")) -> str:
    if not tenant_id:
        raise HTTPException(status_code=400, detail=TENANT_ID_REQUIRED)
    return tenant_id


# ─── Schema ───

class ConnectionTestRequest(BaseModel):
    odata_url: str
    odata_username: str
    odata_password: str


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None


class SyncTriggerRequest(BaseModel):
    entity_type: str | None = None


class SyncStatusResponse(BaseModel):
    status: str
    last_sync_at: str | None = None
    entity_type: str | None = None


class SyncLogEntryResponse(BaseModel):
    id: str
    sync_type: str
    started_at: str
    finished_at: str | None
    duration_ms: int | None
    status: str
    records_processed: int
    records_updated: int
    records_created: int
    records_errors: int
    error_message: str | None


class DashboardResponse(BaseModel):
    sync_status: dict
    db_stats: dict
    watchers_count: dict
    recent_alerts: list[dict]


class WatcherCreate(BaseModel):
    name: str
    description: str | None = None
    schedule: str
    tool_name: str
    tool_params: dict | None = None
    condition: str
    message_template: str
    recipients: list[str] | None = None
    priority: str = "normal"
    enabled: bool = True


class WatcherUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    schedule: str | None = None
    tool_name: str | None = None
    tool_params: dict | None = None
    condition: str | None = None
    message_template: str | None = None
    recipients: list[str] | None = None
    priority: str | None = None
    enabled: bool | None = None


class WatcherResponse(BaseModel):
    id: str
    name: str
    description: str | None
    schedule: str
    tool_name: str
    tool_params: dict | None
    condition: str
    message_template: str
    recipients: list[str]
    priority: str
    enabled: bool
    last_run_at: str | None
    last_alert_at: str | None
    alert_count: int


class TenantCreate(BaseModel):
    name: str
    inn: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    odata_url: str
    odata_db_name: str | None = None
    odata_username: str | None = None
    odata_password: str | None = None
    is_active: bool = True
    subscription_tier: str = "basic"


class TenantResponse(BaseModel):
    id: str
    name: str
    inn: str | None
    contact_email: str | None
    contact_phone: str | None
    odata_url: str
    odata_db_name: str | None
    odata_username: str | None
    is_active: bool
    subscription_tier: str
    sync_enabled: bool
    created_at: str
    updated_at: str


class ToolMetaResponse(BaseModel):
    name: str
    display_name: str
    description: str
    parameters: dict
    status: str = "active"


# ─── Endpoints ───

@router.post("/connect", dependencies=[Depends(verify_admin_token)])
async def test_connection(
    req: ConnectionTestRequest,
    tenant_id: str = Depends(_ensure_tenant_id),
) -> ConnectionTestResponse:
    """Проверить OData подключение."""
    client = ODataClient(
        ODataConnectionParams(
            base_url=req.odata_url,
            username=req.odata_username,
            password=req.odata_password,
        )
    )
    result = await client.check_connection()
    if result.get("success"):
        return ConnectionTestResponse(success=True, message=SYNC_CONNECTION_OK)
    return ConnectionTestResponse(success=False, error=result.get("error", SYNC_CONNECTION_FAILED))


@router.post("/sync/trigger", dependencies=[Depends(verify_admin_token)])
async def trigger_sync(
    req: SyncTriggerRequest = None,
    tenant_id: str = Depends(_ensure_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Ручной запуск синхронизации."""
    from uuid import UUID
    tid = UUID(tenant_id)

    result = await session.execute(
        select(Tenant).where(Tenant.id == tid, Tenant.is_active.is_(True))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail=TENANT_NOT_FOUND)

    entity_type = req.entity_type if req and req.entity_type else "orders"

    try:
        result = await _run_sync_for_tenant(entity_type, tid)
        return {"status": "ok", "message": SYNC_TRIGGERED, "result": result}
    except Exception as e:
        logger.error("Trigger sync error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/status", dependencies=[Depends(verify_admin_token)])
async def get_sync_status(
    tenant_id: str = Depends(_ensure_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> SyncStatusResponse:
    """Статус последней синхронизации."""
    from uuid import UUID
    tid = UUID(tenant_id)

    result = await session.execute(
        select(SyncLog)
        .where(SyncLog.tenant_id == tid)
        .order_by(desc(SyncLog.started_at))
        .limit(1)
    )
    log = result.scalar_one_or_none()
    if not log:
        return SyncStatusResponse(status="no_sync")

    return SyncStatusResponse(
        status=log.status,
        last_sync_at=log.started_at.isoformat() if log.started_at else None,
        entity_type=log.sync_type,
    )


@router.get("/sync/log", dependencies=[Depends(verify_admin_token)])
async def get_sync_log(
    limit: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    tenant_id: str = Depends(_ensure_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> list[SyncLogEntryResponse]:
    """История синхронизаций."""
    from uuid import UUID
    tid = UUID(tenant_id)

    query = select(SyncLog).where(SyncLog.tenant_id == tid)
    if status_filter:
        query = query.where(SyncLog.status == status_filter)
    query = query.order_by(desc(SyncLog.started_at)).limit(limit)

    result = await session.execute(query)
    logs = result.scalars().all()

    return [
        SyncLogEntryResponse(
            id=str(log.id),
            sync_type=log.sync_type,
            started_at=log.started_at.isoformat() if log.started_at else "",
            finished_at=log.finished_at.isoformat() if log.finished_at else None,
            duration_ms=log.duration_ms,
            status=log.status,
            records_processed=log.records_processed,
            records_updated=log.records_updated,
            records_created=log.records_created,
            records_errors=log.records_errors,
            error_message=log.error_message,
        )
        for log in logs
    ]


@router.get("/dashboard", dependencies=[Depends(verify_admin_token)])
async def get_dashboard(
    tenant_id: str = Depends(_ensure_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> DashboardResponse:
    """Статистика для Dashboard."""
    from uuid import UUID
    tid = UUID(tenant_id)

    # Last sync status
    result = await session.execute(
        select(SyncLog)
        .where(SyncLog.tenant_id == tid)
        .order_by(desc(SyncLog.started_at))
        .limit(1)
    )
    last_sync = result.scalar_one_or_none()

    # DB stats
    stats = {}
    for table_name, model_cls in [
        ("counterparties", Counterparty),
        ("contracts", Contract),
        ("orders", Order),
        ("products", Product),
    ]:
        cnt = await session.execute(
            select(func.count()).select_from(model_cls).where(model_cls.tenant_id == tid)  # type: ignore
        )
        stats[table_name] = cnt.scalar() or 0

    # Watcher stats
    watcher_total = await session.execute(
        select(func.count()).select_from(Watcher).where(Watcher.tenant_id == tid)  # type: ignore
    )
    watcher_active = await session.execute(
        select(func.count()).select_from(Watcher)
        .where(Watcher.tenant_id == tid, Watcher.enabled.is_(True))  # type: ignore
    )
    watcher_alerting = await session.execute(
        select(func.count()).select_from(Watcher)
        .where(Watcher.tenant_id == tid, Watcher.alert_count > 0)  # type: ignore
    )

    return DashboardResponse(
        sync_status={
            "last_sync": last_sync.started_at.isoformat() if last_sync and last_sync.started_at else None,
            "status": last_sync.status if last_sync else "no_sync",
        },
        db_stats=stats,
        watchers_count={
            "total": watcher_total.scalar() or 0,
            "active": watcher_active.scalar() or 0,
            "alerting": watcher_alerting.scalar() or 0,
        },
        recent_alerts=[],
    )


@router.get("/watchers", response_model=list[WatcherResponse], dependencies=[Depends(verify_admin_token)])
async def list_watchers(
    tenant_id: str = Depends(_ensure_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Список watchers."""
    from uuid import UUID
    tid = UUID(tenant_id)

    result = await session.execute(
        select(Watcher).where(Watcher.tenant_id == tid).order_by(Watcher.created_at.desc())
    )
    watchers = result.scalars().all()

    return [
        WatcherResponse(
            id=str(w.id),
            name=w.name,
            description=w.description,
            schedule=w.schedule,
            tool_name=w.tool_name,
            tool_params=w.tool_params or {},
            condition=w.condition,
            message_template=w.message_template,
            recipients=list(w.recipients) if w.recipients else [],
            priority=w.priority,
            enabled=w.enabled,
            last_run_at=w.last_run_at.isoformat() if w.last_run_at else None,
            last_alert_at=w.last_alert_at.isoformat() if w.last_alert_at else None,
            alert_count=w.alert_count,
        )
        for w in watchers
    ]


@router.post("/watchers", response_model=WatcherResponse, status_code=201, dependencies=[Depends(verify_admin_token)])
async def create_watcher(
    data: WatcherCreate,
    tenant_id: str = Depends(_ensure_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Создать watcher."""
    from uuid import UUID
    tid = UUID(tenant_id)

    watcher = Watcher(
        tenant_id=tid,
        name=data.name,
        description=data.description,
        schedule=data.schedule,
        tool_name=data.tool_name,
        tool_params=data.tool_params or {},
        condition=data.condition,
        message_template=data.message_template,
        recipients=data.recipients or [],
        priority=data.priority,
        enabled=data.enabled,
    )
    session.add(watcher)
    await session.commit()
    await session.refresh(watcher)

    return WatcherResponse(
        id=str(watcher.id),
        name=watcher.name,
        description=watcher.description,
        schedule=watcher.schedule,
        tool_name=watcher.tool_name,
        tool_params=watcher.tool_params or {},
        condition=watcher.condition,
        message_template=watcher.message_template,
        recipients=list(watcher.recipients) if watcher.recipients else [],
        priority=watcher.priority,
        enabled=watcher.enabled,
        last_run_at=watcher.last_run_at.isoformat() if watcher.last_run_at else None,
        last_alert_at=watcher.last_alert_at.isoformat() if watcher.last_alert_at else None,
        alert_count=watcher.alert_count,
    )


@router.get("/watchers/{watcher_id}", response_model=WatcherResponse, dependencies=[Depends(verify_admin_token)])
async def get_watcher(
    watcher_id: str,
    tenant_id: str = Depends(_ensure_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Детали watcher."""
    from uuid import UUID
    tid = UUID(tenant_id)
    wid = UUID(watcher_id)

    result = await session.execute(
        select(Watcher).where(Watcher.id == wid, Watcher.tenant_id == tid)
    )
    watcher = result.scalar_one_or_none()
    if not watcher:
        raise HTTPException(status_code=404, detail=NOT_FOUND)

    return WatcherResponse(
        id=str(watcher.id),
        name=watcher.name,
        description=watcher.description,
        schedule=watcher.schedule,
        tool_name=watcher.tool_name,
        tool_params=watcher.tool_params or {},
        condition=watcher.condition,
        message_template=watcher.message_template,
        recipients=list(watcher.recipients) if watcher.recipients else [],
        priority=watcher.priority,
        enabled=watcher.enabled,
        last_run_at=watcher.last_run_at.isoformat() if watcher.last_run_at else None,
        last_alert_at=watcher.last_alert_at.isoformat() if watcher.last_alert_at else None,
        alert_count=watcher.alert_count,
    )


@router.put("/watchers/{watcher_id}", response_model=WatcherResponse, dependencies=[Depends(verify_admin_token)])
async def update_watcher(
    watcher_id: str,
    data: WatcherUpdate,
    tenant_id: str = Depends(_ensure_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Обновить watcher."""
    from uuid import UUID
    tid = UUID(tenant_id)
    wid = UUID(watcher_id)

    result = await session.execute(
        select(Watcher).where(Watcher.id == wid, Watcher.tenant_id == tid)
    )
    watcher = result.scalar_one_or_none()
    if not watcher:
        raise HTTPException(status_code=404, detail=NOT_FOUND)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(watcher, key, value)

    await session.commit()
    await session.refresh(watcher)

    return WatcherResponse(
        id=str(watcher.id),
        name=watcher.name,
        description=watcher.description,
        schedule=watcher.schedule,
        tool_name=watcher.tool_name,
        tool_params=watcher.tool_params or {},
        condition=watcher.condition,
        message_template=watcher.message_template,
        recipients=list(watcher.recipients) if watcher.recipients else [],
        priority=watcher.priority,
        enabled=watcher.enabled,
        last_run_at=watcher.last_run_at.isoformat() if watcher.last_run_at else None,
        last_alert_at=watcher.last_alert_at.isoformat() if watcher.last_alert_at else None,
        alert_count=watcher.alert_count,
    )


@router.delete("/watchers/{watcher_id}", dependencies=[Depends(verify_admin_token)])
async def delete_watcher(
    watcher_id: str,
    tenant_id: str = Depends(_ensure_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Удалить watcher."""
    from uuid import UUID
    tid = UUID(tenant_id)
    wid = UUID(watcher_id)

    result = await session.execute(
        select(Watcher).where(Watcher.id == wid, Watcher.tenant_id == tid)
    )
    watcher = result.scalar_one_or_none()
    if not watcher:
        raise HTTPException(status_code=404, detail=NOT_FOUND)

    await session.delete(watcher)
    await session.commit()

    return {"status": "ok", "message": "Watcher deleted"}


@router.get("/tools", dependencies=[Depends(verify_admin_token)])
async def list_tools() -> list[ToolMetaResponse]:
    """Список tools с метаданными."""
    tools = [
        ToolMetaResponse(
            name="get_contract_utilization",
            display_name="Статус исполнения договора",
            description="Получить статус исполнения договора — сумму, процент, остаток.",
            parameters={
                "type": "object",
                "properties": {
                    "contract_id": {"type": "string", "format": "uuid"},
                    "counterparty_id": {"type": "string", "format": "uuid"},
                    "contract_number": {"type": "string"},
                },
            },
        ),
        ToolMetaResponse(
            name="get_overdue_payments",
            display_name="Просроченные платежи",
            description="Получить список просроченных платежей — долги клиентов с overdue-счетами.",
            parameters={
                "type": "object",
                "properties": {
                    "days_overdue_min": {"type": "integer", "default": 1},
                    "limit": {"type": "integer", "default": 20},
                    "counterparty_id": {"type": "string", "format": "uuid"},
                    "threshold_amount": {"type": "number", "minimum": 0},
                },
            },
        ),
        ToolMetaResponse(
            name="get_client_activity",
            display_name="Активность клиента",
            description="Получить активность клиента — заказы, платежи, счета за период.",
            parameters={
                "type": "object",
                "properties": {
                    "counterparty_id": {"type": "string", "format": "uuid"},
                    "inn": {"type": "string"},
                    "period_days": {"type": "integer", "default": 30},
                },
            },
        ),
        ToolMetaResponse(
            name="query_sales",
            display_name="Анализ продаж",
            description="Анализ продаж — выручка, количество, динамика.",
            parameters={
                "type": "object",
                "properties": {
                    "period_days": {"type": "integer", "default": 30},
                    "granularity": {"type": "string", "enum": ["day", "week", "month"]},
                    "counterparty_id": {"type": "string", "format": "uuid"},
                },
            },
        ),
        ToolMetaResponse(
            name="find_contracts",
            display_name="Поиск договоров",
            description="Поиск договоров по различным критериям.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "status": {"type": "string", "enum": ["active", "closed", "suspended"]},
                    "counterparty_id": {"type": "string", "format": "uuid"},
                    "expiring_soon_days": {"type": "integer"},
                    "min_amount": {"type": "number"},
                },
            },
        ),
        ToolMetaResponse(
            name="get_client_360",
            display_name="Карточка клиента 360°",
            description="Полная карточка клиента 360° — все данные о контрагенте.",
            parameters={
                "type": "object",
                "properties": {
                    "counterparty_id": {"type": "string", "format": "uuid"},
                    "inn": {"type": "string"},
                    "name_query": {"type": "string"},
                },
            },
        ),
        ToolMetaResponse(
            name="list_active_clients",
            display_name="Активные клиенты",
            description="Список активных клиентов с ключевыми метриками.",
            parameters={
                "type": "object",
                "properties": {
                    "segment": {"type": "string", "enum": ["vip", "wholesale", "retail"]},
                    "has_overdue": {"type": "boolean"},
                    "min_revenue_30d": {"type": "number"},
                    "limit": {"type": "integer", "default": 20},
                    "sort_by": {"type": "string", "enum": ["revenue", "name", "overdue"]},
                },
            },
        ),
    ]
    return tools


# ─── Tenants CRUD ───

@router.get("/tenants", response_model=list[TenantResponse], dependencies=[Depends(verify_admin_token)])
async def list_tenants(session: AsyncSession = Depends(get_session)):
    """Список тенантов (admin-only)."""
    result = await session.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()
    return [
        TenantResponse(
            id=str(t.id),
            name=t.name,
            inn=t.inn,
            contact_email=t.contact_email,
            contact_phone=t.contact_phone,
            odata_url=t.odata_url,
            odata_db_name=t.odata_db_name,
            odata_username=t.odata_username,
            is_active=t.is_active,
            subscription_tier=t.subscription_tier,
            sync_enabled=t.sync_enabled,
            created_at=t.created_at.isoformat() if t.created_at else "",
            updated_at=t.updated_at.isoformat() if t.updated_at else "",
        )
        for t in tenants
    ]


@router.post("/tenants", response_model=TenantResponse, status_code=201, dependencies=[Depends(verify_admin_token)])
async def create_tenant(
    data: TenantCreate,
    session: AsyncSession = Depends(get_session),
):
    """Создать тенант."""
    tenant = Tenant(
        name=data.name,
        inn=data.inn,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        odata_url=data.odata_url,
        odata_db_name=data.odata_db_name,
        odata_username=data.odata_username,
        odata_password_enc=data.odata_password,
        is_active=data.is_active,
        subscription_tier=data.subscription_tier,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    return TenantResponse(
        id=str(tenant.id),
        name=tenant.name,
        inn=tenant.inn,
        contact_email=tenant.contact_email,
        contact_phone=tenant.contact_phone,
        odata_url=tenant.odata_url,
        odata_db_name=tenant.odata_db_name,
        odata_username=tenant.odata_username,
        is_active=tenant.is_active,
        subscription_tier=tenant.subscription_tier,
        sync_enabled=tenant.sync_enabled,
        created_at=tenant.created_at.isoformat() if tenant.created_at else "",
        updated_at=tenant.updated_at.isoformat() if tenant.updated_at else "",
    )
