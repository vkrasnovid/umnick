# Умник — AI Operations Platform Architecture

> **Version:** 1.0 (MVP)
> **Last updated:** 2026-04-28
> **Status:** Draft — ready for development

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Bridge — Integration & Storage](#2-data-bridge--integration--storage)
3. [Tool Library — API Contracts](#3-tool-library--api-contracts)
4. [OpenClaw Plugin Schema](#4-openclaw-plugin-schema)
5. [Proactive Engine — Watchers](#5-proactive-engine--watchers)
6. [Conversational Layer](#6-conversational-layer)
7. [Admin UI](#7-admin-ui)
8. [Project Structure](#8-project-structure)
9. [Multi-tenant Contract](#9-multi-tenant-contract)
10. [Security](#10-security)
11. [OpenTelemetry & Monitoring](#11-opentelemetry--monitoring)
12. [Decision Log](#12-decision-log)

---

## 1. Architecture Overview

### Four-Layer Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   👤 Conversational Interface                 │
│               (Telegram Bot — OpenClaw Agent)                 │
│                                                              │
│  User → Telegram → OpenClaw Agent → Tool Plugin → Response │
└──────────────────────────────────┬───────────────────────────┘
                                   │
┌──────────────────────────────────▼───────────────────────────┐
│               🔧 Tool Library                                 │
│    (7 tools: Python/TypeScript, SQL, бизнес-логика)           │
│                                                              │
│  get_contract_utilization  │  get_overdue_payments           │
│  get_client_activity      │  query_sales                    │
│  find_contracts           │  get_client_360                 │
│  list_active_clients      │                                  │
└──────────────────────────────────┬───────────────────────────┘
                                   │
┌──────────────────────────────────▼───────────────────────────┐
│           ⏰ Proactive Engine                                 │
│         (Celery Beat — Watcher Scheduler)                     │
│                                                              │
│  Watcher  │  Schedule  │  Condition  │  Alert                 │
│  ───────────────────────────────────────────────────         │
│  Deals    │  daily@9am │ overdue>0    │ 🚨 N overdue          │
│  LowStock │  hourly    │ stock<10    │ ⚠️ Product X low       │
│  Revenue  │  weekly    │ drop>20%    │ 📊 Revenue alert       │
└──────────────────────────────────┬───────────────────────────┘
                                   │
┌──────────────────────────────────▼───────────────────────────┐
│          🏗️ Data Bridge                                       │
│     (FastAPI + Celery + PostgreSQL + OData Client)            │
│                                                              │
│  1С Enterprise  ◄──OData──►  Sync Worker  ──►  PostgreSQL  │
│  (КА2 / УТ / БП)                 │                            │
│                           Webhook (v2)                        │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
                      ┌─────────────┐
                      │   1С КА2    │
                      │  (OData)    │
                      └──────┬──────┘
                             │ pull (5min / 15min / 1h / 24h)
                             ▼
┌────────────────────────────────────────────────────────────┐
│                     Data Bridge                              │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Sync Workers (Celery tasks)                       │     │
│  │  - OrdersSync:    every 5 min                      │     │
│  │  - ContractsSync:  every 15 min                    │     │
│  │  - DictSync:       every 60 min                    │     │
│  │  - FullReconcile:  daily at 02:00                  │     │
│  └──────────────┬─────────────────────────────────────┘     │
│                 │                                           │
│                 ▼                                           │
│  ┌────────────────────────────────────────────────────┐     │
│  │  PostgreSQL — Unified Data Model (multi-tenant)    │     │
│  │  Схема: umnick (вся бизнес-логика)                 │     │
│  └──────────────┬─────────────────────────────────────┘     │
└─────────────────┼──────────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌─────────┐ ┌─────────┐ ┌──────────────┐
│  Tool   │ │Proactive│ │   Admin UI   │
│ Library │ │ Engine  │ │  (FastAPI)   │
└────┬────┘ └────┬────┘ └──────┬───────┘
     │           │             │
     └───────────┼─────────────┘
                 ▼
        ┌─────────────────┐
        │  OpenClaw Agent │
        │  (Conversation) │
        └────────┬────────┘
                 │
                 ▼
            ┌──────────┐
            │ Telegram │
            └──────────┘
```

### Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| **Data Bridge** | Python 3.12, FastAPI, Celery, SQLAlchemy 2.0, PostgreSQL 16 | SMB-проверено, мощная экосистема интеграций, Celery — стандарт для фоновых задач |
| **Tool Library** | Python 3.12 + SQLAlchemy + parametrized SQL | Tools = бизнес-логика, ближе к данным, минимизируем latency |
| **Proactive Engine** | Celery Beat + Redis (broker) | Встроенный scheduler, debouncing через хэши, snooze через БД |
| **Conversational** | OpenClaw Agent (plugin model) | Multi-provider LLM, росси hosting (YandexGPT/GigaChat), tools-first архитектура |
| **Admin UI** | React 18 + shadcn/ui + Tailwind + Vite | Быстрый старт, компоненты высокого качества, небольшой bundle |
| **Infrastructure** | Docker Compose | Минимум DevOps, воспроизводимость |
| **Monitoring** | OpenTelemetry + JSON logs | Lock-in-free, стандарт индустрии |
| **Localization** | Python gettext / i18n files | RU-first, готовность к многоязычности |
| **Secrets** | AES-256-GCM (encrypted at rest in DB) | OData credentials — не plaintext |
| **Message Queue** | Redis 7 | Celery default, достаточно для SMB-нагрузки |

---

## 2. Data Bridge — Integration & Storage

### 2.1 PostgreSQL Schema

#### Schema: `umnick`

> Все таблицы включают поля: `tenant_id UUID NOT NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`.
> Первичные ключи — `UUID` (генерируются на стороне приложения через `uuid7()` для упрощения шардинга в будущем).

#### 🔹 counterparties

```sql
CREATE TABLE umnick.counterparties (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    external_id     VARCHAR(64) NOT NULL,       -- ID контрагента в 1С
    data_version    BIGINT NOT NULL DEFAULT 0,   -- монотонный счётчик версии (timestamp из 1С)

    -- Основные реквизиты
    name            VARCHAR(512) NOT NULL,       -- Наименование
    full_name       VARCHAR(1024),               -- Полное наименование
    inn             VARCHAR(12),                 -- ИНН
    kpp             VARCHAR(9),                  -- КПП
    ogrn            VARCHAR(15),                 -- ОГРН
    legal_address   TEXT,                        -- Юридический адрес
    actual_address  TEXT,                        -- Фактический адрес

    -- Контакты
    phone           VARCHAR(64),
    email           VARCHAR(256),
    website         VARCHAR(512),

    -- Категоризация
    counterparty_type VARCHAR(32)                -- 'legal' | 'individual' | 'foreign'
        CHECK (counterparty_type IN ('legal', 'individual', 'foreign')),
    is_client       BOOLEAN DEFAULT FALSE,
    is_supplier     BOOLEAN DEFAULT FALSE,
    is_buyer        BOOLEAN DEFAULT FALSE,
    segment         VARCHAR(64),                 -- 'retail' | 'wholesale' | 'vip' | etc
    status          VARCHAR(32) DEFAULT 'active'
        CHECK (status IN ('active', 'blocked', 'archived')),

    -- Сырые данные от 1С (на случай расширения)
    raw_data        JSONB,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE UNIQUE INDEX idx_counterparties_tenant_external
    ON umnick.counterparties (tenant_id, external_id);
CREATE INDEX idx_counterparties_tenant_version
    ON umnick.counterparties (tenant_id, data_version DESC);
CREATE INDEX idx_counterparties_inn
    ON umnick.counterparties (tenant_id, inn) WHERE inn IS NOT NULL;
CREATE INDEX idx_counterparties_name_search
    ON umnick.counterparties USING gin (to_tsvector('russian', name));
```

**Mapping КА2 → counterparties:**

| Поле КА2 (OData) | Поле в БД | Примечание |
|---|---|---|
| `Ref_Key` | `external_id` | Уникальный GUID в 1С |
| `Description` | `name` | Краткое наименование |
| `FullDescription` | `full_name` | Полное наименование |
| `INN` | `inn` | ИНН |
| `KPP` | `kpp` | КПП |
| `OGRN` | `ogrn` | ОГРН |
| `JuridicalAddress` | `legal_address` | Представление адреса (строка) |
| `ActualAddress` | `actual_address` | Представление адреса (строка) |
| `Phone` | `phone` | Телефон |
| `Email` | `email` | Email |
| `InternetAddress_Presentation` | `website` | Сайт |
| `IsBuyer` | `is_buyer` | Признак покупателя |
| `IsSupplier` | `is_supplier` | Признак поставщика |
| `Date_Time` | `data_version` | Unix timestamp изменения |

#### 🔹 contracts

```sql
CREATE TABLE umnick.contracts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    external_id     VARCHAR(64) NOT NULL,
    data_version    BIGINT NOT NULL DEFAULT 0,

    -- Связи
    counterparty_id UUID REFERENCES umnick.counterparties(id) ON DELETE RESTRICT,
    counterparty_external_id VARCHAR(64),        -- для скорости sync без JOIN

    -- Реквизиты договора
    number          VARCHAR(64),                 -- Номер договора
    date_start      DATE NOT NULL,               -- Дата начала
    date_end        DATE,                        -- Дата окончания
    amount          NUMERIC(16, 2) DEFAULT 0,    -- Сумма договора
    currency        VARCHAR(3) DEFAULT 'RUB',

    -- Статус и тип
    contract_type   VARCHAR(32)                  -- 'sales' | 'purchase' | 'commission' | 'service'
        CHECK (contract_type IN ('sales', 'purchase', 'commission', 'service', 'other')),
    status          VARCHAR(32) DEFAULT 'active'
        CHECK (status IN ('active', 'closed', 'suspended')),
    close_reason    TEXT,

    -- Исполнение
    utilization_sum NUMERIC(16, 2) DEFAULT 0,    -- Сумма исполнения
    utilization_pct NUMERIC(5, 2) DEFAULT 0,     -- Процент исполнения (вычисляется)
    last_utilization_date DATE,

    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_contracts_tenant_external
    ON umnick.contracts (tenant_id, external_id);
CREATE INDEX idx_contracts_tenant_version
    ON umnick.contracts (tenant_id, data_version DESC);
CREATE INDEX idx_contracts_counterparty
    ON umnick.contracts (tenant_id, counterparty_id);
CREATE INDEX idx_contracts_status
    ON umnick.contracts (tenant_id, status);
CREATE INDEX idx_contracts_date_end
    ON umnick.contracts (tenant_id, date_end) WHERE status = 'active';
```

**Mapping КА2 → contracts:**

| Поле КА2 | Поле в БД | Примечание |
|---|---|---|
| `Ref_Key` | `external_id` | GUID договора |
| `Description` | `number` | Номер договора |
| `StartDate` | `date_start` | Дата начала |
| `FinishDate` | `date_end` | Дата окончания |
| `Amount` | `amount` | Сумма |
| `Currency` | `currency` | Код валюты |
| `ОрганизацияВзаиморасчетов_Key` | — | → в `counterparty_external_id` через resolve |
| `Date_Time` | `data_version` | Версия |

#### 🔹 orders

```sql
CREATE TABLE umnick.orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    external_id     VARCHAR(64) NOT NULL,
    data_version    BIGINT NOT NULL DEFAULT 0,

    -- Связи
    counterparty_id UUID REFERENCES umnick.counterparties(id) ON DELETE RESTRICT,
    counterparty_external_id VARCHAR(64),

    -- Реквизиты заказа
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
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_orders_tenant_external
    ON umnick.orders (tenant_id, external_id);
CREATE INDEX idx_orders_tenant_version
    ON umnick.orders (tenant_id, data_version DESC);
CREATE INDEX idx_orders_counterparty
    ON umnick.orders (tenant_id, counterparty_id);
CREATE INDEX idx_orders_date
    ON umnick.orders (tenant_id, date DESC);
CREATE INDEX idx_orders_status
    ON umnick.orders (tenant_id, status);
CREATE INDEX idx_orders_delivery_overdue
    ON umnick.orders (tenant_id, delivery_date)
    WHERE status NOT IN ('completed', 'cancelled') AND delivery_date IS NOT NULL;
```

#### 🔹 invoices

```sql
CREATE TABLE umnick.invoices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    external_id     VARCHAR(64) NOT NULL,
    data_version    BIGINT NOT NULL DEFAULT 0,

    -- Связи
    counterparty_id     UUID REFERENCES umnick.counterparties(id) ON DELETE RESTRICT,
    counterparty_external_id VARCHAR(64),
    order_id            UUID REFERENCES umnick.orders(id) ON DELETE SET NULL,
    order_external_id   VARCHAR(64),

    -- Реквизиты счёта
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
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_invoices_tenant_external
    ON umnick.invoices (tenant_id, external_id);
CREATE INDEX idx_invoices_tenant_version
    ON umnick.invoices (tenant_id, data_version DESC);
CREATE INDEX idx_invoices_counterparty
    ON umnick.invoices (tenant_id, counterparty_id);
CREATE INDEX idx_invoices_due_overdue
    ON umnick.invoices (tenant_id, due_date, status)
    WHERE status IN ('unpaid', 'partial');
CREATE INDEX idx_invoices_balance
    ON umnick.invoices (tenant_id, balance)
    WHERE balance > 0;
```

#### 🔹 payments

```sql
CREATE TABLE umnick.payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    external_id     VARCHAR(64) NOT NULL,
    data_version    BIGINT NOT NULL DEFAULT 0,

    -- Связи
    counterparty_id     UUID REFERENCES umnick.counterparties(id) ON DELETE RESTRICT,
    counterparty_external_id VARCHAR(64),
    invoice_id          UUID REFERENCES umnick.invoices(id) ON DELETE SET NULL,
    invoice_external_id VARCHAR(64),
    order_id            UUID REFERENCES umnick.orders(id) ON DELETE SET NULL,
    order_external_id   VARCHAR(64),

    -- Реквизиты платежа
    number          VARCHAR(64),
    date            DATE NOT NULL,
    amount          NUMERIC(16, 2) NOT NULL,
    currency        VARCHAR(3) DEFAULT 'RUB',
    payment_type    VARCHAR(32) DEFAULT 'cashless'
        CHECK (payment_type IN ('cash', 'cashless', 'card', 'offset', 'other')),
    direction       VARCHAR(16) NOT NULL
        CHECK (direction IN ('incoming', 'outgoing')),
    purpose         TEXT,                        -- Назначение платежа
    payment_date    TIMESTAMPTZ,

    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_payments_tenant_external
    ON umnick.payments (tenant_id, external_id);
CREATE INDEX idx_payments_tenant_version
    ON umnick.payments (tenant_id, data_version DESC);
CREATE INDEX idx_payments_counterparty
    ON umnick.payments (tenant_id, counterparty_id);
CREATE INDEX idx_payments_date
    ON umnick.payments (tenant_id, date DESC);
CREATE INDEX idx_payments_invoice
    ON umnick.payments (tenant_id, invoice_id) WHERE invoice_id IS NOT NULL;
```

#### 🔹 products

```sql
CREATE TABLE umnick.products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    external_id     VARCHAR(64) NOT NULL,
    data_version    BIGINT NOT NULL DEFAULT 0,

    -- Основные реквизиты
    name            VARCHAR(512) NOT NULL,
    article         VARCHAR(64),
    barcode         VARCHAR(128),
    description     TEXT,
    category        VARCHAR(256),
    unit            VARCHAR(16) DEFAULT 'шт',

    -- Цены и остатки
    price           NUMERIC(16, 2) DEFAULT 0,
    cost_price      NUMERIC(16, 2),              -- Себестоимость
    currency        VARCHAR(3) DEFAULT 'RUB',
    stock_balance   NUMERIC(16, 3) DEFAULT 0,    -- Текущий остаток
    stock_reserved  NUMERIC(16, 3) DEFAULT 0,    -- Зарезервировано
    stock_available NUMERIC(16, 3) GENERATED ALWAYS AS (stock_balance - stock_reserved) STORED,
    min_stock       NUMERIC(16, 3) DEFAULT 0,    -- Минимальный запас

    status          VARCHAR(32) DEFAULT 'active'
        CHECK (status IN ('active', 'discontinued', 'archived')),

    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_products_tenant_external
    ON umnick.products (tenant_id, external_id);
CREATE INDEX idx_products_tenant_version
    ON umnick.products (tenant_id, data_version DESC);
CREATE INDEX idx_products_category
    ON umnick.products (tenant_id, category);
CREATE INDEX idx_products_low_stock
    ON umnick.products (tenant_id, stock_available)
    WHERE stock_available <= min_stock AND status = 'active';
CREATE INDEX idx_products_barcode
    ON umnick.products (tenant_id, barcode) WHERE barcode IS NOT NULL;
CREATE INDEX idx_products_article
    ON umnick.products (tenant_id, article) WHERE article IS NOT NULL;
CREATE INDEX idx_products_name_search
    ON umnick.products USING gin (to_tsvector('russian', name));
```

#### 🔹 employees

```sql
CREATE TABLE umnick.employees (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
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
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_employees_tenant_external
    ON umnick.employees (tenant_id, external_id);
CREATE INDEX idx_employees_tenant_version
    ON umnick.employees (tenant_id, data_version DESC);
```

#### 🔹 sync_log

```sql
CREATE TABLE umnick.sync_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,

    -- Тип синхронизации
    sync_type       VARCHAR(32) NOT NULL
        CHECK (sync_type IN (
            'counterparties', 'contracts', 'orders',
            'invoices', 'payments', 'products', 'employees',
            'full_reconciliation'
        )),

    -- Хронология
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    duration_ms     INTEGER,

    -- Результат
    status          VARCHAR(16) NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'success', 'error', 'partial')),
    records_processed INTEGER DEFAULT 0,
    records_updated   INTEGER DEFAULT 0,
    records_created   INTEGER DEFAULT 0,
    records_errors    INTEGER DEFAULT 0,
    error_message     TEXT,
    correlation_id    VARCHAR(64),               -- для трассировки

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sync_log_tenant_type
    ON umnick.sync_log (tenant_id, sync_type, started_at DESC);
CREATE INDEX idx_sync_log_tenant_failed
    ON umnick.sync_log (tenant_id, started_at DESC)
    WHERE status = 'error';
```

#### 🔹 tenants

```sql
CREATE TABLE umnick.tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Данные клиента
    name            VARCHAR(256) NOT NULL,
    inn             VARCHAR(12),
    contact_email   VARCHAR(256),
    contact_phone   VARCHAR(64),

    -- Подключение к 1С
    odata_url       TEXT NOT NULL,               -- https://server/db/odata/standard.odata
    odata_db_name   VARCHAR(128),                -- Имя базы 1С
    odata_username  VARCHAR(128),
    odata_password_enc TEXT,                     -- AES-256-GCM encrypted

    -- Статус
    is_active       BOOLEAN DEFAULT TRUE,
    subscription_tier VARCHAR(16) DEFAULT 'basic'
        CHECK (subscription_tier IN ('basic', 'pro', 'enterprise')),
    sync_enabled    BOOLEAN DEFAULT TRUE,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2.2 Sync Strategy

| Entity | Interval | Query Pattern | Notes |
|--------|----------|---------------|-------|
| Orders | 5 min | `DateTime >= :last_sync AND DateTime < :now` | Часто меняются статусы |
| Invoices | 5 min | Same as orders | Привязаны к заказам |
| Payments | 5 min | Same as orders | Новые платежи |
| Contracts | 15 min | Same pattern | Меняются реже |
| Counterparties | 15 min | Same pattern | Почти статичные |
| Products | 60 min | Same pattern | Номенклатура |
| Employees | 60 min | Same pattern | Кадры |
| Full reconcile | Daily 02:00 | Full dump + diff | Сверка |

**Incremental sync algorithm:**
1. Get `max(data_version)` for entity from PostgreSQL per tenant
2. Query OData: `$filter=DateTime gt <max_version>`
3. UPSERT each record (`external_id + tenant_id` unique)
4. Update `sync_log` with results
5. On error: retry 3 times with exponential backoff, then alert

### 2.3 OData Client Configuration

```python
# bridge/odata_client.py — пример конфигурации
ODATA_CONFIG = {
    "counterparties": {
        "entity_set": "Catalog_Контрагенты",
        "select": "Ref_Key,Description,FullDescription,INN,KPP,OGRN,"
                  "JuridicalAddress,ActualAddress,Phone,Email,"
                  "InternetAddress_Presentation,IsBuyer,IsSupplier,Date_Time",
        "orderby": "Date_Time",
    },
    "contracts": {
        "entity_set": "Catalog_ДоговорыКонтрагентов",
        "select": "Ref_Key,Description,StartDate,FinishDate,Amount,"
                  "Currency,ОрганизацияВзаиморасчетов_Key,Date_Time",
        "orderby": "Date_Time",
    },
    "orders": {
        "entity_set": "Document_ЗаказКлиента",
        "select": "Ref_Key,Description,Date,Amount,Currency,"
                  "ОрганизацияВзаиморасчетов_Key,Date_Time",
        "orderby": "Date_Time",
    },
    # ... аналогично для invoices, payments, products, employees
}
```

---

## 3. Tool Library — API Contracts

### 3.1 Tool Registration Architecture

```
┌─────────────────────────────────────────────────────┐
│                   OpenClaw Agent                      │
│                                                       │
│  Incoming msg → Intent Classification → Tool Call    │
│                      │                                │
│                      ▼                                │
│  ┌─────────────────────────────────────────────────┐ │
│  │  OpenClaw Plugin (TypeScript wrapper)           │ │
│  │                                                  │ │
│  │  handler(payload, context) → response            │ │
│  │  schema: { params, response } (JSON Schema)      │ │
│  │  description: "..."                              │ │
│  │                                                  │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │ │
│  │  │ Tool 1   │ │ Tool 2   │ │ Tool N   │        │ │
│  │  └──────────┘ └──────────┘ └──────────┘        │ │
│  │         │           │            │               │ │
│  │         ▼           ▼            ▼               │ │
│  │  ┌──────────────────────────────────────────┐   │ │
│  │  │  Tool Runtime (Python FastAPI, internal)  │   │ │
│  │  │  GET /tools/{name}?tenant_id=...&args=... │   │ │
│  │  │  ┌────────────────────────────────────┐  │   │ │
│  │  │  │  PostgreSQL — parametrized queries  │  │   │ │
│  │  │  └────────────────────────────────────┘  │   │ │
│  │  └──────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 3.2 Tool Contracts

All tools:
- Receive `tenant_id` from OpenClaw session context (not from user input)
- Return structured JSON with `{ success: bool, data: any, error?: string }`
- Use **only parameterized SQL** — no string interpolation
- Are idempotent (read-only in MVP; no write operations)

---

#### Tool 1: `get_contract_utilization`

**Purpose:** Получить статус исполнения договора — сумму, процент, остаток.

**Parameters:**
```json
{
  "type": "object",
  "properties": {
    "contract_id": {
      "type": "string",
      "format": "uuid",
      "description": "ID договора в системе Умник"
    },
    "counterparty_id": {
      "type": "string",
      "format": "uuid",
      "description": "ID контрагента (если contract_id не указан)"
    },
    "contract_number": {
      "type": "string",
      "description": "Номер договора (поиск по номеру)"
    }
  },
  "anyOf": [
    { "required": ["contract_id"] },
    { "required": ["counterparty_id"] },
    { "required": ["contract_number"] }
  ]
}
```

**Response:**
```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "data": {
      "type": "object",
      "properties": {
        "contract": {
          "type": "object",
          "properties": {
            "id": { "type": "string", "format": "uuid" },
            "number": { "type": "string" },
            "counterparty": { "type": "string" },
            "date_start": { "type": "string", "format": "date" },
            "date_end": { "type": "string", "format": "date" },
            "amount": { "type": "number" },
            "currency": { "type": "string" },
            "utilization_sum": { "type": "number" },
            "utilization_pct": { "type": "number" },
            "remaining": { "type": "number" },
            "status": { "type": "string" }
          }
        },
        "recent_invoices": {
          "type": "array",
          "items": { "$ref": "#/definitions/InvoiceSummary" }
        }
      }
    }
  }
}
```

**SQL:**
```sql
WITH target AS (
    SELECT id, tenant_id, number, counterparty_id, date_start, date_end,
           amount, currency, utilization_sum, utilization_pct, status
    FROM umnick.contracts
    WHERE tenant_id = :tenant_id
      AND (id = :contract_id OR :contract_id IS NULL)
      AND (counterparty_id = :counterparty_id OR :counterparty_id IS NULL)
      AND (number ILIKE '%' || :contract_number || '%' OR :contract_number IS NULL)
    LIMIT 1
)
SELECT c.*,
       cp.name AS counterparty_name,
       (c.amount - c.utilization_sum) AS remaining
FROM target c
LEFT JOIN umnick.counterparties cp ON cp.id = c.counterparty_id AND cp.tenant_id = :tenant_id;
```

---

#### Tool 2: `get_overdue_payments`

**Purpose:** Получить список просроченных платежей — долги клиентов с overdue-счетами.

**Parameters:**
```json
{
  "type": "object",
  "properties": {
    "days_overdue_min": {
      "type": "integer",
      "description": "Минимальное количество дней просрочки (default: 1)",
      "minimum": 0,
      "default": 1
    },
    "limit": {
      "type": "integer",
      "description": "Максимум результатов",
      "minimum": 1,
      "maximum": 100,
      "default": 20
    },
    "counterparty_id": {
      "type": "string",
      "format": "uuid",
      "description": "Фильтр по конкретному контрагенту"
    },
    "threshold_amount": {
      "type": "number",
      "description": "Минимальная сумма просрочки",
      "minimum": 0
    }
  }
}
```

**Response:**
```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "data": {
      "type": "object",
      "properties": {
        "summary": {
          "type": "object",
          "properties": {
            "total_overdue_count": { "type": "integer" },
            "total_overdue_sum": { "type": "number" },
            "currency": { "type": "string" }
          }
        },
        "overdue_invoices": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "invoice_number": { "type": "string" },
              "counterparty": { "type": "string" },
              "amount": { "type": "number" },
              "balance": { "type": "number" },
              "due_date": { "type": "string", "format": "date" },
              "days_overdue": { "type": "integer" }
            }
          }
        }
      }
    }
  }
}
```

**SQL:**
```sql
SELECT i.id, i.number, i.date, i.due_date, i.amount, i.balance,
       i.paid_amount, i.status,
       cp.name AS counterparty_name, cp.id AS counterparty_id,
       (CURRENT_DATE - i.due_date) AS days_overdue
FROM umnick.invoices i
JOIN umnick.counterparties cp ON cp.id = i.counterparty_id AND cp.tenant_id = :tenant_id
WHERE i.tenant_id = :tenant_id
  AND i.status IN ('unpaid', 'partial')
  AND i.due_date < CURRENT_DATE - :days_overdue_min::integer
  AND (:counterparty_id IS NULL OR i.counterparty_id = :counterparty_id)
  AND (:threshold_amount IS NULL OR i.balance >= :threshold_amount)
ORDER BY i.due_date ASC
LIMIT :limit;
```

---

#### Tool 3: `get_client_activity`

**Purpose:** Получить активность клиента — заказы, платежи, счета за период.

**Parameters:**
```json
{
  "type": "object",
  "properties": {
    "counterparty_id": {
      "type": "string",
      "format": "uuid",
      "description": "ID контрагента"
    },
    "inn": {
      "type": "string",
      "description": "ИНН контрагента (поиск, если нет ID)"
    },
    "period_days": {
      "type": "integer",
      "description": "Глубина анализа в днях",
      "minimum": 1,
      "maximum": 365,
      "default": 30
    },
    "include_invoices": {
      "type": "boolean",
      "default": true
    },
    "include_payments": {
      "type": "boolean",
      "default": true
    },
    "include_orders": {
      "type": "boolean",
      "default": true
    }
  },
  "anyOf": [
    { "required": ["counterparty_id"] },
    { "required": ["inn"] }
  ]
}
```

**Response:**
```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "data": {
      "type": "object",
      "properties": {
        "counterparty": {
          "type": "object",
          "properties": {
            "id": { "type": "string", "format": "uuid" },
            "name": { "type": "string" },
            "inn": { "type": "string" },
            "status": { "type": "string" }
          }
        },
        "period": {
          "type": "object",
          "properties": {
            "from": { "type": "string", "format": "date" },
            "to": { "type": "string", "format": "date" }
          }
        },
        "activity_summary": {
          "type": "object",
          "properties": {
            "total_orders": { "type": "integer" },
            "total_invoices": { "type": "integer" },
            "total_payments_in": { "type": "number" },
            "total_payments_out": { "type": "number" }
          }
        },
        "orders": { "type": "array" },
        "invoices": { "type": "array" },
        "payments": { "type": "array" }
      }
    }
  }
}
```

**SQL (activity_summary):**
```sql
WITH cp AS (
    SELECT id, name, inn, status
    FROM umnick.counterparties
    WHERE tenant_id = :tenant_id
      AND (id = :counterparty_id OR inn = :inn)
    LIMIT 1
)
SELECT
    (SELECT COUNT(*) FROM umnick.orders
     WHERE tenant_id = :tenant_id
       AND counterparty_id = (SELECT id FROM cp)
       AND date >= :period_start) AS total_orders,

    (SELECT COUNT(*) FROM umnick.invoices
     WHERE tenant_id = :tenant_id
       AND counterparty_id = (SELECT id FROM cp)
       AND date >= :period_start) AS total_invoices,

    (SELECT COALESCE(SUM(amount), 0) FROM umnick.payments
     WHERE tenant_id = :tenant_id
       AND counterparty_id = (SELECT id FROM cp)
       AND date >= :period_start
       AND direction = 'incoming') AS total_payments_in,

    (SELECT COALESCE(SUM(amount), 0) FROM umnick.payments
     WHERE tenant_id = :tenant_id
       AND counterparty_id = (SELECT id FROM cp)
       AND date >= :period_start
       AND direction = 'outgoing') AS total_payments_out;
```

---

#### Tool 4: `query_sales`

**Purpose:** Анализ продаж — выручка, количество, динамика.

**Parameters:**
```json
{
  "type": "object",
  "properties": {
    "period_days": {
      "type": "integer",
      "description": "Период анализа в днях",
      "minimum": 1,
      "maximum": 365,
      "default": 30
    },
    "granularity": {
      "type": "string",
      "enum": ["day", "week", "month"],
      "default": "day"
    },
    "counterparty_id": {
      "type": "string",
      "format": "uuid",
      "description": "Фильтр по контрагенту"
    },
    "include_chart_data": {
      "type": "boolean",
      "default": false,
      "description": "Включить данные для построения графика"
    }
  }
}
```

**Response:**
```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "data": {
      "type": "object",
      "properties": {
        "summary": {
          "type": "object",
          "properties": {
            "total_revenue": { "type": "number" },
            "total_orders": { "type": "integer" },
            "avg_order_value": { "type": "number" },
            "currency": { "type": "string" }
          }
        },
        "by_counterparty": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": { "type": "string" },
              "revenue": { "type": "number" },
              "orders_count": { "type": "integer" }
            }
          }
        },
        "chart_data": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "period": { "type": "string" },
              "revenue": { "type": "number" },
              "orders": { "type": "integer" }
            }
          }
        }
      }
    }
  }
}
```

**SQL (summary):**
```sql
SELECT
    COALESCE(SUM(amount), 0) AS total_revenue,
    COUNT(*) AS total_orders,
    CASE WHEN COUNT(*) > 0 THEN SUM(amount) / COUNT(*) ELSE 0 END AS avg_order_value
FROM umnick.orders
WHERE tenant_id = :tenant_id
  AND date >= CURRENT_DATE - :period_days::integer
  AND status NOT IN ('cancelled', 'draft')
  AND (:counterparty_id IS NULL OR counterparty_id = :counterparty_id);
```

---

#### Tool 5: `find_contracts`

**Purpose:** Поиск договоров по различным критериям.

**Parameters:**
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Текст для поиска по номеру или контрагенту"
    },
    "status": {
      "type": "string",
      "enum": ["active", "closed", "suspended"],
      "description": "Фильтр по статусу"
    },
    "counterparty_id": {
      "type": "string",
      "format": "uuid"
    },
    "expiring_soon_days": {
      "type": "integer",
      "description": "Истекает в ближайшие N дней"
    },
    "min_amount": {
      "type": "number",
      "minimum": 0
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 50,
      "default": 20
    }
  }
}
```

**SQL:**
```sql
SELECT c.*, cp.name AS counterparty_name
FROM umnick.contracts c
LEFT JOIN umnick.counterparties cp ON cp.id = c.counterparty_id AND cp.tenant_id = :tenant_id
WHERE c.tenant_id = :tenant_id
  AND (:query IS NULL
       OR c.number ILIKE '%' || :query || '%'
       OR cp.name ILIKE '%' || :query || '%')
  AND (:status IS NULL OR c.status = :status)
  AND (:counterparty_id IS NULL OR c.counterparty_id = :counterparty_id)
  AND (:expiring_soon_days IS NULL
       OR (c.date_end IS NOT NULL
           AND c.date_end BETWEEN CURRENT_DATE AND CURRENT_DATE + :expiring_soon_days::integer))
  AND (:min_amount IS NULL OR c.amount >= :min_amount)
ORDER BY c.date_start DESC
LIMIT :limit;
```

---

#### Tool 6: `get_client_360`

**Purpose:** Полная карточка клиента 360° — все данные о контрагенте.

**Parameters:**
```json
{
  "type": "object",
  "properties": {
    "counterparty_id": {
      "type": "string",
      "format": "uuid"
    },
    "inn": {
      "type": "string"
    },
    "name_query": {
      "type": "string",
      "description": "Поиск по названию"
    }
  },
  "anyOf": [
    { "required": ["counterparty_id"] },
    { "required": ["inn"] },
    { "required": ["name_query"] }
  ]
}
```

**SQL (кумулятивный — вызывается несколько запросов в рамках одного tool handler):**

```sql
-- 1. Контрагент
SELECT * FROM umnick.counterparties
WHERE tenant_id = :tenant_id
  AND (id = :counterparty_id OR inn = :inn OR name ILIKE '%' || :name_query || '%')
LIMIT 1;

-- 2. Активные договоры
SELECT * FROM umnick.contracts
WHERE tenant_id = :tenant_id AND counterparty_id = :resolved_cp_id AND status = 'active';

-- 3. Просроченные счета
SELECT COUNT(*), COALESCE(SUM(balance), 0) AS total_overdue
FROM umnick.invoices
WHERE tenant_id = :tenant_id
  AND counterparty_id = :resolved_cp_id
  AND status IN ('unpaid', 'partial')
  AND due_date < CURRENT_DATE;

-- 4. Последние заказы
SELECT * FROM umnick.orders
WHERE tenant_id = :tenant_id AND counterparty_id = :resolved_cp_id
ORDER BY date DESC LIMIT 10;

-- 5. Итого по продажам (30 дней)
SELECT COALESCE(SUM(amount), 0) AS sales_30d
FROM umnick.orders
WHERE tenant_id = :tenant_id
  AND counterparty_id = :resolved_cp_id
  AND date >= CURRENT_DATE - 30
  AND status NOT IN ('cancelled', 'draft');
```

---

#### Tool 7: `list_active_clients`

**Purpose:** Список активных клиентов с ключевыми метриками.

**Parameters:**
```json
{
  "type": "object",
  "properties": {
    "segment": {
      "type": "string",
      "enum": ["vip", "wholesale", "retail", null],
      "description": "Фильтр по сегменту"
    },
    "has_overdue": {
      "type": "boolean",
      "description": "Только с просрочками"
    },
    "min_revenue_30d": {
      "type": "number",
      "minimum": 0,
      "description": "Мин. выручка за 30 дней"
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 50,
      "default": 20
    },
    "sort_by": {
      "type": "string",
      "enum": ["revenue", "name", "overdue"],
      "default": "revenue"
    }
  }
}
```

**SQL:**
```sql
WITH active_cp AS (
    SELECT id, name, inn, segment, status, phone, email,
           is_client, is_buyer
    FROM umnick.counterparties
    WHERE tenant_id = :tenant_id
      AND status = 'active'
      AND (:segment IS NULL OR segment = :segment)
),
cp_metrics AS (
    SELECT
        ac.id,
        ac.name,
        ac.inn,
        ac.segment,
        ac.phone,
        ac.email,
        COALESCE(s30.sales_30d, 0) AS revenue_30d,
        COALESCE(od.overdue_count, 0) AS overdue_count,
        COALESCE(od.overdue_sum, 0) AS overdue_sum,
        COALESCE(oc.order_count, 0) AS order_count_90d
    FROM active_cp ac
    LEFT JOIN (
        SELECT counterparty_id,
               COUNT(*) AS order_count
        FROM umnick.orders
        WHERE tenant_id = :tenant_id
          AND date >= CURRENT_DATE - 90
          AND status NOT IN ('cancelled', 'draft')
        GROUP BY counterparty_id
    ) oc ON oc.counterparty_id = ac.id
    LEFT JOIN (
        SELECT counterparty_id,
               SUM(amount) AS sales_30d
        FROM umnick.orders
        WHERE tenant_id = :tenant_id
          AND date >= CURRENT_DATE - 30
          AND status NOT IN ('cancelled', 'draft')
        GROUP BY counterparty_id
    ) s30 ON s30.counterparty_id = ac.id
    LEFT JOIN (
        SELECT counterparty_id,
               COUNT(*) AS overdue_count,
               COALESCE(SUM(balance), 0) AS overdue_sum
        FROM umnick.invoices
        WHERE tenant_id = :tenant_id
          AND status IN ('unpaid', 'partial')
          AND due_date < CURRENT_DATE
        GROUP BY counterparty_id
    ) od ON od.counterparty_id = ac.id
    WHERE (:has_overdue IS NULL OR (:has_overdue = TRUE AND od.overdue_count > 0))
      AND (:min_revenue_30d IS NULL OR COALESCE(s30.sales_30d, 0) >= :min_revenue_30d)
)
SELECT *
FROM cp_metrics
ORDER BY
    CASE WHEN :sort_by = 'revenue' THEN revenue_30d END DESC,
    CASE WHEN :sort_by = 'name' THEN name END ASC,
    CASE WHEN :sort_by = 'overdue' THEN overdue_sum END DESC
LIMIT :limit;
```

---

## 4. OpenClaw Plugin Schema

### 4.1 Plugin Architecture

```
/opt/umnick/openclaw-plugins/
  ├── package.json
  ├── tsconfig.json
  ├── src/
  │   ├── index.ts            # Plugin entry — регистрация всех tools
  │   ├── types.ts             # TypeScript интерфейсы
  │   ├── tools/
  │   │   ├── contract-utilization.ts
  │   │   ├── overdue-payments.ts
  │   │   ├── client-activity.ts
  │   │   ├── query-sales.ts
  │   │   ├── find-contracts.ts
  │   │   ├── client-360.ts
  │   │   └── active-clients.ts
  │   └── lib/
  │       ├── tool-runtime.ts   # HTTP-клиент к Tool Runtime (FastAPI)
  │       └── types.ts          # Внутренние типы
  ├── Dockerfile
  └── dist/                    # Сборка
```

### 4.2 TypeScript Interfaces

```typescript
// types.ts — TypeScript интерфейс плагина

interface ToolHandler<Params, Response> {
  /**
   * Выполнить tool.
   * @param params — валидированные параметры (по JSON Schema)
   * @param context — контекст OpenClaw (tenant_id, session_id, и т.д.)
   * @returns структурированный ответ
   */
  (params: Params, context: ToolContext): Promise<ToolResponse<Response>>;
}

interface ToolSchema {
  /** Имя tool-а — уникально */
  name: string;
  /** Читаемое описание для LLM */
  description: string;
  /** JSON Schema для валидации входных параметров */
  parameters: Record<string, unknown>;
  /** JSON Schema для ответа (опционально) */
  response?: Record<string, unknown>;
}

interface ToolPlugin {
  /** Версия плагина */
  version: string;
  /** Список tools */
  tools: ToolDefinition[];
}

interface ToolDefinition {
  schema: ToolSchema;
  handler: ToolHandler<unknown, unknown>;
}

interface ToolContext {
  /** ID арендатора (из сессии) */
  tenantId: string;
  /** ID сессии OpenClaw */
  sessionId: string;
  /** Метаданные сессии */
  metadata: Record<string, unknown>;
}

interface ToolResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
}
```

### 4.3 Plugin Registration

```typescript
// index.ts — регистрация плагина

import type { ToolPlugin } from './types';
import { contractUtilizationHandler, contractUtilizationSchema } from './tools/contract-utilization';
import { overduePaymentsHandler, overduePaymentsSchema } from './tools/overdue-payments';
import { clientActivityHandler, clientActivitySchema } from './tools/client-activity';
import { querySalesHandler, querySalesSchema } from './tools/query-sales';
import { findContractsHandler, findContractsSchema } from './tools/find-contracts';
import { client360Handler, client360Schema } from './tools/client-360';
import { activeClientsHandler, activeClientsSchema } from './tools/active-clients';

export default {
  version: '1.0.0',
  tools: [
    {
      schema: contractUtilizationSchema,
      handler: contractUtilizationHandler,
    },
    {
      schema: overduePaymentsSchema,
      handler: overduePaymentsHandler,
    },
    {
      schema: clientActivitySchema,
      handler: clientActivityHandler,
    },
    {
      schema: querySalesSchema,
      handler: querySalesHandler,
    },
    {
      schema: findContractsSchema,
      handler: findContractsHandler,
    },
    {
      schema: client360Schema,
      handler: client360Handler,
    },
    {
      schema: activeClientsSchema,
      handler: activeClientsHandler,
    },
  ],
} satisfies ToolPlugin;
```

### 4.4 Tool Handler Example

```typescript
// tools/overdue-payments.ts

import type { ToolSchema, ToolHandler, ToolContext, ToolResponse } from '../types';

const TOOL_RUNTIME_URL = process.env.TOOL_RUNTIME_URL || 'http://tools:8000';

export const overduePaymentsSchema: ToolSchema = {
  name: 'get_overdue_payments',
  description: 'Получить список просроченных платежей. Возвращает счета клиентов, по которым ' +
    'пропущен срок оплаты, с указанием суммы долга, количества дней просрочки и контактных данных.',
  parameters: {
    type: 'object',
    properties: {
      days_overdue_min: {
        type: 'integer',
        description: 'Минимальное количество дней просрочки',
        minimum: 0,
        default: 1,
      },
      limit: {
        type: 'integer',
        default: 20,
      },
      threshold_amount: {
        type: 'number',
        description: 'Минимальная сумма просрочки',
        minimum: 0,
      },
    },
  },
};

export const overduePaymentsHandler: ToolHandler<
  { days_overdue_min?: number; limit?: number; threshold_amount?: number },
  any
> = async (params, context: ToolContext) => {
  try {
    const url = new URL(`${TOOL_RUNTIME_URL}/tools/get_overdue_payments`);
    url.searchParams.set('tenant_id', context.tenantId);
    if (params.days_overdue_min) url.searchParams.set('days_overdue_min', String(params.days_overdue_min));
    if (params.limit) url.searchParams.set('limit', String(params.limit));
    if (params.threshold_amount) url.searchParams.set('threshold_amount', String(params.threshold_amount));

    const response = await fetch(url.toString());
    const data = await response.json();
    return data;
  } catch (err) {
    return {
      success: false,
      error: {
        code: 'TOOL_ERROR',
        message: `Ошибка получения просроченных платежей: ${err instanceof Error ? err.message : 'Unknown'}`,
      },
    };
  }
};
```

### 4.5 Docker Deployment

```dockerfile
# openclaw-plugins/Dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json tsconfig.json ./
COPY src/ ./src/
RUN npm ci && npm run build

FROM node:22-alpine AS runner
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package.json ./
EXPOSE 3001
CMD ["node", "dist/index.js"]
```

**Docker Compose:**
```yaml
# docker/docker-compose.yml (фрагмент)
services:
  openclaw-plugins:
    build: ../openclaw-plugins
    environment:
      - TOOL_RUNTIME_URL=http://tools:8000
    networks:
      - umnick-net
    restart: unless-stopped
```

---

## 5. Proactive Engine — Watchers

### 5.1 Watcher Data Model

```sql
CREATE TABLE umnick.watchers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,

    -- Конфигурация
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    schedule        VARCHAR(64) NOT NULL,          -- cron-выражение: '0 9 * * 1-5'
    tool_name       VARCHAR(64) NOT NULL,           -- имя tool для проверки условия
    tool_params     JSONB DEFAULT '{}'::jsonb,      -- параметры для tool
    condition       TEXT NOT NULL,                  -- JS-подобное выражение: 'data.overdue_count > 0'
    message_template TEXT NOT NULL,                 -- Markdown-шаблон для Telegram

    -- Получатели
    recipients      TEXT[] NOT NULL DEFAULT '{}',   -- Telegram chat_ids / user_ids
    priority        VARCHAR(16) DEFAULT 'normal'
        CHECK (priority IN ('low', 'normal', 'high', 'critical')),

    -- Состояние
    enabled         BOOLEAN DEFAULT TRUE,
    snooze_until    TIMESTAMPTZ,                   -- временное отключение
    last_run_at     TIMESTAMPTZ,                   -- последний запуск
    last_alert_hash VARCHAR(64),                   -- хэш последнего алерта (дедупликация)
    last_alert_at   TIMESTAMPTZ,                   — время последнего алерта
    alert_count     INTEGER DEFAULT 0,              — всего алертов отправлено

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ограничения
    CONSTRAINT unique_watcher_name_per_tenant UNIQUE (tenant_id, name)
);

CREATE INDEX idx_watchers_tenant_enabled
    ON umnick.watchers (tenant_id, enabled)
    WHERE enabled = TRUE AND (snooze_until IS NULL OR snooze_until < NOW());
```

### 5.2 Deduplication

```
                    ┌─────────────┐
                    │ Celery Beat │
                    │ (cron tick) │
                    └──────┬──────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  Check watchers due    │
              │  (schedule matches now) │
              └──────────┬─────────────┘
                         │
                         ▼
              ┌────────────────────────┐
              │  Call tool_name with   │
              │  tool_params           │
              └──────────┬─────────────┘
                         │
                         ▼
              ┌────────────────────────┐
              │  Evaluate condition    │
              │  against tool response │
              └──────────┬─────────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
    ┌─────────────────┐     ┌──────────────────┐
    │ Condition FALSE │     │ Condition TRUE    │
    │ (skip, update   │     │ Compute alert_hash│
    │  last_run_at)   │     │ SHA256(tool_name  │
    └─────────────────┘     │ + tool_params +   │
                            │ + response slice) │
                            └────────┬─────────┘
                                     │
                          ┌──────────┴──────────┐
                          ▼                     ▼
                 ┌────────────────┐   ┌──────────────────┐
                 │ hash == last    │   │ hash != last      │
                 │ (dedup, skip)   │   │ (send alert)       │
                 └────────────────┘   │ Update last_       │
                                      │ alert_hash         │
                                      └────────────────────┘
```

**De-duplication algorithm:**
```python
def should_send_alert(watcher: Watcher, tool_response: dict) -> tuple[bool, str]:
    """
    Returns (should_send: bool, new_hash: str)
    """
    # Строим хэш от ключевой информации ответа
    content_for_hash = {
        "tool": watcher.tool_name,
        "params": watcher.tool_params,
        "summary": tool_response.get("data", {}).get("summary", {}),
    }
    new_hash = hashlib.sha256(
        json.dumps(content_for_hash, sort_keys=True).encode()
    ).hexdigest()

    if watcher.last_alert_hash == new_hash:
        return False, new_hash  # Дедупликация — алерт уже отправлен

    # Проверка snooze
    if watcher.snooze_until and watcher.snooze_until > datetime.utcnow():
        return False, new_hash

    return True, new_hash
```

### 5.3 Starter Watchers

#### Watcher 1: `daily_overdue_check` — Ежедневная проверка просрочек

```json
{
  "name": "daily_overdue_check",
  "description": "Ежедневная проверка просроченных платежей в 9:00 по будням",
  "schedule": "0 9 * * 1-5",
  "tool_name": "get_overdue_payments",
  "tool_params": { "days_overdue_min": 1, "limit": 50, "threshold_amount": 1000 },
  "condition": "data.summary.total_overdue_count > 0",
  "message_template": "📋 *Ежедневный отчёт по просрочкам*\n\n" +
    "Всего просроченных счетов: *{{data.summary.total_overdue_count}}*\n" +
    "Общая сумма просрочки: *{{data.summary.total_overdue_sum | number}} {{data.summary.currency}}*\n\n" +
    "{% for inv in data.overdue_invoices[:5] %}\n" +
    "🔴 {{inv.counterparty}} — {{inv.balance | number}}₽ ({{inv.days_overdue}} дн.)\n" +
    "{% endfor %}\n" +
    "{% if data.overdue_invoices | length > 5 %}\n" +
    "...и ещё {{data.overdue_invoices | length - 5}} просрочек\n" +
    "{% endif %}",
  "priority": "high",
  "enabled": true
}
```

#### Watcher 2: `low_stock_alert` — Оповещение о низких остатках

```json
{
  "name": "low_stock_alert",
  "description": "Ежечасная проверка товаров с остатком ниже минимального",
  "schedule": "0 * * * *",
  "tool_name": "query_sales",
  "tool_params": {
    "period_days": 1,
    "include_low_stock": true
  },
  "condition": "data.low_stock_products is defined and data.low_stock_products | length > 0",
  "message_template": "⚠️ *Низкий остаток товаров*\n\n" +
    "{% for p in data.low_stock_products %}\n" +
    "• {{p.name}} — остаток *{{p.stock_available}} {{p.unit}}* (мин. {{p.min_stock}})\n" +
    "{% endfor %}\n\n" +
    "🏪 Всего товаров ниже min: {{data.low_stock_products | length}}",
  "priority": "normal",
  "enabled": true
}
```

#### Watcher 3: `weekly_revenue_drop` — Недельный мониторинг продаж

```json
{
  "name": "weekly_revenue_drop",
  "description": "Еженедельная проверка: не упала ли выручка >20% по сравнению с прошлой неделей",
  "schedule": "0 10 * * 1",
  "tool_name": "query_sales",
  "tool_params": {
    "period_days": 14,
    "granularity": "week",
    "include_chart_data": true
  },
  "condition": "data.chart_data | length >= 2 and (data.chart_data[0].revenue - data.chart_data[1].revenue) / data.chart_data[1].revenue * 100 < -20",
  "message_template": "📊 *Мониторинг выручки*\n\n" +
    "⚠️ Выручка за последнюю неделю снизилась на *{{drop_pct | round(1)}}%*\n\n" +
    "▫️ Текущая неделя: *{{data.chart_data[0].revenue | number}}₽*\n" +
    "▫️ Предыдущая: *{{data.chart_data[1].revenue | number}}₽*\n\n" +
    "Рекомендуем проверить активность по ключевым клиентам.",
  "priority": "normal",
  "enabled": true
}
```

### 5.4 Celery Beat Configuration

```python
# engine/celery_app.py
from celery import Celery
from celery.schedules import crontab

app = Celery("umnick_engine", broker="redis://redis:6379/0")

app.conf.beat_schedule = {
    "check-watchers-every-minute": {
        "task": "engine.tasks.check_due_watchers",
        "schedule": 60.0,  # Каждую минуту проверяем, какие watchers запускать
    },
    "sync-orders-every-5min": {
        "task": "bridge.tasks.sync_orders",
        "schedule": 300.0,
    },
    "sync-contracts-every-15min": {
        "task": "bridge.tasks.sync_contracts",
        "schedule": 900.0,
    },
    "sync-counterparties-every-15min": {
        "task": "bridge.tasks.sync_counterparties",
        "schedule": 900.0,
    },
    "sync-dicts-every-hour": {
        "task": "bridge.tasks.sync_products_and_employees",
        "schedule": 3600.0,
    },
    "full-reconciliation-daily": {
        "task": "bridge.tasks.full_reconciliation",
        "schedule": crontab(hour=2, minute=0),
    },
}
```

### 5.5 Telegram Message Format

```python
# engine/templates.py
import jinja2

template_env = jinja2.Environment(
    loader=jinja2.BaseLoader(),
    autoescape=False,
    undefined=jinja2.StrictUndefined,
)

def render_message(template_text: str, data: dict) -> str:
    """
    Рендеринг Markdown-шаблона для Telegram.
    Используется Jinja2 с кастомными фильтрами.
    """
    template_env.filters["number"] = lambda v: f"{v:,.2f}"
    template_env.filters["round"] = lambda v, n: round(v, n)
    template = template_env.from_string(template_text)
    return template.render(data=data)
```

**Формат сообщения:**
- Заголовок: эмодзи + **жирный текст** (Markdown V2)
- Разделители: пустая строка `\n\n`
- Элементы списка: буллиты `•` с **жирными** ключевыми значениями
- Общая статистика: эмодзи + **ключ**: *значение*
- Call to action в конце (если применимо)

---

## 6. Conversational Layer

### 6.1 System Prompt

```
Ты — Умник, AI-операционный агент для малого и среднего бизнеса.
Твоя задача — помогать владельцам и менеджерам бизнеса отвечать на вопросы
о состоянии их компании: финансы, продажи, договоры, клиенты.

## ПРАВИЛА РАБОТЫ

### Источники данных
- Ты НЕ используешь информацию из своего обучения (веса модели) для цифр.
- ВСЕ числовые данные (суммы, даты, количества, проценты) ты получаешь
  ТОЛЬКО через вызов tools.
- Если данные по запросу пользователя получены — используй их.
- Если tool вернул ошибку или пустой ответ — честно скажи об этом пользователю.
  Не выдумывай данные.

### Инструменты
У тебя есть 7 tools для работы с данными:
1. get_overdue_payments — просроченные платежи
2. get_contract_utilization — статус исполнения договора
3. get_client_activity — активность клиента (заказы, платежи)
4. query_sales — анализ продаж
5. find_contracts — поиск договоров
6. get_client_360 — полная карточка клиента
7. list_active_clients — список активных клиентов

Используй их согласно описанию. Не вызывай tools без необходимости.
Для простых запросов (приветствие, общие вопросы) можно отвечать без tools.

### Формат ответа
- Отвечай структурированно, с эмодзи-маркерами:
  📋 — сводка/список
  🏢 — информация о клиенте
  💰 — финансы, деньги
  📊 — аналитика, графики данных
  ⚠️ — предупреждение
  ✅ — успех, подтверждение
  ❌ — ошибка, проблема
  ℹ️ — справочная информация

- Для списков используй буллеты (•)
- Для чисел используй *жирный* формат
- Разделяй смысловые блоки пустой строкой
- Завершай ответ вопросом для продолжения диалога, если уместно

### Обработка ошибок
- Если tool не сработал: "Извините, не удалось получить данные.
  [причина ошибки]. Попробуйте позже или проверьте подключение к 1С."
- Если данные не найдены: "По вашему запросу данные не найдены.
  Попробуйте уточнить параметры поиска."

### Конфиденциальность
- Не показывай технические идентификаторы (UUID) пользователю
- Не показывай внутренние ID из 1С
- Не раскрывай данные других арендаторов

### Язык
- Отвечай на русском языке
- Избегай канцеляризмов — говори по делу, коротко, ясно
- Используй термины, понятные владельцу бизнеса
```

### 6.2 Commands

| Command | Description | Handler |
|---------|-------------|---------|
| `/start` | Приветствие и список возможностей | Выводит приветствие + список доступных команд |
| `/help` | Справка по использованию | Краткое описание всех tools и команд |
| `/watchers` | Управление уведомлениями | Список активных watchers, кнопки включения/отключения |
| `/pause N` | Приостановить watcher на N часов | Обновляет `snooze_until` в БД |
| `/status` | Статус системы и синхронизации | Показывает последнюю синхронизацию с 1С |

### 6.3 Response Format Examples

**Пример ответа на запрос о просрочках:**
```
📋 *Просроченные платежи*

💰 Общая сумма: *145 800₽*
📄 Количество: *12 счетов*

🔴 ООО "Ромашка" — *45 000₽* (35 дн.)
🔴 ИП Иванов — *23 500₽* (12 дн.)
🔴 ООО "ТехноСервис" — *12 300₽* (8 дн.)
...и ещё 9 просрочек

ℹ️ Хотите детали по конкретному клиенту?
```

**Пример ответа на запрос клиента 360°:**
```
🏢 *ООО "Ромашка"*
ИНН: 7701234567
Сегмент: wholesale | Статус: ✅ активен

💰 *Финансы*
• Продажи за 30 дней: *890 000₽*
• Всего отгружено: *1 200 000₽*
• Просрочек: *нет*

📄 *Договоры*
• №Д-2025/001 — *1 500 000₽* — действует до 31.12.2026
  Исполнение: 45% (*675 000₽*)

📦 *Последние заказы*
• ЗК-2026/042 — *340 000₽* — 15.04.2026
• ЗК-2026/038 — *210 000₽* — 02.04.2026

ℹ️ Что ещё вас интересует?
```

---

## 7. Admin UI

### 7.1 Architecture

```
Client (React SPA) ───REST──► FastAPI ───► PostgreSQL
                                    │
                                    └───► Celery (run sync)
```

- **Stack:** React 18 + TypeScript + shadcn/ui + Tailwind CSS + Vite
- **Build output:** `admin/dist/` → served by FastAPI as static files
- **Routing:** React Router v6 (client-side)
- **State:** React Query (TanStack Query) — все запросы к API

### 7.2 Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Общая сводка: статус sync, активные watchers, последние алерты |
| `/settings` | 1С настройки | Подключение к 1С-базе (OData URL, логин, пароль) |
| `/watchers` | Watchers | Список watchers, создание, редактирование, snooze |
| `/sync-log` | Лог синхронизации | История синхронизаций, фильтры, детали ошибок |
| `/tools` | Тест tools | Вызов tools вручную для отладки |
| `/tenants` | Управление арендаторами | (admin-only) Список тенантов |

### 7.3 API Endpoints

```yaml
openapi: 3.0.0
info:
  title: Umnick Admin API
  version: 1.0.0
components:
  headers:
    X-Tenant-Id:
      schema:
        type: string
        format: uuid
      required: true
      description: ID арендатора (кроме /api/admin/tenants)

paths:
  /api/admin/tenants:
    get:
      summary: Список тенантов (admin-only)
      security: [{ bearerAuth: [] }]
    post:
      summary: Создание тенанта

  /api/admin/tenants/{tenant_id}/settings:
    get:
      summary: Настройки 1С подключения
      parameters:
        - $ref: '#/components/headers/X-Tenant-Id'
    put:
      summary: Обновление OData credentials

  /api/admin/watchers:
    get:
      summary: Список watchers
      parameters:
        - $ref: '#/components/headers/X-Tenant-Id'
    post:
      summary: Создание watcher

  /api/admin/watchers/{watcher_id}:
    get:
      summary: Детали watcher
    put:
      summary: Обновление watcher
    delete:
      summary: Удаление watcher

  /api/admin/watchers/{watcher_id}/snooze:
    post:
      summary: Отключить watcher на N часов
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                hours:
                  type: integer
                  minimum: 1
                  maximum: 168

  /api/admin/sync:
    post:
      summary: Запустить синхронизацию вручную
      parameters:
        - $ref: '#/components/headers/X-Tenant-Id'
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                entity_type:
                  type: string
                  enum: [counterparties, contracts, orders, invoices, payments, products, employees]

  /api/admin/sync/log:
    get:
      summary: Лог синхронизаций
      parameters:
        - $ref: '#/components/headers/X-Tenant-Id'
      query:
        type: object
        properties:
          limit: { type: integer, default: 50 }
          status: { type: string, enum: [success, error, running] }

  /api/admin/tools/{tool_name}:
    get:
      summary: Выполнить tool (для отладки)
      parameters:
        - $ref: '#/components/headers/X-Tenant-Id'
      query:
        type: object  # параметры tool

  /api/admin/dashboard:
    get:
      summary: Данные для дашборда
      parameters:
        - $ref: '#/components/headers/X-Tenant-Id'
      response:
        type: object
        properties:
          sync_status:
            type: object
            properties:
              last_sync: { type: string, format: date-time }
              status: { type: string }
          watchers_count:
            type: object
            properties:
              total: { type: integer }
              active: { type: integer }
              alerting: { type: integer }
          recent_alerts:
            type: array
            items:
              type: object
              properties:
                watcher_name: { type: string }
                sent_at: { type: string, format: date-time }
                message_preview: { type: string }
```

---

## 8. Project Structure

### 8.1 Monorepo Layout

```
/opt/umnick/
├── docker/
│   ├── docker-compose.yml          # Все сервисы
│   ├── Dockerfile.bridge           # Data Bridge
│   ├── Dockerfile.engine           # Proactive Engine
│   ├── Dockerfile.tools            # Tool Library Runtime
│   └── Dockerfile.admin            # Admin UI + FastAPI
│
├── bridge/                         # Python — Data Bridge
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/              # Миграции БД
│   ├── src/
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic Settings
│   │   ├── database.py            # SQLAlchemy engine + session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Declarative Base
│   │   │   ├── counterparty.py
│   │   │   ├── contract.py
│   │   │   ├── order.py
│   │   │   ├── invoice.py
│   │   │   ├── payment.py
│   │   │   ├── product.py
│   │   │   ├── employee.py
│   │   │   ├── sync_log.py
│   │   │   ├── watcher.py
│   │   │   └── tenant.py
│   │   ├── odata/
│   │   │   ├── __init__.py
│   │   │   ├── client.py          # OData HTTP-клиент
│   │   │   ├── auth.py            # Basic Auth (1С)
│   │   │   └── config.py          # Маппинг сущностей
│   │   ├── sync/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # AbstractSyncWorker
│   │   │   ├── orders.py
│   │   │   ├── contracts.py
│   │   │   ├── counterparties.py
│   │   │   ├── invoices.py
│   │   │   ├── payments.py
│   │   │   ├── products.py
│   │   │   ├── employees.py
│   │   │   └── reconciliation.py  # Полная сверка
│   │   └── web/
│   │       ├── __init__.py
│   │       ├── app.py             # FastAPI bridge app (health, metrics)
│   │       └── routers/
│   │           ├── health.py
│   │           └── metrics.py
│   └── tests/
│       ├── conftest.py
│       ├── test_odata_client.py
│       ├── test_sync_orders.py
│       └── test_crypto.py
│
├── tools/                          # Python — Tool Library Runtime
│   ├── pyproject.toml
│   ├── src/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py            # Read-only session
│   │   ├── app.py                 # FastAPI (routes: /tools/{name})
│   │   ├── middleware.py          # X-Tenant-Id extraction
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # BaseToolHandler
│   │   │   ├── contract_utilization.py
│   │   │   ├── overdue_payments.py
│   │   │   ├── client_activity.py
│   │   │   ├── query_sales.py
│   │   │   ├── find_contracts.py
│   │   │   ├── client_360.py
│   │   │   └── active_clients.py
│   │   └── models/
│   │       └── schemas.py         # Pydantic request/response models
│   └── tests/
│       ├── conftest.py
│       └── test_tools.py
│
├── engine/                         # Python — Proactive Engine
│   ├── pyproject.toml
│   ├── src/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── celery_app.py          # Celery app configuration
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── check_watchers.py  # Основная задача: check due watchers
│   │   │   └── send_alert.py      # Отправка алерта через OpenClaw API
│   │   ├── watcher/
│   │   │   ├── __init__.py
│   │   │   ├── evaluator.py       # Условный движок (Jinja-like condition eval)
│   │   │   ├── dedup.py           # Дедупликация по хэшу
│   │   │   └── template.py        # Jinja2 рендеринг сообщений
│   │   └── notifier/
│   │       ├── __init__.py
│   │       ├── telegram.py        # Отправка через OpenClaw message API
│   │       └── base.py            # AbstractNotifier
│   └── tests/
│       ├── conftest.py
│       ├── test_evaluator.py
│       └── test_dedup.py
│
├── admin/                          # React SPA
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── routes.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── Settings.tsx
│       │   ├── Watchers.tsx
│       │   ├── SyncLog.tsx
│       │   └── Tenants.tsx
│       ├── components/
│       │   ├── ui/                # shadcn/ui components
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx
│       │   │   └── Header.tsx
│       │   ├── sync/
│       │   │   └── SyncStatusBadge.tsx
│       │   └── watchers/
│       │       └── WatcherCard.tsx
│       ├── hooks/
│       │   ├── useTenant.ts
│       │   └── useWatchers.ts
│       ├── lib/
│       │   ├── api.ts             # Axios/Fetch wrapper
│       │   └── utils.ts
│       └── i18n/
│           └── ru.json            # Русская локализация
│
├── openclaw-plugins/               # TypeScript — OpenClaw Plugin
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── index.ts               # Plugin entry point
│       ├── types.ts               # OpenClaw plugin types
│       ├── tools/
│       │   ├── contract-utilization.ts
│       │   ├── overdue-payments.ts
│       │   ├── client-activity.ts
│       │   ├── query-sales.ts
│       │   ├── find-contracts.ts
│       │   ├── client-360.ts
│       │   └── active-clients.ts
│       └── lib/
│           ├── tool-runtime.ts    # HTTP client to tools service
│           └── errors.ts          # Error types
│
├── scripts/
│   ├── init_db.sql                # Первичная инициализация схем
│   ├── seed_data.sql              # Тестовые данные
│   └── migrate.sh                 # Alembic wrapper
│
├── docker/
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── Dockerfile.bridge
│   ├── Dockerfile.engine
│   ├── Dockerfile.tools
│   └── Dockerfile.admin
│
├── .env.example
├── .gitignore
├── README.md
└── ARCHITECTURE.md                # Этот документ
```

### 8.2 Migrations (Alembic)

```bash
# Инициализация
cd bridge && alembic init alembic

# Создание миграции
alembic revision --autogenerate -m "add counterparties table"

# Применение
alembic upgrade head

# Откат
alembic downgrade -1
```

### 8.3 Environment Variables

```bash
# .env.example
# Database
DATABASE_URL=postgresql+asyncpg://umnick:password@postgres:5432/umnick

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Encryption (для OData credentials)
ENCRYPTION_KEY=base64:...

# OpenClaw
OPENCLAW_API_URL=http://openclaw:8080
OPENCLAW_API_KEY=sk-...

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# OpenTelemetry
OTEL_SERVICE_NAME=umnick
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
```

---

## 9. Multi-tenant Contract

### 9.1 Tenant Isolation

```
┌──────────────────────────────────────────────────────────────┐
│                        PostgreSQL                              │
│                                                               │
│  umnick.tenants                                                │
│  ├── tenant_aaa... (ООО "Ромашка")   ←── X-Tenant-Id: aaa    │
│  ├── tenant_bbb... (ИП Иванов)       ←── X-Tenant-Id: bbb    │
│  └── tenant_ccc... (ООО "Техно")     ←── X-Tenant-Id: ccc    │
│                                                               │
│  umnick.counterparties  │  umnick.orders  │  umnick.invoices   │
│  ├── tenant_id: aaa      ├── tenant_id: aaa ├── tenant_id: aaa│
│  ├── tenant_id: bbb      ├── tenant_id: bbb ├── tenant_id: bbb│
│  └── tenant_id: ccc      └── tenant_id: ccc └── tenant_id: ccc│
└──────────────────────────────────────────────────────────────┘
```

### 9.2 Tenant ID Propagation

```
Browser ───GET /api/admin/watchers──► FastAPI
  Request Headers:                        │
    X-Tenant-Id: aaa...                   │ Extract tenant_id from header
                                          ▼
                                    ┌──────────────┐
                                    │  Middleware    │
                                    │  extract       │
                                    │  X-Tenant-Id   │
                                    └──────┬───────┘
                                           │
                                           ▼
                                    ┌──────────────┐
                                    │  Query with   │
                                    │  tenant_id    │
                                    │  filter       │
                                    └──────────────┘

OpenClaw Agent ──Tool Call──► OpenClaw Plugin ──HTTP──► Tool Runtime
  Session Context:                  │                       │
    tenantId: aaa...               Inject tenant_id         │
                                   into URL query            │
                                                             ▼
                                                    ┌──────────────┐
                                                    │  SQL: WHERE   │
                                                    │  tenant_id =   │
                                                    │  :tenant_id   │
                                                    └──────────────┘
```

### 9.3 Row-Level Security (RLS)

```sql
-- Включение RLS на всех таблицах
ALTER TABLE umnick.counterparties ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.sync_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE umnick.watchers ENABLE ROW LEVEL SECURITY;

-- Политика для всех таблиц
CREATE POLICY tenant_isolation ON umnick.counterparties
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- Аналогично для остальных таблиц...
```

### 9.4 OpenClaw Session Metadata

```typescript
// OpenClaw session metadata содержит tenant_id
interface SessionMetadata {
  tenantId: string;
  tenantName: string;
  userId: string;
  userRole: 'owner' | 'admin' | 'viewer';
}
```

---

## 10. Security

### 10.1 SQL Injection Prevention

**Правила (строгие):**
1. Все SQL-запросы — **только** через SQLAlchemy ORM или параметризованные сырые запросы
2. Никакой `f-string` или `.format()` в SQL-строках
3. Никакой `raw_connection()` без параметризации
4. Для LIKE-поиска: `ILIKE '%' || :query || '%'` — параметр, не конкатенация в коде

✅ **Правильно:**
```python
result = await session.execute(
    text("""
        SELECT * FROM umnick.orders
        WHERE tenant_id = :tenant_id
          AND number ILIKE '%' || :query || '%'
    """),
    {"tenant_id": tenant_id, "query": user_input}
)
```

❌ **Неправильно:**
```python
result = await session.execute(
    text(f"SELECT * FROM umnick.orders WHERE number LIKE '%{user_input}%'")
)
```

### 10.2 Data Encryption

```python
# bridge/src/crypto.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import os

class CredentialCrypto:
    """AES-256-GCM шифрование OData-кредов."""

    def __init__(self, key: bytes = None):
        # key: 32 bytes for AES-256
        self.key = key or base64.b64decode(os.environ["ENCRYPTION_KEY"])

    def encrypt(self, plaintext: str) -> str:
        """Encrypt → base64-encoded ciphertext."""
        aesgcm = AESGCM(self.key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ct).decode()

    def decrypt(self, ciphertext_b64: str) -> str:
        """base64-encoded ciphertext → plaintext."""
        raw = base64.b64decode(ciphertext_b64)
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(self.key)
        return aesgcm.decrypt(nonce, ct, None).decode()
```

### 10.3 LLM Data Privacy

**Проблема:** Данные бизнеса (контрагенты, суммы, договоры) отправляются в облачные LLM (OpenAI, YandexGPT, GigaChat) для генерации ответа.

**Меры:**
1. **Дисклеймер в Admin UI:** «Для работы Умника данные вашей компании отправляются к провайдеру LLM. Используются только запрошенные вами данные.»
2. **Архитектурная готовность к on-prem LLM:** OpenClaw поддерживает смену провайдера. При необходимости:
   - Поднять локальную LLM (Llama 3, Qwen 2.5)
   - Сменить адрес в конфиге OpenClaw
3. **Минимизация данных:** В tools передаются только запрошенные данные, без сырых полей (raw_data не включается в ответ tool если не требуется).

### 10.4 API Security Checklist

- [x] X-Tenant-Id header обязателен для tenant-specific endpoints
- [x] Все admin endpoints требуют bearer-token аутентификацию
- [x] OData credentials зашифрованы в БД
- [x] SQL injection защита через параметризацию
- [x] CORS: разрешён только origin admin UI
- [x] Rate limiting: на /api/admin/* (100 req/min per tenant)
- [x] RLS второй рубеж защиты на уровне PostgreSQL
- [x] HTTPS termination на reverse proxy (nginx/traefik)

---

## 11. OpenTelemetry & Monitoring

### 11.1 Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `umnick_sync_duration_ms` | Histogram | tenant_id, entity_type, status | Время синхронизации сущности |
| `umnick_sync_records_total` | Counter | tenant_id, entity_type, action | Количество записей (created/updated/error) |
| `umnick_tool_latency_ms` | Histogram | tenant_id, tool_name | Задержка выполнения tool |
| `umnick_tool_errors_total` | Counter | tenant_id, tool_name, error_code | Ошибки tools |
| `umnick_watcher_runs_total` | Counter | tenant_id, watcher_name, triggered | Количество запусков watcher |
| `umnick_watcher_alerts_total` | Counter | tenant_id, watcher_name | Количество отправленных алертов |
| `umnick_active_tenants` | Gauge | — | Количество активных арендаторов |
| `umnick_db_pool_usage` | Gauge | pool_name | Использование пула соединений |

### 11.2 Structured Logging

```json
// Пример JSON-лога
{
  "timestamp": "2026-04-28T21:30:00.123Z",
  "level": "INFO",
  "message": "Sync completed for orders",
  "service": "bridge",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "a1b2c3d4-...",
  "entity_type": "orders",
  "records_processed": 42,
  "records_updated": 15,
  "records_created": 27,
  "duration_ms": 1234,
  "status": "success"
}
```

**Correlation ID propagation:**
```
HTTP Request (OpenClaw → Plugin → Tool Runtime)
  │
  ├─ correlation_id: 550e... (generated at entry)
  │
  ├─ OpenClaw Plugin adds header X-Correlation-Id
  │
  └─ Tool Runtime passes to DB query context

Celery Task
  │
  ├─ Task.id = correlation_id
  │
  └─ Every log line includes task_id
```

### 11.3 Python Logging Configuration

```python
# bridge/src/config.py
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if DEBUG else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

### 11.4 Health Check Endpoint

```python
# bridge/src/web/routers/health.py
from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter()

@router.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok", "service": "bridge"}

@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_session)):
    """Readiness probe — проверяет соединение с БД и Redis."""
    try:
        await db.execute(text("SELECT 1"))
        redis_ok = await check_redis()
        return {
            "status": "ready" if redis_ok else "degraded",
            "database": "ok",
            "redis": "ok" if redis_ok else "down",
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "error": str(e),
        }
```

### 11.5 Docker Compose — Monitoring Stack

```yaml
# docker/docker-compose.yml (фрагмент monitoring)
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: umnick
      POSTGRES_USER: umnick
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U umnick"]
      interval: 10s

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4318:4318"  # OTLP HTTP

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - promdata:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafanadata:/var/lib/grafana
    ports:
      - "3000:3000"
```

---

## 12. Decision Log

### ADR-001: Single Agent, No Multi-Agent Routing

- **Date:** 2026-04-28
- **Status:** Accepted
- **Context:** Рассматривалась архитектура с мульти-агентной системой (роутинг между LLM-агентами по доменам)
- **Decision:** В MVP — один агент в OpenClaw с tools. Архитектурные закладки под multi-agent не делаем.
- **Rationale:** SMB-нагрузка не требует multi-agent. Сложность неоправданна для MVP. В будущем — tool → LangGraph-граф для сложных сценариев, но не multi-agent роутинг.

### ADR-002: Pull over Webhook for 1С Sync

- **Date:** 2026-04-28
- **Status:** Accepted
- **Context:** 1С не умеет отправлять webhook-и на внешние системы стандартными средствами (без доработки конфигурации)
- **Decision:** MVP использует pull-синхронизацию через OData. Webhook-архитектура — для v2.
- **Rationale:** Pull не требует доработки 1С со стороны клиента. Webhook потребует либо внешнюю надстройку, либо доработку типовой конфигурации.

### ADR-003: RU-Only Interface with i18n Ready

- **Date:** 2026-04-28
- **Status:** Accepted
- **Context:** Продукт для российского рынка. Целевая аудитория — владельцы SMB.
- **Decision:** Весь интерфейс и системный промпт на русском. Все строки вынесены в отдельные i18n-файлы.
- **Rationale:** Не делать лишнюю работу сейчас. i18n-структура позволит быстро добавить EN/KZ/UA при выходе на новые рынки.

### ADR-004: No LangGraph in MVP

- **Date:** 2026-04-28
- **Status:** Accepted
- **Context:** LangGraph может быть полезен для сложных многошаговых сценариев (например, "проанализируй всех клиентов, найди риски, предложи действия")
- **Decision:** Используем OpenClaw с прямым tool-роутингом. Закладываем возможность: tool → LangGraph-граф в будущем.
- **Rationale:** MVP-сценарии — простые question-answering. LangGraph добавит сложность без необходимости на старте.

### ADR-005: AES-256-GCM for Credential Storage

- **Date:** 2026-04-28
- **Status:** Accepted
- **Context:** OData credentials (username/password) хранятся в БД для автоматической синхронизации
- **Decision:** Шифрование AES-256-GCM. Ключ — в переменной окружения ENCRYPTION_KEY.
- **Rationale:** GCM обеспечивает authenticated encryption. Ключ вне БД — базовый принцип безопасности.

### ADR-006: Row-Level Security as Second Layer

- **Date:** 2026-04-28
- **Status:** Accepted
- **Context:** Multi-tenant изоляция критична — клиенты не должны видеть данные друг друга
- **Decision:** tenant_id во всех запросах (первый рубеж) + RLS в PostgreSQL (второй рубеж).
- **Rationale:** Defense in depth. Если баг в приложении пропустит tenant_id, RLS не даст утечки.

---

## Appendix A: Quick Start

```bash
# 1. Клонировать репо
git clone git@github.com:vkrasnovid/umnick.git /opt/umnick

# 2. Настройка окружения
cp .env.example .env
# Отредактировать .env: пароли, ключи, URL

# 3. Запуск инфраструктуры
cd docker
docker compose up -d postgres redis

# 4. Миграции БД
cd ../bridge
poetry install
poetry run alembic upgrade head

# 5. Seed-данные (для разработки)
psql -h localhost -U umnick -d umnick -f ../scripts/seed_data.sql

# 6. Запуск всех сервисов
cd ../docker
docker compose up -d

# 7. Проверка
curl http://localhost:8000/health
# {"status": "ok", "service": "bridge"}
```

## Appendix B: Development Commands

```bash
# Data Bridge
cd bridge
poetry install
poetry run uvicorn src.web.app:app --reload --port 8000

# Tool Runtime
cd tools
poetry install
poetry run uvicorn src.app:app --reload --port 8001

# Proactive Engine (worker + beat)
cd engine
poetry install
poetry run celery -A src.celery_app worker --beat --loglevel=info

# Admin UI
cd admin
npm install
npm run dev

# OpenClaw Plugins (development)
cd openclaw-plugins
npm install
npm run dev
```

## Appendix C: Glossary

| Term | Definition |
|------|-----------|
| **1С** | Платформа 1С:Предприятие (чаще — КА2, УТ, БП) |
| **OData** | Open Data Protocol — RESTful API протокол для доступа к данным 1С |
| **Tenant** | Арендатор — клиент, владелец 1С-базы |
| **Tool** | Инструмент — функция, которую агент вызывает для получения данных |
| **Watcher** | Наблюдатель — правило, которое проверяет условие и шлёт алерт |
| **OpenClaw** | Платформа для запуска AI-агентов |
| **KA2** | 1С:Комплексная Автоматизация 2 |
| **UT** | 1С:Управление Торговлей |
| **BP** | 1С:Бухгалтерия Предприятия |
| **RLS** | Row-Level Security — строчная безопасность PostgreSQL |
