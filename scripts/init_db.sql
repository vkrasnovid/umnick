-- Primary initialization: create schema and all tables
-- This runs on first container startup (docker-entrypoint-initdb.d)

CREATE SCHEMA IF NOT EXISTS umnick;

-- Tenants
CREATE TABLE IF NOT EXISTS umnick.tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(256) NOT NULL,
    inn             VARCHAR(12),
    contact_email   VARCHAR(256),
    contact_phone   VARCHAR(64),
    odata_url       TEXT NOT NULL,
    odata_db_name   VARCHAR(128),
    odata_username  VARCHAR(128),
    odata_password_enc TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    subscription_tier VARCHAR(16) DEFAULT 'basic'
        CHECK (subscription_tier IN ('basic', 'pro', 'enterprise')),
    sync_enabled    BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Counterparties
CREATE TABLE IF NOT EXISTS umnick.counterparties (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES umnick.tenants(id),
    external_id     VARCHAR(64) NOT NULL,
    data_version    BIGINT NOT NULL DEFAULT 0,
    name            VARCHAR(512) NOT NULL,
    full_name       VARCHAR(1024),
    inn             VARCHAR(12),
    kpp             VARCHAR(9),
    ogrn            VARCHAR(15),
    legal_address   TEXT,
    actual_address  TEXT,
    phone           VARCHAR(64),
    email           VARCHAR(256),
    website         VARCHAR(512),
    counterparty_type VARCHAR(32)
        CHECK (counterparty_type IN ('legal', 'individual', 'foreign')),
    is_client       BOOLEAN DEFAULT FALSE,
    is_supplier     BOOLEAN DEFAULT FALSE,
    is_buyer        BOOLEAN DEFAULT FALSE,
    segment         VARCHAR(64),
    status          VARCHAR(32) DEFAULT 'active'
        CHECK (status IN ('active', 'blocked', 'archived')),
    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, external_id)
);

-- Contracts
CREATE TABLE IF NOT EXISTS umnick.contracts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES umnick.tenants(id),
    external_id     VARCHAR(64) NOT NULL,
    data_version    BIGINT NOT NULL DEFAULT 0,
    counterparty_id UUID REFERENCES umnick.counterparties(id) ON DELETE RESTRICT,
    counterparty_external_id VARCHAR(64),
    number          VARCHAR(64),
    date_start      DATE NOT NULL,
    date_end        DATE,
    amount          NUMERIC(16, 2) DEFAULT 0,
    currency        VARCHAR(3) DEFAULT 'RUB',
    contract_type   VARCHAR(32)
        CHECK (contract_type IN ('sales', 'purchase', 'commission', 'service', 'other')),
    status          VARCHAR(32) DEFAULT 'active'
        CHECK (status IN ('active', 'closed', 'suspended')),
    close_reason    TEXT,
    utilization_sum NUMERIC(16, 2) DEFAULT 0,
    utilization_pct NUMERIC(5, 2) DEFAULT 0,
    last_utilization_date DATE,
    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, external_id)
);

-- Orders
CREATE TABLE IF NOT EXISTS umnick.orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES umnick.tenants(id),
    external_id     VARCHAR(64) NOT NULL,
    data_version    BIGINT NOT NULL DEFAULT 0,
    counterparty_id UUID REFERENCES umnick.counterparties(id) ON DELETE RESTRICT,
    counterparty_external_id VARCHAR(64),
    number          VARCHAR(64) NOT NULL,
    date            DATE NOT NULL,
    amount          NUMERIC(16, 2) NOT NULL DEFAULT 0,
    currency        VARCHAR(3) DEFAULT 'RUB',
    paid_amount     NUMERIC(16, 2) DEFAULT 0,
    status          VARCHAR(32) DEFAULT 'pending'
        CHECK (status IN ('draft', 'pending', 'confirmed', 'shipped', 'completed', 'cancelled')),
    delivery_date   DATE,
    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, external_id)
);

-- Invoices
CREATE TABLE IF NOT EXISTS umnick.invoices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES umnick.tenants(id),
    external_id     VARCHAR(64) NOT NULL,
    data_version    BIGINT NOT NULL DEFAULT 0,
    counterparty_id UUID REFERENCES umnick.counterparties(id) ON DELETE RESTRICT,
    counterparty_external_id VARCHAR(64),
    order_id        UUID REFERENCES umnick.orders(id) ON DELETE SET NULL,
    order_external_id VARCHAR(64),
    number          VARCHAR(64) NOT NULL,
    date            DATE NOT NULL,
    due_date        DATE,
    amount          NUMERIC(16, 2) NOT NULL DEFAULT 0,
    paid_amount     NUMERIC(16, 2) DEFAULT 0,
    balance         NUMERIC(16, 2) GENERATED ALWAYS AS (amount - paid_amount) STORED,
    status          VARCHAR(32) DEFAULT 'unpaid'
        CHECK (status IN ('unpaid', 'partial', 'paid', 'overdue', 'cancelled')),
    payment_date    DATE,
    invoice_type    VARCHAR(16) DEFAULT 'outgoing'
        CHECK (invoice_type IN ('outgoing', 'incoming')),
    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, external_id)
);

-- Payments
CREATE TABLE IF NOT EXISTS umnick.payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES umnick.tenants(id),
    external_id     VARCHAR(64) NOT NULL,
    data_version    BIGINT NOT NULL DEFAULT 0,
    counterparty_id UUID REFERENCES umnick.counterparties(id) ON DELETE RESTRICT,
    counterparty_external_id VARCHAR(64),
    invoice_id      UUID REFERENCES umnick.invoices(id) ON DELETE SET NULL,
    invoice_external_id VARCHAR(64),
    order_id        UUID REFERENCES umnick.orders(id) ON DELETE SET NULL,
    order_external_id VARCHAR(64),
    number          VARCHAR(64),
    date            DATE NOT NULL,
    amount          NUMERIC(16, 2) NOT NULL,
    paid_amount     NUMERIC(16, 2) DEFAULT 0,
    balance         NUMERIC(16, 2) GENERATED ALWAYS AS (amount - paid_amount) STORED,
    currency        VARCHAR(3) DEFAULT 'RUB',
    payment_type    VARCHAR(32) DEFAULT 'cashless'
        CHECK (payment_type IN ('cash', 'cashless', 'card', 'offset', 'other')),
    direction       VARCHAR(16) NOT NULL
        CHECK (direction IN ('incoming', 'outgoing')),
    purpose         TEXT,
    payment_date    TIMESTAMPTZ,
    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, external_id)
);

-- Products
CREATE TABLE IF NOT EXISTS umnick.products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES umnick.tenants(id),
    external_id     VARCHAR(64) NOT NULL,
    data_version    BIGINT NOT NULL DEFAULT 0,
    name            VARCHAR(512) NOT NULL,
    article         VARCHAR(64),
    barcode         VARCHAR(128),
    description     TEXT,
    category        VARCHAR(256),
    unit            VARCHAR(16) DEFAULT 'шт',
    price           NUMERIC(16, 2) DEFAULT 0,
    cost_price      NUMERIC(16, 2),
    currency        VARCHAR(3) DEFAULT 'RUB',
    stock_balance   NUMERIC(16, 3) DEFAULT 0,
    stock_reserved  NUMERIC(16, 3) DEFAULT 0,
    min_stock       NUMERIC(16, 3) DEFAULT 0,
    status          VARCHAR(32) DEFAULT 'active'
        CHECK (status IN ('active', 'discontinued', 'archived')),
    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, external_id)
);

-- Employees
CREATE TABLE IF NOT EXISTS umnick.employees (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES umnick.tenants(id),
    external_id     VARCHAR(64) NOT NULL,
    data_version    BIGINT NOT NULL DEFAULT 0,
    full_name       VARCHAR(256) NOT NULL,
    position        VARCHAR(256),
    email           VARCHAR(256),
    phone           VARCHAR(64),
    department      VARCHAR(256),
    is_active       BOOLEAN DEFAULT TRUE,
    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, external_id)
);

-- SyncLog
CREATE TABLE IF NOT EXISTS umnick.sync_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES umnick.tenants(id),
    sync_type       VARCHAR(32) NOT NULL
        CHECK (sync_type IN (
            'counterparties', 'contracts', 'orders',
            'invoices', 'payments', 'products', 'employees',
            'full_reconciliation'
        )),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    duration_ms     INTEGER,
    status          VARCHAR(16) NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'success', 'error', 'partial')),
    records_processed INTEGER DEFAULT 0,
    records_updated   INTEGER DEFAULT 0,
    records_created   INTEGER DEFAULT 0,
    records_errors    INTEGER DEFAULT 0,
    error_message     TEXT,
    correlation_id    VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Watchers
CREATE TABLE IF NOT EXISTS umnick.watchers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES umnick.tenants(id),
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    schedule        VARCHAR(64) NOT NULL,
    tool_name       VARCHAR(64) NOT NULL,
    tool_params     JSONB DEFAULT '{}'::jsonb,
    condition       TEXT NOT NULL,
    message_template TEXT NOT NULL,
    recipients      TEXT[] NOT NULL DEFAULT '{}',
    priority        VARCHAR(16) DEFAULT 'normal'
        CHECK (priority IN ('low', 'normal', 'high', 'critical')),
    enabled         BOOLEAN DEFAULT TRUE,
    snooze_until    TIMESTAMPTZ,
    last_run_at     TIMESTAMPTZ,
    last_alert_hash VARCHAR(64),
    last_alert_at   TIMESTAMPTZ,
    alert_count     INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, name)
);

-- Indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_counterparties_tenant_external
    ON umnick.counterparties (tenant_id, external_id);
CREATE INDEX IF NOT EXISTS idx_counterparties_tenant_version
    ON umnick.counterparties (tenant_id, data_version DESC);
CREATE INDEX IF NOT EXISTS idx_counterparties_inn
    ON umnick.counterparties (tenant_id, inn) WHERE inn IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_contracts_tenant_external
    ON umnick.contracts (tenant_id, external_id);
CREATE INDEX IF NOT EXISTS idx_contracts_tenant_version
    ON umnick.contracts (tenant_id, data_version DESC);
CREATE INDEX IF NOT EXISTS idx_contracts_counterparty
    ON umnick.contracts (tenant_id, counterparty_id);
CREATE INDEX IF NOT EXISTS idx_contracts_status
    ON umnick.contracts (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_contracts_date_end
    ON umnick.contracts (tenant_id, date_end) WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_orders_tenant_external
    ON umnick.orders (tenant_id, external_id);
CREATE INDEX IF NOT EXISTS idx_orders_tenant_version
    ON umnick.orders (tenant_id, data_version DESC);
CREATE INDEX IF NOT EXISTS idx_orders_counterparty
    ON umnick.orders (tenant_id, counterparty_id);
CREATE INDEX IF NOT EXISTS idx_orders_date
    ON umnick.orders (tenant_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status
    ON umnick.orders (tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_invoices_tenant_external
    ON umnick.invoices (tenant_id, external_id);
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_version
    ON umnick.invoices (tenant_id, data_version DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_counterparty
    ON umnick.invoices (tenant_id, counterparty_id);
CREATE INDEX IF NOT EXISTS idx_invoices_due_overdue
    ON umnick.invoices (tenant_id, due_date, status) WHERE status IN ('unpaid', 'partial');
CREATE INDEX IF NOT EXISTS idx_invoices_balance
    ON umnick.invoices (tenant_id, (amount - paid_amount)) WHERE (amount - paid_amount) > 0;

CREATE INDEX IF NOT EXISTS idx_payments_tenant_external
    ON umnick.payments (tenant_id, external_id);
CREATE INDEX IF NOT EXISTS idx_payments_tenant_version
    ON umnick.payments (tenant_id, data_version DESC);
CREATE INDEX IF NOT EXISTS idx_payments_counterparty
    ON umnick.payments (tenant_id, counterparty_id);
CREATE INDEX IF NOT EXISTS idx_payments_date
    ON umnick.payments (tenant_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_payments_invoice
    ON umnick.payments (tenant_id, invoice_id) WHERE invoice_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_products_tenant_external
    ON umnick.products (tenant_id, external_id);
CREATE INDEX IF NOT EXISTS idx_products_tenant_version
    ON umnick.products (tenant_id, data_version DESC);
CREATE INDEX IF NOT EXISTS idx_products_category
    ON umnick.products (tenant_id, category);
CREATE INDEX IF NOT EXISTS idx_products_low_stock
    ON umnick.products (tenant_id, (stock_balance - stock_reserved))
    WHERE (stock_balance - stock_reserved) <= min_stock AND status = 'active';
CREATE INDEX IF NOT EXISTS idx_products_barcode
    ON umnick.products (tenant_id, barcode) WHERE barcode IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_article
    ON umnick.products (tenant_id, article) WHERE article IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_employees_tenant_external
    ON umnick.employees (tenant_id, external_id);
CREATE INDEX IF NOT EXISTS idx_employees_tenant_version
    ON umnick.employees (tenant_id, data_version DESC);

CREATE INDEX IF NOT EXISTS idx_sync_log_tenant_type
    ON umnick.sync_log (tenant_id, sync_type, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_log_tenant_failed
    ON umnick.sync_log (tenant_id, started_at DESC) WHERE status = 'error';

CREATE INDEX IF NOT EXISTS idx_watchers_tenant_enabled
    ON umnick.watchers (tenant_id, enabled)
    WHERE enabled = TRUE AND (snooze_until IS NULL OR snooze_until < NOW());

-- Row Level Security
ALTER TABLE umnick.counterparties ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.sync_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.watchers ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON umnick.counterparties
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY tenant_isolation ON umnick.contracts
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY tenant_isolation ON umnick.orders
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY tenant_isolation ON umnick.invoices
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY tenant_isolation ON umnick.payments
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY tenant_isolation ON umnick.products
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY tenant_isolation ON umnick.employees
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY tenant_isolation ON umnick.sync_log
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY tenant_isolation ON umnick.watchers
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
