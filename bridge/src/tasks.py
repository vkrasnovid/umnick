from __future__ import annotations

"""
Celery задачи для синхронизации данных из 1С.
"""

import uuid
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import async_session_factory
from logging_setup import get_logger, correlation_id_ctx, setup_logging
from models import Tenant, SyncLog
from sync import (
    CounterpartySyncWorker, ContractSyncWorker, OrderSyncWorker,
    InvoiceSyncWorker, PaymentSyncWorker, ProductSyncWorker, EmployeeSyncWorker,
)

setup_logging("umnick-bridge")
logger = get_logger(__name__)

celery_app = Celery(
    "umnick_bridge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Beat schedule for sync tasks (bridge runs its own beat process)
celery_app.conf.beat_schedule = {
    "sync-orders-every-5min": {
        "task": "tasks.sync_orders",
        "schedule": 300.0,
    },
    "sync-invoices-every-5min": {
        "task": "tasks.sync_invoices",
        "schedule": 300.0,
    },
    "sync-payments-every-5min": {
        "task": "tasks.sync_payments",
        "schedule": 300.0,
    },
    "sync-contracts-every-15min": {
        "task": "tasks.sync_contracts_counterparties",
        "schedule": 900.0,
    },
    "sync-counterparties-every-15min": {
        "task": "tasks.sync_counterparties",
        "schedule": 900.0,
    },
    "sync-products-every-hour": {
        "task": "tasks.sync_products",
        "schedule": 3600.0,
    },
    "sync-employees-every-hour": {
        "task": "tasks.sync_employees",
        "schedule": 3600.0,
    },
    "full-reconciliation-daily": {
        "task": "tasks.full_reconciliation",
        "schedule": crontab(hour=2, minute=0),
    },
}


def get_sync_worker(entity_name: str, tenant_id: uuid.UUID, tenant_settings: dict):
    """Фабрика sync worker по имени сущности."""
    workers = {
        "counterparties": CounterpartySyncWorker,
        "contracts": ContractSyncWorker,
        "orders": OrderSyncWorker,
        "invoices": InvoiceSyncWorker,
        "payments": PaymentSyncWorker,
        "products": ProductSyncWorker,
        "employees": EmployeeSyncWorker,
    }
    worker_cls = workers.get(entity_name)
    if not worker_cls:
        raise ValueError(f"Unknown entity: {entity_name}")
    return worker_cls(tenant_id, tenant_settings)


async def _run_sync_for_tenant(entity_name: str, tenant_id: uuid.UUID) -> dict:
    """Запустить синхронизацию для конкретного тенанта."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active.is_(True))
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return {"status": "error", "error": "Tenant not found or inactive"}

        tenant_settings = {
            "odata_url": tenant.odata_url,
            "odata_username": tenant.odata_username or "",
            "odata_password_enc": tenant.odata_password_enc or "",
        }

        worker = get_sync_worker(entity_name, tenant_id, tenant_settings)
        sync_result = await worker.run(session)

        return {
            "status": "error" if sync_result.error_message else "success",
            "processed": sync_result.records_processed,
            "created": sync_result.records_created,
            "updated": sync_result.records_updated,
            "errors": sync_result.records_errors,
            "duration_ms": sync_result.duration_ms,
            "error": sync_result.error_message,
        }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_orders(self) -> dict:
    """Синхронизация заказов (каждые 5 мин)."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_sync_all("orders"))
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_invoices(self) -> dict:
    """Синхронизация счетов (каждые 5 мин)."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_sync_all("invoices"))
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_payments(self) -> dict:
    """Синхронизация платежей (каждые 5 мин)."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_sync_all("payments"))
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_contracts_counterparties(self) -> dict:
    """Синхронизация договоров и контрагентов (каждые 15 мин)."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_sync_all("contracts"))
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_counterparties(self) -> dict:
    """Синхронизация контрагентов (каждые 15 мин)."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_sync_all("counterparties"))
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_products(self) -> dict:
    """Синхронизация товаров (каждый час)."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_sync_all("products"))
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_employees(self) -> dict:
    """Синхронизация сотрудников (каждый час)."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_sync_all("employees"))
    finally:
        loop.close()


async def _run_sync_all(entity_name: str) -> dict:
    """Запустить синхронизацию для всех активных тенантов."""
    results = {}
    async with async_session_factory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.is_active.is_(True), Tenant.sync_enabled.is_(True))
        )
        tenants = result.scalars().all()

        for tenant in tenants:
            try:
                tenant_result = await _run_sync_for_tenant(entity_name, tenant.id)
                results[str(tenant.id)] = tenant_result
            except Exception as e:
                logger.error("Sync error for tenant", tenant_id=str(tenant.id), error=str(e))
                results[str(tenant.id)] = {"status": "error", "error": str(e)}

    return results


@celery_app.task(bind=True)
def full_reconciliation(self) -> dict:
    """Полная сверка всех сущностей (ночной, раз в сутки)."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        entities = ["counterparties", "contracts", "orders", "invoices",
                     "payments", "products", "employees"]
        results = {}
        for entity in entities:
            try:
                results[entity] = loop.run_until_complete(_run_sync_all(entity))
            except Exception as e:
                results[entity] = {"status": "error", "error": str(e)}
        return results
    finally:
        loop.close()



