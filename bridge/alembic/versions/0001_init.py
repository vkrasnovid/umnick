"""empty message

Revision ID: 0001_init
Revises:
Create Date: 2026-04-28 21:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create schema
    op.execute("CREATE SCHEMA IF NOT EXISTS umnick")

    # Create ENUM-like check constraints via domain types omitted for simplicity
    # Use CHECK constraints directly

    # Tenants
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("inn", sa.String(12)),
        sa.Column("contact_email", sa.String(256)),
        sa.Column("contact_phone", sa.String(64)),
        sa.Column("odata_url", sa.Text, nullable=False),
        sa.Column("odata_db_name", sa.String(128)),
        sa.Column("odata_username", sa.String(128)),
        sa.Column("odata_password_enc", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("TRUE")),
        sa.Column("subscription_tier", sa.String(16), server_default=sa.text("'basic'::character varying")),
        sa.Column("sync_enabled", sa.Boolean, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("subscription_tier IN ('basic', 'pro', 'enterprise')", name="ck_tenants_tier"),
        schema="umnick",
    )

    # Counterparties
    op.create_table(
        "counterparties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.tenants.id"), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("data_version", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("full_name", sa.String(1024)),
        sa.Column("inn", sa.String(12)),
        sa.Column("kpp", sa.String(9)),
        sa.Column("ogrn", sa.String(15)),
        sa.Column("legal_address", sa.Text),
        sa.Column("actual_address", sa.Text),
        sa.Column("phone", sa.String(64)),
        sa.Column("email", sa.String(256)),
        sa.Column("website", sa.String(512)),
        sa.Column("counterparty_type", sa.String(32)),
        sa.Column("is_client", sa.Boolean, server_default=sa.text("FALSE")),
        sa.Column("is_supplier", sa.Boolean, server_default=sa.text("FALSE")),
        sa.Column("is_buyer", sa.Boolean, server_default=sa.text("FALSE")),
        sa.Column("segment", sa.String(64)),
        sa.Column("status", sa.String(32), server_default=sa.text("'active'::character varying")),
        sa.Column("raw_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("counterparty_type IN ('legal', 'individual', 'foreign')", name="ck_cp_type"),
        sa.CheckConstraint("status IN ('active', 'blocked', 'archived')", name="ck_cp_status"),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_counterparties_tenant_external"),
        schema="umnick",
    )

    # Contracts
    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.tenants.id"), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("data_version", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("counterparty_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.counterparties.id", ondelete="RESTRICT")),
        sa.Column("counterparty_external_id", sa.String(64)),
        sa.Column("number", sa.String(64)),
        sa.Column("date_start", sa.Date, nullable=False),
        sa.Column("date_end", sa.Date),
        sa.Column("amount", sa.Numeric(16, 2), server_default=sa.text("0")),
        sa.Column("currency", sa.String(3), server_default=sa.text("'RUB'::character varying")),
        sa.Column("contract_type", sa.String(32)),
        sa.Column("status", sa.String(32), server_default=sa.text("'active'::character varying")),
        sa.Column("close_reason", sa.Text),
        sa.Column("utilization_sum", sa.Numeric(16, 2), server_default=sa.text("0")),
        sa.Column("utilization_pct", sa.Numeric(5, 2), server_default=sa.text("0")),
        sa.Column("last_utilization_date", sa.Date),
        sa.Column("raw_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("contract_type IN ('sales', 'purchase', 'commission', 'service', 'other')",
                           name="ck_contract_type"),
        sa.CheckConstraint("status IN ('active', 'closed', 'suspended')", name="ck_contract_status"),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_contracts_tenant_external"),
        schema="umnick",
    )

    # Orders
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.tenants.id"), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("data_version", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("counterparty_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.counterparties.id", ondelete="RESTRICT")),
        sa.Column("counterparty_external_id", sa.String(64)),
        sa.Column("number", sa.String(64), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("currency", sa.String(3), server_default=sa.text("'RUB'::character varying")),
        sa.Column("paid_amount", sa.Numeric(16, 2), server_default=sa.text("0")),
        sa.Column("status", sa.String(32), server_default=sa.text("'pending'::character varying")),
        sa.Column("delivery_date", sa.Date),
        sa.Column("raw_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'pending', 'confirmed', 'shipped', 'completed', 'cancelled')",
            name="ck_order_status",
        ),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_orders_tenant_external"),
        schema="umnick",
    )

    # Invoices
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.tenants.id"), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("data_version", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("counterparty_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.counterparties.id", ondelete="RESTRICT")),
        sa.Column("counterparty_external_id", sa.String(64)),
        sa.Column("order_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.orders.id", ondelete="SET NULL")),
        sa.Column("order_external_id", sa.String(64)),
        sa.Column("number", sa.String(64), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("due_date", sa.Date),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("paid_amount", sa.Numeric(16, 2), server_default=sa.text("0")),
        sa.Column("status", sa.String(32), server_default=sa.text("'unpaid'::character varying")),
        sa.Column("payment_date", sa.Date),
        sa.Column("invoice_type", sa.String(16), server_default=sa.text("'outgoing'::character varying")),
        sa.Column("raw_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("status IN ('unpaid', 'partial', 'paid', 'overdue', 'cancelled')",
                           name="ck_invoice_status"),
        sa.CheckConstraint("invoice_type IN ('outgoing', 'incoming')", name="ck_invoice_type"),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_invoices_tenant_external"),
        schema="umnick",
    )

    # Payments
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.tenants.id"), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("data_version", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("counterparty_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.counterparties.id", ondelete="RESTRICT")),
        sa.Column("counterparty_external_id", sa.String(64)),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.invoices.id", ondelete="SET NULL")),
        sa.Column("invoice_external_id", sa.String(64)),
        sa.Column("order_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.orders.id", ondelete="SET NULL")),
        sa.Column("order_external_id", sa.String(64)),
        sa.Column("number", sa.String(64)),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default=sa.text("'RUB'::character varying")),
        sa.Column("payment_type", sa.String(32), server_default=sa.text("'cashless'::character varying")),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("purpose", sa.Text),
        sa.Column("payment_date", sa.DateTime(timezone=True)),
        sa.Column("raw_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("payment_type IN ('cash', 'cashless', 'card', 'offset', 'other')",
                           name="ck_payment_type"),
        sa.CheckConstraint("direction IN ('incoming', 'outgoing')", name="ck_payment_direction"),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_payments_tenant_external"),
        schema="umnick",
    )

    # Products
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.tenants.id"), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("data_version", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("article", sa.String(64)),
        sa.Column("barcode", sa.String(128)),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.String(256)),
        sa.Column("unit", sa.String(16), server_default=sa.text("'шт'::character varying")),
        sa.Column("price", sa.Numeric(16, 2), server_default=sa.text("0")),
        sa.Column("cost_price", sa.Numeric(16, 2)),
        sa.Column("currency", sa.String(3), server_default=sa.text("'RUB'::character varying")),
        sa.Column("stock_balance", sa.Numeric(16, 3), server_default=sa.text("0")),
        sa.Column("stock_reserved", sa.Numeric(16, 3), server_default=sa.text("0")),
        sa.Column("min_stock", sa.Numeric(16, 3), server_default=sa.text("0")),
        sa.Column("status", sa.String(32), server_default=sa.text("'active'::character varying")),
        sa.Column("raw_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("status IN ('active', 'discontinued', 'archived')", name="ck_product_status"),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_products_tenant_external"),
        schema="umnick",
    )

    # Employees
    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.tenants.id"), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("data_version", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column("position", sa.String(256)),
        sa.Column("email", sa.String(256)),
        sa.Column("phone", sa.String(64)),
        sa.Column("department", sa.String(256)),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("TRUE")),
        sa.Column("raw_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_employees_tenant_external"),
        schema="umnick",
    )

    # SyncLog
    op.create_table(
        "sync_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.tenants.id"), nullable=False),
        sa.Column("sync_type", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'running'::character varying")),
        sa.Column("records_processed", sa.Integer, server_default=sa.text("0")),
        sa.Column("records_updated", sa.Integer, server_default=sa.text("0")),
        sa.Column("records_created", sa.Integer, server_default=sa.text("0")),
        sa.Column("records_errors", sa.Integer, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text),
        sa.Column("correlation_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(
            "sync_type IN ('counterparties', 'contracts', 'orders', "
            "'invoices', 'payments', 'products', 'employees', 'full_reconciliation')",
            name="ck_sync_type",
        ),
        sa.CheckConstraint("status IN ('running', 'success', 'error', 'partial')", name="ck_sync_status"),
        schema="umnick",
    )

    # Watchers
    op.create_table(
        "watchers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("umnick.tenants.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("schedule", sa.String(64), nullable=False),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("tool_params", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("condition", sa.Text, nullable=False),
        sa.Column("message_template", sa.Text, nullable=False),
        sa.Column("recipients", postgresql.ARRAY(sa.Text), server_default=sa.text("'{}'::text[]")),
        sa.Column("priority", sa.String(16), server_default=sa.text("'normal'::character varying")),
        sa.Column("enabled", sa.Boolean, server_default=sa.text("TRUE")),
        sa.Column("snooze_until", sa.DateTime(timezone=True)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_alert_hash", sa.String(64)),
        sa.Column("last_alert_at", sa.DateTime(timezone=True)),
        sa.Column("alert_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("priority IN ('low', 'normal', 'high', 'critical')", name="ck_watcher_priority"),
        schema="umnick",
    )

    # Create indexes
    op.create_index("idx_counterparties_tenant_version", "counterparties",
                    ["tenant_id", sa.text("data_version DESC")], schema="umnick")
    op.create_index("idx_counterparties_inn", "counterparties",
                    ["tenant_id", "inn"], postgresql_where=sa.text("inn IS NOT NULL"), schema="umnick")

    op.create_index("idx_contracts_tenant_version", "contracts",
                    ["tenant_id", sa.text("data_version DESC")], schema="umnick")
    op.create_index("idx_contracts_counterparty", "contracts",
                    ["tenant_id", "counterparty_id"], schema="umnick")
    op.create_index("idx_contracts_status", "contracts",
                    ["tenant_id", "status"], schema="umnick")
    op.create_index("idx_contracts_date_end", "contracts",
                    ["tenant_id", "date_end"], postgresql_where=sa.text("status = 'active'"), schema="umnick")

    op.create_index("idx_orders_tenant_version", "orders",
                    ["tenant_id", sa.text("data_version DESC")], schema="umnick")
    op.create_index("idx_orders_counterparty", "orders",
                    ["tenant_id", "counterparty_id"], schema="umnick")
    op.create_index("idx_orders_date", "orders",
                    ["tenant_id", sa.text("date DESC")], schema="umnick")
    op.create_index("idx_orders_status", "orders",
                    ["tenant_id", "status"], schema="umnick")

    op.create_index("idx_invoices_tenant_version", "invoices",
                    ["tenant_id", sa.text("data_version DESC")], schema="umnick")
    op.create_index("idx_invoices_counterparty", "invoices",
                    ["tenant_id", "counterparty_id"], schema="umnick")
    op.create_index("idx_invoices_due_overdue", "invoices",
                    ["tenant_id", "due_date", "status"],
                    postgresql_where=sa.text("status IN ('unpaid', 'partial')"), schema="umnick")

    op.create_index("idx_payments_tenant_version", "payments",
                    ["tenant_id", sa.text("data_version DESC")], schema="umnick")
    op.create_index("idx_payments_counterparty", "payments",
                    ["tenant_id", "counterparty_id"], schema="umnick")
    op.create_index("idx_payments_date", "payments",
                    ["tenant_id", sa.text("date DESC")], schema="umnick")

    op.create_index("idx_products_tenant_version", "products",
                    ["tenant_id", sa.text("data_version DESC")], schema="umnick")
    op.create_index("idx_products_category", "products",
                    ["tenant_id", "category"], schema="umnick")
    op.create_index("idx_products_barcode", "products",
                    ["tenant_id", "barcode"], postgresql_where=sa.text("barcode IS NOT NULL"), schema="umnick")
    op.create_index("idx_products_article", "products",
                    ["tenant_id", "article"], postgresql_where=sa.text("article IS NOT NULL"), schema="umnick")

    op.create_index("idx_employees_tenant_version", "employees",
                    ["tenant_id", sa.text("data_version DESC")], schema="umnick")

    op.create_index("idx_sync_log_tenant_type", "sync_log",
                    ["tenant_id", "sync_type", sa.text("started_at DESC")], schema="umnick")

    op.create_index("idx_watchers_tenant_enabled", "watchers",
                    ["tenant_id", "enabled"],
                    postgresql_where=sa.text("enabled = TRUE"), schema="umnick")


def downgrade() -> None:
    op.drop_table("watchers", schema="umnick")
    op.drop_table("sync_log", schema="umnick")
    op.drop_table("employees", schema="umnick")
    op.drop_table("products", schema="umnick")
    op.drop_table("payments", schema="umnick")
    op.drop_table("invoices", schema="umnick")
    op.drop_table("orders", schema="umnick")
    op.drop_table("contracts", schema="umnick")
    op.drop_table("counterparties", schema="umnick")
    op.drop_table("tenants", schema="umnick")
