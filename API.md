# API Reference — Умник AI Operations Platform

> **Версия:** 1.0.0  
> **Формат запросов/ответов:** JSON  
> **Кодировка:** UTF-8  

---

## Обзор

Умник предоставляет два API:

| API | Порт | Назначение |
|-----|------|-----------|
| **Bridge Admin API** | 8085 | Администрирование: синхронизация, watchers, tenant, dashboard |
| **Tools API** | 8086 | Бизнес-инструменты (tools) — запросы от OpenClaw плагина |

---

## Общие заголовки

### Bridge Admin API

| Header | Обязательность | Описание |
|--------|---------------|----------|
| `X-Tenant-Id` | Да (кроме `/api/admin/tenants`) | UUID арендатора |
| `X-Admin-Token` | Да | Bearer-токен администратора |
| `Content-Type` | Да | `application/json` |

### Tools API

| Header | Обязательность | Описание |
|--------|---------------|----------|
| `X-Correlation-Id` | Нет | UUID для трассировки запроса |

---

## Коды ошибок

| HTTP-код | Описание |
|----------|---------|
| `200` | Успех |
| `400` | Некорректный запрос (ошибка валидации) |
| `401` | Не авторизован (неверный или отсутствующий токен) |
| `403` | Доступ запрещён |
| `404` | Ресурс не найден |
| `422` | Ошибка валидации тела запроса |
| `429` | Превышен лимит запросов (rate limit) |
| `500` | Внутренняя ошибка сервера |

### Структура ошибки

```json
{
  "detail": "Описание ошибки",
  "error_code": "TENANT_NOT_FOUND"
}
```

---

## Bridge Admin API (порт 8085)

### Health & Readiness

---

#### `GET /health`

Liveness probe. Проверяет, что сервис запущен и отвечает.

**Headers:** не требуются

**Response `200`:**
```json
{
  "status": "ok",
  "service": "bridge"
}
```

---

#### `GET /ready`

Readiness probe. Проверяет соединение с БД и Redis.

**Headers:** не требуются

**Response `200` (всё работает):**
```json
{
  "status": "ready",
  "database": "ok",
  "redis": "ok"
}
```

**Response `503` (проблемы):**
```json
{
  "status": "degraded",
  "database": "ok",
  "redis": "down"
}
```

---

### Подключение к 1С

---

#### `POST /api/admin/connect`

Тестирует подключение к 1С по OData.

**Headers:** `X-Tenant-Id`, `X-Admin-Token`

**Request body:**
```json
{
  "odata_url": "https://server/db/odata/standard.odata",
  "odata_db_name": "БухгалтерияПредприятия",
  "odata_username": "admin",
  "odata_password": "password123"
}
```

**Response `200`:**
```json
{
  "success": true,
  "message": "Соединение с 1С установлено успешно",
  "odata_version": "4.0",
  "available_entities": [
    "Catalog_Контрагенты",
    "Catalog_ДоговорыКонтрагентов",
    "Document_ЗаказКлиента"
  ]
}
```

**Error `400`:**
```json
{
  "success": false,
  "error": "Не удалось подключиться к OData-серверу: Connection refused",
  "error_code": "ODATA_CONNECTION_FAILED"
}
```

**Error codes:** `ODATA_CONNECTION_FAILED`, `ODATA_AUTH_FAILED`, `ODATA_INVALID_URL`

---

### Синхронизация

---

#### `POST /api/admin/sync/trigger`

Запускает ручную синхронизацию выбранной сущности.

**Headers:** `X-Tenant-Id`, `X-Admin-Token`

**Request body:**
```json
{
  "entity_type": "orders"
}
```

**Допустимые `entity_type`:** `counterparties`, `contracts`, `orders`, `invoices`, `payments`, `products`, `employees`

**Response `202`:**
```json
{
  "success": true,
  "message": "Синхронизация orders запущена",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error `400`:**
```json
{
  "success": false,
  "error": "Неизвестный тип сущности: unknown_type",
  "error_code": "INVALID_ENTITY_TYPE"
}
```

---

#### `GET /api/admin/sync/status`

Статус последней синхронизации для всех типов сущностей.

**Headers:** `X-Tenant-Id`, `X-Admin-Token`

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "overall_status": "syncing",
    "entities": {
      "orders": { "last_sync": "2026-04-28T22:15:00Z", "status": "success", "records": 142 },
      "contracts": { "last_sync": "2026-04-28T22:00:00Z", "status": "success", "records": 58 },
      "counterparties": { "last_sync": "2026-04-28T21:00:00Z", "status": "success", "records": 93 },
      "invoices": { "last_sync": "2026-04-28T22:15:00Z", "status": "error", "records": 0, "last_error": "OData timeout" },
      "payments": { "last_sync": "2026-04-28T22:15:00Z", "status": "running", "records": 0 },
      "products": { "last_sync": "2026-04-28T21:00:00Z", "status": "success", "records": 1204 },
      "employees": { "last_sync": "2026-04-28T21:00:00Z", "status": "success", "records": 15 }
    }
  }
}
```

---

#### `GET /api/admin/sync/log`

История синхронизаций с фильтрацией.

**Headers:** `X-Tenant-Id`, `X-Admin-Token`

**Query Parameters:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|-------------|----------|
| `limit` | int | 50 | Количество записей |
| `status` | string | — | Фильтр: `success`, `error`, `running` |
| `entity_type` | string | — | Фильтр по типу сущности |

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "a1b2c3d4-...",
      "sync_type": "orders",
      "started_at": "2026-04-28T22:15:00Z",
      "finished_at": "2026-04-28T22:15:03Z",
      "duration_ms": 3450,
      "status": "success",
      "records_processed": 142,
      "records_updated": 15,
      "records_created": 0,
      "records_errors": 0,
      "error_message": null,
      "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  ],
  "total": 1
}
```

---

### Dashboard

---

#### `GET /api/admin/dashboard`

Статистика для главной панели администратора.

**Headers:** `X-Tenant-Id`, `X-Admin-Token`

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "sync_status": {
      "last_sync": "2026-04-28T22:15:00Z",
      "status": "syncing",
      "entities_up_to_date": 5,
      "entities_in_error": 1,
      "entities_syncing": 1
    },
    "watchers": {
      "total": 3,
      "active": 3,
      "alerting": 1,
      "last_triggered": "daily_overdue_check"
    },
    "recent_alerts": [
      {
        "watcher_name": "daily_overdue_check",
        "sent_at": "2026-04-28T09:00:05Z",
        "message_preview": "📋 Ежедневный отчёт по просрочкам"
      }
    ],
    "tenants_stats": {
      "active": 1,
      "total_orders": 1234,
      "total_revenue": "45 678 000₽"
    }
  }
}
```

---

### Watchers (Управление наблюдателями)

---

#### `GET /api/admin/watchers`

Список всех watchers для арендатора.

**Headers:** `X-Tenant-Id`, `X-Admin-Token`

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "w1-...",
      "name": "daily_overdue_check",
      "description": "Ежедневная проверка просроченных платежей",
      "schedule": "0 9 * * 1-5",
      "tool_name": "get_overdue_payments",
      "priority": "high",
      "enabled": true,
      "last_run_at": "2026-04-28T09:00:00Z",
      "last_alert_at": "2026-04-28T09:00:05Z",
      "alert_count": 45
    }
  ]
}
```

---

#### `POST /api/admin/watchers`

Создать новый watcher.

**Headers:** `X-Tenant-Id`, `X-Admin-Token`

**Request body:**
```json
{
  "name": "daily_overdue_check",
  "description": "Ежедневная проверка просроченных платежей в 9:00 по будням",
  "schedule": "0 9 * * 1-5",
  "tool_name": "get_overdue_payments",
  "tool_params": {
    "days_overdue_min": 1,
    "limit": 50,
    "threshold_amount": 1000
  },
  "condition": "data.summary.total_overdue_count > 0",
  "message_template": "📋 *Ежедневный отчёт по просрочкам*\n\nВсего просроченных счетов: *{{data.summary.total_overdue_count}}*",
  "recipients": ["-1001234567890"],
  "priority": "high",
  "enabled": true
}
```

**Response `201`:**
```json
{
  "success": true,
  "data": {
    "id": "w1-...",
    "name": "daily_overdue_check",
    "enabled": true,
    "created_at": "2026-04-28T23:00:00Z"
  }
}
```

**Error codes:** `WATCHER_NAME_EXISTS`, `INVALID_CRON`, `INVALID_TOOL_NAME`, `INVALID_CONDITION`

---

#### `GET /api/admin/watchers/{watcher_id}`

Детали конкретного watcher.

**Headers:** `X-Tenant-Id`, `X-Admin-Token`

**Path Parameters:** `watcher_id` — UUID watcher

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "id": "w1-...",
    "name": "daily_overdue_check",
    "description": "Ежедневная проверка просроченных платежей",
    "schedule": "0 9 * * 1-5",
    "tool_name": "get_overdue_payments",
    "tool_params": { "days_overdue_min": 1, "limit": 50 },
    "condition": "data.summary.total_overdue_count > 0",
    "message_template": "📋 *Ежедневный отчёт по просрочкам*\n\n...",
    "recipients": ["-1001234567890"],
    "priority": "high",
    "enabled": true,
    "snooze_until": null,
    "last_run_at": "2026-04-28T09:00:00Z",
    "last_alert_at": "2026-04-28T09:00:05Z",
    "alert_count": 45,
    "created_at": "2026-04-28T23:00:00Z",
    "updated_at": "2026-04-28T23:00:00Z"
  }
}
```

**Error `404`:** `{ "detail": "Watcher not found" }`

---

#### `PUT /api/admin/watchers/{watcher_id}`

Обновить существующий watcher. Передаются только изменяемые поля.

**Headers:** `X-Tenant-Id`, `X-Admin-Token`

**Path Parameters:** `watcher_id` — UUID watcher

**Request body (partial):**
```json
{
  "enabled": false,
  "schedule": "0 10 * * 1-5"
}
```

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "id": "w1-...",
    "enabled": false,
    "schedule": "0 10 * * 1-5",
    "updated_at": "2026-04-28T23:01:00Z"
  }
}
```

---

#### `DELETE /api/admin/watchers/{watcher_id}`

Удалить watcher.

**Headers:** `X-Tenant-Id`, `X-Admin-Token`

**Response `200`:**
```json
{
  "success": true,
  "message": "Watcher 'daily_overdue_check' удалён"
}
```

---

### Tenants (Арендаторы)

---

#### `GET /api/admin/tenants`

Список всех арендаторов (admin-only, без X-Tenant-Id).

**Headers:** `X-Admin-Token`

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "t1-...",
      "name": "ООО Ромашка",
      "inn": "7701234567",
      "contact_email": "admin@romashka.ru",
      "is_active": true,
      "subscription_tier": "pro",
      "sync_enabled": true,
      "created_at": "2026-04-01T00:00:00Z",
      "odata_url": "https://1c.romashka.ru/odata/standard.odata"
    }
  ]
}
```

---

#### `POST /api/admin/tenants`

Создать нового арендатора (admin-only).

**Headers:** `X-Admin-Token`

**Request body:**
```json
{
  "name": "ООО Ромашка",
  "inn": "7701234567",
  "contact_email": "admin@romashka.ru",
  "contact_phone": "+7 495 123-45-67",
  "odata_url": "https://1c.romashka.ru/odata/standard.odata",
  "odata_username": "admin",
  "odata_password": "password123",
  "subscription_tier": "basic"
}
```

**Response `201`:**
```json
{
  "success": true,
  "data": {
    "id": "t1-...",
    "name": "ООО Ромашка",
    "is_active": true,
    "created_at": "2026-04-28T23:00:00Z"
  }
}
```

---

#### `PUT /api/admin/tenants/{tenant_id}`

Обновить данные арендатора (admin-only).

**Headers:** `X-Admin-Token`

**Path Parameters:** `tenant_id` — UUID арендатора

**Request body (partial):**
```json
{
  "is_active": false,
  "subscription_tier": "enterprise"
}
```

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "id": "t1-...",
    "is_active": false,
    "subscription_tier": "enterprise",
    "updated_at": "2026-04-28T23:02:00Z"
  }
}
```

---

#### `DELETE /api/admin/tenants/{tenant_id}`

Удалить арендатора (admin-only). Требует подтверждения.

**Headers:** `X-Admin-Token`

**Path Parameters:** `tenant_id` — UUID арендатора

**Response `200`:**
```json
{
  "success": true,
  "message": "Арендатор 'ООО Ромашка' удалён. Все данные очищены."
}
```

---

### Tools (Список зарегистрированных инструментов)

---

#### `GET /api/admin/tools`

Возвращает список зарегистрированных бизнес-инструментов.

**Headers:** `X-Tenant-Id`, `X-Admin-Token`

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "name": "get_contract_utilization",
      "description": "Статус исполнения договора"
    },
    {
      "name": "get_overdue_payments",
      "description": "Просроченные платежи"
    },
    {
      "name": "get_client_activity",
      "description": "Активность клиента"
    },
    {
      "name": "query_sales",
      "description": "Анализ продаж"
    },
    {
      "name": "find_contracts",
      "description": "Поиск договоров"
    },
    {
      "name": "get_client_360",
      "description": "Полная карточка клиента"
    },
    {
      "name": "list_active_clients",
      "description": "Список активных клиентов"
    }
  ],
  "total": 7
}
```

---

## Tools API (порт 8086)

### Общий формат

```
GET /tools/{tool_name}?tenant_id={uuid}&param1=value1&param2=value2
```

**Заголовки:** опционально `X-Correlation-Id`

**Параметры запроса:**

- `tenant_id` (UUID, **обязательный**) — ID арендатора из контекста сессии
- Остальные параметры зависят от конкретного tool (см. ниже)

**Стандартный ответ:**
```json
{
  "success": true,
  "data": { ... }
}
```

**Стандартный ответ с ошибкой:**
```json
{
  "success": false,
  "error": {
    "code": "TOOL_ERROR",
    "message": "Описание ошибки"
  }
}
```

**HTTP коды:** `200` при успехе, `400` при некорректных параметрах, `404` для неизвестного tool

---

### Tool 1: `get_contract_utilization`

Статус исполнения договора — сумма, процент, остаток.

**Endpoint:** `GET /tools/get_contract_utilization`

**Query parameters:**

| Параметр | Тип | Обязательность | Описание |
|----------|-----|---------------|----------|
| `tenant_id` | UUID | **Да** | ID арендатора |
| `contract_id` | UUID | Нет* | ID договора в системе |
| `counterparty_id` | UUID | Нет* | ID контрагента |
| `contract_number` | string | Нет* | Номер договора (частичный поиск) |

*Должен быть указан хотя бы один из `contract_id`, `counterparty_id`, `contract_number`.

**Response `200` (data):**
```json
{
  "contract": {
    "id": "c1-...",
    "number": "Д-2025/001",
    "counterparty": "ООО Ромашка",
    "date_start": "2025-01-01",
    "date_end": "2026-12-31",
    "amount": 1500000.00,
    "currency": "RUB",
    "utilization_sum": 675000.00,
    "utilization_pct": 45.00,
    "remaining": 825000.00,
    "status": "active"
  },
  "recent_invoices": [
    {
      "number": "Сч-2026/042",
      "amount": 340000.00,
      "date": "2026-04-15",
      "status": "paid"
    }
  ]
}
```

---

### Tool 2: `get_overdue_payments`

Просроченные платежи — долги клиентов.

**Endpoint:** `GET /tools/get_overdue_payments`

**Query parameters:**

| Параметр | Тип | По умолч. | Описание |
|----------|-----|-----------|----------|
| `tenant_id` | UUID | — | **Обязательный** |
| `days_overdue_min` | int | 1 | Мин. дней просрочки |
| `limit` | int | 20 | Максимум результатов (≤100) |
| `counterparty_id` | UUID | — | Фильтр по контрагенту |
| `threshold_amount` | float | — | Мин. сумма просрочки |

**Response `200` (data):**
```json
{
  "summary": {
    "total_overdue_count": 12,
    "total_overdue_sum": 145800.50,
    "currency": "RUB"
  },
  "overdue_invoices": [
    {
      "invoice_number": "Сч-2026/015",
      "counterparty": "ООО Ромашка",
      "amount": 50000.00,
      "balance": 45000.00,
      "due_date": "2026-03-25",
      "days_overdue": 34
    },
    {
      "invoice_number": "Сч-2026/020",
      "counterparty": "ИП Иванов",
      "amount": 23500.00,
      "balance": 23500.00,
      "due_date": "2026-04-16",
      "days_overdue": 12
    }
  ]
}
```

---

### Tool 3: `get_client_activity`

Активность клиента — заказы, платежи, счета за период.

**Endpoint:** `GET /tools/get_client_activity`

**Query parameters:**

| Параметр | Тип | По умолч. | Описание |
|----------|-----|-----------|----------|
| `tenant_id` | UUID | — | **Обязательный** |
| `counterparty_id` | UUID | — | ID контрагента* |
| `inn` | string | — | ИНН контрагента* |
| `period_days` | int | 30 | Глубина анализа (1–365) |
| `include_invoices` | bool | true | Включить счета |
| `include_payments` | bool | true | Включить платежи |
| `include_orders` | bool | true | Включить заказы |

*Должен быть указан `counterparty_id` или `inn`.

**Response `200` (data):**
```json
{
  "counterparty": {
    "id": "cp-...",
    "name": "ООО Ромашка",
    "inn": "7701234567",
    "status": "active"
  },
  "period": {
    "from": "2026-03-29",
    "to": "2026-04-28"
  },
  "activity_summary": {
    "total_orders": 8,
    "total_invoices": 12,
    "total_payments_in": 890000.00,
    "total_payments_out": 0
  },
  "orders": [
    {
      "number": "ЗК-2026/042",
      "date": "2026-04-15",
      "amount": 340000.00,
      "status": "shipped"
    }
  ],
  "invoices": [
    {
      "number": "Сч-2026/015",
      "date": "2026-04-01",
      "amount": 50000.00,
      "balance": 45000.00,
      "status": "partial"
    }
  ],
  "payments": [
    {
      "number": "Пл-2026/010",
      "date": "2026-04-10",
      "amount": 50000.00,
      "direction": "incoming"
    }
  ]
}
```

---

### Tool 4: `query_sales`

Анализ продаж — выручка, количество, динамика.

**Endpoint:** `GET /tools/query_sales`

**Query parameters:**

| Параметр | Тип | По умолч. | Описание |
|----------|-----|-----------|----------|
| `tenant_id` | UUID | — | **Обязательный** |
| `period_days` | int | 30 | Период анализа (1–365) |
| `granularity` | string | `day` | Детализация: `day`, `week`, `month` |
| `counterparty_id` | UUID | — | Фильтр по контрагенту |
| `include_chart_data` | bool | false | Данные для графика |

**Response `200` (data):**
```json
{
  "summary": {
    "total_revenue": 45678000.00,
    "total_orders": 142,
    "avg_order_value": 321676.06,
    "currency": "RUB"
  },
  "by_counterparty": [
    {
      "name": "ООО Ромашка",
      "revenue": 890000.00,
      "orders_count": 8
    }
  ],
  "chart_data": [
    {
      "period": "2026-04-28",
      "revenue": 1520000.00,
      "orders": 5
    }
  ]
}
```

---

### Tool 5: `find_contracts`

Поиск договоров по различным критериям.

**Endpoint:** `GET /tools/find_contracts`

**Query parameters:**

| Параметр | Тип | По умолч. | Описание |
|----------|-----|-----------|----------|
| `tenant_id` | UUID | — | **Обязательный** |
| `query` | string | — | Поиск по номеру/контрагенту |
| `status` | string | — | `active`, `closed`, `suspended` |
| `counterparty_id` | UUID | — | Фильтр по контрагенту |
| `expiring_soon_days` | int | — | Истекает в ближайшие N дней |
| `min_amount` | float | — | Мин. сумма договора |
| `limit` | int | 20 | Максимум результатов (≤50) |

**Response `200` (data):**
```json
{
  "contracts": [
    {
      "id": "c1-...",
      "number": "Д-2025/001",
      "counterparty_name": "ООО Ромашка",
      "date_start": "2025-01-01",
      "date_end": "2026-12-31",
      "amount": 1500000.00,
      "currency": "RUB",
      "utilization_sum": 675000.00,
      "utilization_pct": 45.00,
      "status": "active"
    }
  ],
  "total": 1
}
```

---

### Tool 6: `get_client_360`

Полная карточка клиента 360° — все данные о контрагенте.

**Endpoint:** `GET /tools/get_client_360`

**Query parameters:**

| Параметр | Тип | Обязательность | Описание |
|----------|-----|---------------|----------|
| `tenant_id` | UUID | **Да** | ID арендатора |
| `counterparty_id` | UUID | Нет* | ID контрагента |
| `inn` | string | Нет* | ИНН контрагента |
| `name_query` | string | Нет* | Поиск по названию |

*Должен быть указан хотя бы один из параметров.

**Response `200` (data):**
```json
{
  "counterparty": {
    "id": "cp-...",
    "name": "ООО Ромашка",
    "full_name": "Общество с ограниченной ответственностью Ромашка",
    "inn": "7701234567",
    "kpp": "770101001",
    "ogrn": "1234567890123",
    "legal_address": "г. Москва, ул. Ленина, д. 1",
    "phone": "+7 495 123-45-67",
    "email": "info@romashka.ru",
    "segment": "wholesale",
    "status": "active",
    "is_client": true,
    "is_buyer": true
  },
  "contracts": [
    {
      "number": "Д-2025/001",
      "amount": 1500000.00,
      "date_start": "2025-01-01",
      "date_end": "2026-12-31",
      "status": "active",
      "utilization_pct": 45.00
    }
  ],
  "overdue": {
    "count": 1,
    "total_overdue": 45000.00
  },
  "recent_orders": [
    {
      "number": "ЗК-2026/042",
      "date": "2026-04-15",
      "amount": 340000.00,
      "status": "shipped"
    }
  ],
  "sales_30d": {
    "total": 890000.00,
    "order_count": 8
  }
}
```

---

### Tool 7: `list_active_clients`

Список активных клиентов с ключевыми метриками.

**Endpoint:** `GET /tools/list_active_clients`

**Query parameters:**

| Параметр | Тип | По умолч. | Описание |
|----------|-----|-----------|----------|
| `tenant_id` | UUID | — | **Обязательный** |
| `segment` | string | — | `vip`, `wholesale`, `retail` |
| `has_overdue` | bool | — | Только с просрочками |
| `min_revenue_30d` | float | — | Мин. выручка за 30 дней |
| `limit` | int | 20 | Максимум результатов (≤50) |
| `sort_by` | string | `revenue` | Сортировка: `revenue`, `name`, `overdue` |

**Response `200` (data):**
```json
{
  "clients": [
    {
      "id": "cp-...",
      "name": "ООО Ромашка",
      "inn": "7701234567",
      "segment": "wholesale",
      "phone": "+7 495 123-45-67",
      "email": "info@romashka.ru",
      "revenue_30d": 890000.00,
      "overdue_count": 1,
      "overdue_sum": 45000.00,
      "order_count_90d": 15
    }
  ],
  "total": 1
}
```

---

## Rate Limiting

| Endpoint | Лимит | Окно |
|----------|-------|------|
| `GET /health`, `GET /ready` | 10 req/s | 1 секунда |
| `GET /api/admin/*` | 100 req | 1 минута (на tenant) |
| `POST /api/admin/*` | 30 req | 1 минута (на tenant) |
| `GET /tools/*` | 200 req | 1 минута (на tenant) |

При превышении лимита возвращается `429 Too Many Requests` с заголовком `Retry-After`.
