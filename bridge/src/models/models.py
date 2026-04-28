from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Computed, Date, DateTime, ForeignKey,
    Index, Integer, Numeric, String, Text, text, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import metadata  # noqa: F401
from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> uuid.UUID:
    return uuid.uuid4()


class TimestampMixin:
    """Mixin with tenant_id, created_at, updated_at."""
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("umnick.tenants.id"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"),
        onupdate=datetime.now(timezone.utc), nullable=False,
    )


# Schema reference
SCHEMA = "umnick"


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint(
            "subscription_tier IN ('basic', 'pro', 'enterprise')",
            name="ck_tenants_tier",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid,
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    inn: Mapped[Optional[str]] = mapped_column(String(12))
    contact_email: Mapped[Optional[str]] = mapped_column(String(256))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(64))
    odata_url: Mapped[str] = mapped_column(Text, nullable=False)
    odata_db_name: Mapped[Optional[str]] = mapped_column(String(128))
    odata_username: Mapped[Optional[str]] = mapped_column(String(128))
    odata_password_enc: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    subscription_tier: Mapped[str] = mapped_column(
        String(16), default="basic",
    )
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"),
        onupdate=datetime.now(timezone.utc), nullable=False,
    )


class Counterparty(Base, TimestampMixin):
    __tablename__ = "counterparties"
    __table_args__ = (
        CheckConstraint(
            "counterparty_type IN ('legal', 'individual', 'foreign')",
            name="ck_cp_type",
        ),
        CheckConstraint(
            "status IN ('active', 'blocked', 'archived')",
            name="ck_cp_status",
        ),
        Index("idx_counterparties_tenant_external", "tenant_id", "external_id", unique=True),
        Index("idx_counterparties_tenant_version", "tenant_id", Column("data_version").desc()),
        Index("idx_counterparties_inn", "tenant_id", "inn",
              postgresql_where=Column("inn").is_not(None)),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid,
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(1024))
    inn: Mapped[Optional[str]] = mapped_column(String(12))
    kpp: Mapped[Optional[str]] = mapped_column(String(9))
    ogrn: Mapped[Optional[str]] = mapped_column(String(15))
    legal_address: Mapped[Optional[str]] = mapped_column(Text)
    actual_address: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(String(64))
    email: Mapped[Optional[str]] = mapped_column(String(256))
    website: Mapped[Optional[str]] = mapped_column(String(512))
    counterparty_type: Mapped[Optional[str]] = mapped_column(String(32))
    is_client: Mapped[bool] = mapped_column(Boolean, default=False)
    is_supplier: Mapped[bool] = mapped_column(Boolean, default=False)
    is_buyer: Mapped[bool] = mapped_column(Boolean, default=False)
    segment: Mapped[Optional[str]] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="active")
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    contracts = relationship("Contract", back_populates="counterparty")
    orders = relationship("Order", back_populates="counterparty")
    invoices = relationship("Invoice", back_populates="counterparty")
    payments = relationship("Payment", back_populates="counterparty")


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint(
            "contract_type IN ('sales', 'purchase', 'commission', 'service', 'other')",
            name="ck_contract_type",
        ),
        CheckConstraint(
            "status IN ('active', 'closed', 'suspended')",
            name="ck_contract_status",
        ),
        Index("idx_contracts_tenant_external", "tenant_id", "external_id", unique=True),
        Index("idx_contracts_tenant_version", "tenant_id", Column("data_version").desc()),
        Index("idx_contracts_counterparty", "tenant_id", "counterparty_id"),
        Index("idx_contracts_status", "tenant_id", "status"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid,
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    counterparty_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("umnick.counterparties.id", ondelete="RESTRICT"),
    )
    counterparty_external_id: Mapped[Optional[str]] = mapped_column(String(64))
    number: Mapped[Optional[str]] = mapped_column(String(64))
    date_start: Mapped[datetime] = mapped_column(Date, nullable=False)
    date_end: Mapped[Optional[datetime]] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    contract_type: Mapped[Optional[str]] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="active")
    close_reason: Mapped[Optional[str]] = mapped_column(Text)
    utilization_sum: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    utilization_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    last_utilization_date: Mapped[Optional[datetime]] = mapped_column(Date)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    counterparty = relationship("Counterparty", back_populates="contracts")


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending', 'confirmed', 'shipped', 'completed', 'cancelled')",
            name="ck_order_status",
        ),
        Index("idx_orders_tenant_external", "tenant_id", "external_id", unique=True),
        Index("idx_orders_tenant_version", "tenant_id", Column("data_version").desc()),
        Index("idx_orders_counterparty", "tenant_id", "counterparty_id"),
        Index("idx_orders_date", "tenant_id", Column("date").desc()),
        Index("idx_orders_status", "tenant_id", "status"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid,
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    counterparty_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("umnick.counterparties.id", ondelete="RESTRICT"),
    )
    counterparty_external_id: Mapped[Optional[str]] = mapped_column(String(64))
    number: Mapped[str] = mapped_column(String(64), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    paid_amount: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    delivery_date: Mapped[Optional[datetime]] = mapped_column(Date)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    counterparty = relationship("Counterparty", back_populates="orders")
    invoices = relationship("Invoice", back_populates="order")
    payments = relationship("Payment", back_populates="order")


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint(
            "status IN ('unpaid', 'partial', 'paid', 'overdue', 'cancelled')",
            name="ck_invoice_status",
        ),
        CheckConstraint(
            "invoice_type IN ('outgoing', 'incoming')",
            name="ck_invoice_type",
        ),
        Index("idx_invoices_tenant_external", "tenant_id", "external_id", unique=True),
        Index("idx_invoices_tenant_version", "tenant_id", Column("data_version").desc()),
        Index("idx_invoices_counterparty", "tenant_id", "counterparty_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid,
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    counterparty_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("umnick.counterparties.id", ondelete="RESTRICT"),
    )
    counterparty_external_id: Mapped[Optional[str]] = mapped_column(String(64))
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("umnick.orders.id", ondelete="SET NULL"),
    )
    order_external_id: Mapped[Optional[str]] = mapped_column(String(64))
    number: Mapped[str] = mapped_column(String(64), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    paid_amount: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    balance: Mapped[Optional[float]] = mapped_column(
        Numeric(16, 2), Computed("amount - paid_amount"),
    )
    status: Mapped[str] = mapped_column(String(32), default="unpaid")
    payment_date: Mapped[Optional[datetime]] = mapped_column(Date)
    invoice_type: Mapped[str] = mapped_column(String(16), default="outgoing")
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    counterparty = relationship("Counterparty", back_populates="invoices")
    order = relationship("Order", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "payment_type IN ('cash', 'cashless', 'card', 'offset', 'other')",
            name="ck_payment_type",
        ),
        CheckConstraint(
            "direction IN ('incoming', 'outgoing')",
            name="ck_payment_direction",
        ),
        Index("idx_payments_tenant_external", "tenant_id", "external_id", unique=True),
        Index("idx_payments_tenant_version", "tenant_id", Column("data_version").desc()),
        Index("idx_payments_counterparty", "tenant_id", "counterparty_id"),
        Index("idx_payments_date", "tenant_id", Column("date").desc()),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid,
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    counterparty_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("umnick.counterparties.id", ondelete="RESTRICT"),
    )
    counterparty_external_id: Mapped[Optional[str]] = mapped_column(String(64))
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("umnick.invoices.id", ondelete="SET NULL"),
    )
    invoice_external_id: Mapped[Optional[str]] = mapped_column(String(64))
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("umnick.orders.id", ondelete="SET NULL"),
    )
    order_external_id: Mapped[Optional[str]] = mapped_column(String(64))
    number: Mapped[Optional[str]] = mapped_column(String(64))
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False)
    paid_amount: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    balance: Mapped[Optional[float]] = mapped_column(
        Numeric(16, 2), Computed("amount - paid_amount"),
    )
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    payment_type: Mapped[str] = mapped_column(String(32), default="cashless")
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    purpose: Mapped[Optional[str]] = mapped_column(Text)
    payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    counterparty = relationship("Counterparty", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payments")
    order = relationship("Order", back_populates="payments")


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'discontinued', 'archived')",
            name="ck_product_status",
        ),
        Index("idx_products_tenant_external", "tenant_id", "external_id", unique=True),
        Index("idx_products_tenant_version", "tenant_id", Column("data_version").desc()),
        Index("idx_products_category", "tenant_id", "category"),
        Index("idx_products_barcode", "tenant_id", "barcode",
              postgresql_where=Column("barcode").is_not(None)),
        Index("idx_products_article", "tenant_id", "article",
              postgresql_where=Column("article").is_not(None)),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid,
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    article: Mapped[Optional[str]] = mapped_column(String(64))
    barcode: Mapped[Optional[str]] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(256))
    unit: Mapped[str] = mapped_column(String(16), default="шт")
    price: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    cost_price: Mapped[Optional[float]] = mapped_column(Numeric(16, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    stock_balance: Mapped[float] = mapped_column(Numeric(16, 3), default=0)
    stock_reserved: Mapped[float] = mapped_column(Numeric(16, 3), default=0)
    min_stock: Mapped[float] = mapped_column(Numeric(16, 3), default=0)
    status: Mapped[str] = mapped_column(String(32), default="active")
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"
    __table_args__ = (
        Index("idx_employees_tenant_external", "tenant_id", "external_id", unique=True),
        Index("idx_employees_tenant_version", "tenant_id", Column("data_version").desc()),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid,
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    position: Mapped[Optional[str]] = mapped_column(String(256))
    email: Mapped[Optional[str]] = mapped_column(String(256))
    phone: Mapped[Optional[str]] = mapped_column(String(64))
    department: Mapped[Optional[str]] = mapped_column(String(256))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)


class SyncLog(Base):
    __tablename__ = "sync_log"
    __table_args__ = (
        CheckConstraint(
            "sync_type IN ('counterparties', 'contracts', 'orders', "
            "'invoices', 'payments', 'products', 'employees', 'full_reconciliation')",
            name="ck_sync_type",
        ),
        CheckConstraint(
            "status IN ('running', 'success', 'error', 'partial')",
            name="ck_sync_status",
        ),
        Index("idx_sync_log_tenant_type", "tenant_id", "sync_type", Column("started_at").desc()),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("umnick.tenants.id"), nullable=False,
    )
    sync_type: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_errors: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )


class Watcher(Base, TimestampMixin):
    __tablename__ = "watchers"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'critical')",
            name="ck_watcher_priority",
        ),
        Index("idx_watchers_tenant_enabled", "tenant_id", "enabled",
              postgresql_where=Column("enabled").is_(True)),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    schedule: Mapped[str] = mapped_column(String(64), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    tool_params: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    condition: Mapped[str] = mapped_column(Text, nullable=False)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    recipients: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    snooze_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_alert_hash: Mapped[Optional[str]] = mapped_column(String(64))
    last_alert_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    alert_count: Mapped[int] = mapped_column(Integer, default=0)
