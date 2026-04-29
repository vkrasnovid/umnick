# Умник — AI Operations Platform для бизнеса на 1С

> **Статус:** MVP — готов к деплою  
> **Версия:** 1.0.0  
> **Лицензия:** Проприетарная  
> **GitHub:** https://github.com/vkrasnovid/umnick

---

## Проблема

Владельцы малого и среднего бизнеса работают в 1С, но **не видят критических сигналов** вовремя:

- Просроченные платежи клиентов обнаруживают через недели
- Остатки товаров падают ниже минимума — а закуп не сделан
- Падение выручки замечают только в конце месяца
- Каждый отчёт — ручная выгрузка из 1С в Excel

**Умник решает эту проблему:** AI-агент сам мониторит данные из 1С, проактивно алертит о проблемах и отвечает на вопросы на естественном языке.

---

## Решение

Умник — это AI Operations Platform, которая:

1. **Автоматически синхронизирует данные** из 1С (КА2, УТ, БП) через OData
2. **Хранит унифицированную модель** в PostgreSQL (контрагенты, договоры, заказы, счета, платежи, товары, сотрудники)
3. **Предоставляет 7 бизнес-инструментов** (tools) для анализа данных
4. **Проактивно алертит** о проблемах через Telegram (watchers)
5. **Отвечает на вопросы** на естественном русском языке через Telegram-бота

---

## Архитектура

### Четыре слоя

```
┌──────────────────────────────────────────────────────────────┐
│              👤 Conversational Interface                      │
│          (Telegram Bot — OpenClaw Agent)                      │
│  Пользователь → Telegram → OpenClaw → Tools → Ответ          │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│              🔧 Tool Library (7 tools)                        │
│  get_contract_utilization  │  get_overdue_payments            │
│  get_client_activity      │  query_sales                     │
│  find_contracts           │  get_client_360                  │
│  list_active_clients      │                                   │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│              ⏰ Proactive Engine                               │
│  Watcher проверяет условие → вызывает tool → алерт в Telegram │
│  Deals (daily@9am) │ LowStock (hourly) │ Revenue (weekly)    │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│              🏗️ Data Bridge                                   │
│  1С → OData → Sync Workers → PostgreSQL                       │
│  Orders: 5min │ Contracts: 15min │ Products: 60min            │
└──────────────────────────────────────────────────────────────┘
```

### Технологический стек

| Компонент | Технология |
|-----------|-----------|
| **Data Bridge (Sync)** | Python 3.12, FastAPI, Celery, SQLAlchemy 2.0 |
| **Tool Library** | Python 3.12, FastAPI, SQLAlchemy |
| **Proactive Engine** | Celery Beat, Redis |
| **Conversational** | OpenClaw Agent, TypeScript Plugin |
| **Admin UI** | React 18, shadcn/ui, Tailwind CSS, Vite |
| **База данных** | PostgreSQL 16 |
| **Брокер / Кэш** | Redis 7 |
| **Инфраструктура** | Docker Compose |
| **Мониторинг** | OpenTelemetry + Prometheus + Grafana |

---

## Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone git@github.com:vkrasnovid/umnick.git
cd umnick

# 2. Настроить окружение
cp .env.example .env
# Отредактировать .env: пароли, ключи, подключения

# 3. Запустить все сервисы
cd docker
docker compose up -d --build

# 4. Проверить работоспособность
curl http://localhost:8085/health    # Bridge API
curl http://localhost:8086/health    # Tools API

# Ожидаемый ответ:
# {"status":"ok","service":"bridge"}
# {"status":"ok","service":"tool-runtime"}
```

---

## Доступ к сервисам

| Сервис | Внутренний порт | Хост-порт | Назначение |
|--------|----------------|-----------|------------|
| **Bridge API** | 8000 | **8085** | Admin API, синхронизация, health checks |
| **Tools API** | 8001 | **8086** | Tool Runtime для бизнес-запросов |
| PostgreSQL | 5432 | 5432 | База данных (internal only) |
| Redis | 6379 | 6379 | Кэш и Celery broker (internal only) |

---

## 7 инструментов (Tools)

| № | Tool | Назначение | Через Telegram |
|---|------|-----------|----------------|
| 1 | `get_contract_utilization` | Исполнение договора — сумма, процент, остаток | «Покажи исполнение договора №123» |
| 2 | `get_overdue_payments` | Просроченные платежи клиентов | «Кто должен деньги?» |
| 3 | `get_client_activity` | Активность клиента за период | «Что делал Иванов в этом месяце?» |
| 4 | `query_sales` | Анализ продаж: выручка, динамика | «Какие продажи на этой неделе?» |
| 5 | `find_contracts` | Поиск договоров по критериям | «Найди договоры до 1 млн» |
| 6 | `get_client_360` | Полная карточка клиента 360° | «Всё о Ромашке» |
| 7 | `list_active_clients` | Список активных клиентов с метриками | «Покажи всех активных клиентов» |

Каждый tool:
- Принимает `tenant_id` из контекста сессии OpenClaw (не от пользователя)
- Возвращает структурированный JSON `{ success, data, error? }`
- Использует только параметризованные SQL-запросы
- Идемпотентен (только чтение, без записи в MVP)

---

## 3 наблюдателя (Watchers)

| Watcher | Расписание | Условие | Действие |
|---------|-----------|---------|----------|
| **daily_overdue_check** | Будни, 9:00 | Просрочки > 0 | 📋 Отчёт по просрочкам |
| **low_stock_alert** | Каждый час | Остаток < минимума | ⚠️ Предупреждение о запасах |
| **weekly_revenue_drop** | Понедельник, 10:00 | Падение > 20% | 📊 Сигнал о падении продаж |

Алерты отправляются в Telegram по настроенным шаблонам с дедупликацией (одинаковые алерты не дублируются).

---

## Multi-tenant изоляция

Умник поддерживает несколько арендаторов (tenant) в одной инсталляции:

1. **tenant_id** в каждой строке всех таблиц БД
2. **X-Tenant-Id header** — обязателен для всех API-запросов
3. **Все SQL-запросы** фильтруются по `tenant_id`
4. **Row-Level Security (RLS)** в PostgreSQL — второй рубеж защиты
5. **OpenClaw сессия** содержит `tenantId` в метаданных

Каждый клиент работает только со своими данными — данные других арендаторов недоступны.

---

## Документация

| Документ | Описание |
|----------|---------|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Полная архитектурная спецификация (4 слоя, БД, tools, watchers, безопасность) |
| [`API.md`](./API.md) | API Reference для всех эндпоинтов Bridge Admin API и Tools API |
| [`DEPLOYMENT.md`](./DEPLOYMENT.md) | DevOps-гайд: деплой, конфигурация, troubleshoooting |
| [`DESIGN_SPEC.md`](./DESIGN_SPEC.md) | Дизайн-система: UI, Telegram-шаблоны, UX |
| [`CODE_REVIEW.md`](./CODE_REVIEW.md) | Отчёт code review |
| [`QA_REPORT.md`](./QA_REPORT.md) | Результаты QA-тестирования |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Как добавить tool, watcher, поддержку 1С |
| [`openclaw-plugins/telegram-setup.md`](./openclaw-plugins/telegram-setup.md) | Настройка Telegram-бота |

---

## Структура репозитория

```
/opt/umnick/
├── bridge/              # Data Bridge (FastAPI + Celery)
├── tools/               # Tool Library (FastAPI)
├── engine/              # Proactive Engine (Celery)
├── admin/               # Admin UI (React SPA)
├── openclaw-plugins/    # OpenClaw Plugin (TypeScript)
├── docker/              # Docker Compose + Dockerfiles
├── scripts/             # init_db.sql, seed_data.sql
└── docs/                # Документация
```

---

## Безопасность

- **SQL-инъекции:** Только параметризованные запросы — никаких f-strings в SQL
- **Credentials:** OData-пароли шифруются AES-256-GCM, ключ в ENVIRONMENT
- **RLS:** Row-Level Security как второй рубеж multi-tenant изоляции
- **CORS:** Разрешён только origin Admin UI
- **Rate limiting:** 100 запросов/мин на tenant для admin API
- **HTTPS:** Терминация на reverse proxy (nginx/traefik)
- **LLM privacy:** Отправляются только запрошенные данные, готовность к on-prem LLM

---

## Требования к окружению

- Docker Engine 24+
- Docker Compose v2
- Python 3.12+
- Node.js 22+ (для плагинов и Admin UI)

---

## Лицензия

Проприетарная. © 2026 Dream Team. Все права защищены.
