# CONTRIBUTING.md — Умник

> Как добавлять новые инструменты, наблюдатели и конфигурации 1С.

---

## Как добавить новый Tool

### 1. SQL-запрос

Добавьте параметризованный запрос в `tools/src/handlers/`. Пример:

```python
# tools/src/handlers/my_new_tool.py
from sqlalchemy import text

QUERY = """
    SELECT ...
    FROM umnick.table
    WHERE tenant_id = :tenant_id
      AND (:param IS NULL OR column = :param)
"""
```

**Правила:**
- Только **параметризованные** запросы — никаких f-strings
- Всегда фильтр по `tenant_id`
- Всегда `LIMIT` для предотвращения перегрузки
- Возврат: `{ "success": true, "data": {...} }`

### 2. Pydantic-схемы

Определите входные параметры и ответ в `tools/src/models/schemas.py`:

```python
from pydantic import BaseModel, Field
from typing import Optional

class MyNewToolParams(BaseModel):
    param1: str = Field(..., description="Описание")
    param2: Optional[int] = Field(None, ge=1, le=365)

class MyNewToolResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[dict] = None
```

### 3. Handler

Зарегистрируйте handler в `tools/src/handlers/__init__.py`:

```python
from .my_new_tool import handle_my_new_tool
```

### 4. API-роутинг

Добавьте эндпоинт в `tools/src/app.py`:

### 5. TypeScript-плагин (OpenClaw)

Создайте файл в `openclaw-plugins/src/tools/`:

```typescript
// openclaw-plugins/src/tools/my-new-tool.ts
import type { ToolSchema, ToolHandler } from '../types';

export const myNewToolSchema: ToolSchema = {
  name: 'my_new_tool',
  description: 'Описание для LLM на русском языке',
  parameters: { ... JSON Schema ... },
};

export const myNewToolHandler: ToolHandler<...> = async (params, context) => {
  // HTTP-запрос к Tool Runtime (порт 8001)
};
```

Зарегистрируйте в `openclaw-plugins/src/index.ts`.

### 6. Обновите документацию

- `API.md` — endpoint для нового tool
- `README.md` — добавьте в таблицу tools

---

## Как добавить новый Watcher

Watcher создаётся через **Bridge Admin API** (`POST /api/admin/watchers`). Код менять не нужно.

Минимальный набор полей:

```json
{
  "name": "new_watcher",
  "schedule": "0 9 * * 1-5",
  "tool_name": "get_overdue_payments",
  "tool_params": { "limit": 10 },
  "condition": "data.summary.total_overdue_count > 0",
  "message_template": "⚠️ *Алерт*\n\nНайдено просрочек: {{data.summary.total_overdue_count}}",
  "recipients": ["-1001234567890"],
  "priority": "normal"
}
```

**Поля:**

| Поле | Описание |
|------|---------|
| `name` | Уникальное имя watcher (на tenant) |
| `schedule` | Cron-выражение |
| `tool_name` | Имя tool для проверки условия |
| `tool_params` | Параметры, передаваемые в tool |
| `condition` | Jinja-like выражение. Если `true` — алерт |
| `message_template` | Jinja2-шаблон сообщения в Telegram |
| `recipients` | Telegram chat_id для отправки |
| `priority` | `low`, `normal`, `high`, `critical` |

**Фильтры шаблонов:** `{{ value | number("0,0.00") }}`, `{{ value | round(1) }}`

Если watcher должен запускаться через Celery Beat, добавьте задачу в `engine/src/celery_app.py`:

```python
app.conf.beat_schedule["check-custom-watcher"] = {
    "task": "engine.tasks.check_due_watchers",
    "schedule": 60.0,
}
```

---

## Как добавить поддержку новой конфигурации 1С

### 1. Настройка OData-маппинга

В `bridge/src/odata/config.py` добавьте конфигурацию для сущности:

```python
ODATA_ENTITIES["products"] = {
    "entity_set": "Catalog_Номенклатура",
    "select": "Ref_Key,Description,Article,BarCode,"
              "СкладОстатки,Цена,ДатаИзменения",
    "orderby": "Date_Time",
}
```

### 2. Модель SQLAlchemy

Добавьте или обновите модель в `bridge/src/models/`:

```python
class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": "umnick"}

    id = Column(UUID, primary_key=True, default=uuid7)
    tenant_id = Column(UUID, nullable=False)
    external_id = Column(String(64), nullable=False)
    # ... поля
```

### 3. Sync Worker

Создайте синхронизатор в `bridge/src/sync/`:

```python
# bridge/src/sync/products.py
from .base import BaseSyncWorker

class ProductsSync(BaseSyncWorker):
    entity_type = "products"
    batch_size = 100

    async def transform(self, raw: dict) -> dict:
        return {
            "external_id": raw["Ref_Key"],
            "name": raw["Description"],
            "article": raw.get("Article"),
            # ... маппинг
        }
```

Зарегистрируйте в `bridge/src/sync/__init__.py`.

### 4. Celery-задача

Добавьте задачу синхронизации в Celery Beat:

```python
# engine/src/celery_app.py
app.conf.beat_schedule["sync-products-hourly"] = {
    "task": "bridge.tasks.sync_products",
    "schedule": 3600.0,
}
```

### 5. RLS-политика

Убедитесь, что для таблицы включена Row-Level Security:

```sql
ALTER TABLE umnick.products ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON umnick.products
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

### 6. Seed-данные

Добавьте тестовые данные в `scripts/seed_data.sql`.

---

## Code Style

### Python

- **Type hints** — обязательны для всех функций и методов
- **SQL** — только через SQLAlchemy или параметризованный `text()`
- **Русские строки** — вынесены в `messages_ru.py` (или i18n-файлы)
- **Максимальная длина строки:** 120 символов
- **Форматирование:** `ruff format`

```python
# ✅ Правильно
async def get_contract_utilization(
    tenant_id: UUID,
    contract_id: UUID | None = None,
) -> ToolResponse:
    result = await session.execute(
        text("SELECT * FROM umnick.contracts WHERE tenant_id = :tenant_id"),
        {"tenant_id": tenant_id},
    )
    ...

# ❌ Неправильно
def get_contract_utilization(tenant_id, contract_id=None):
    result = session.execute(f"SELECT * FROM contracts WHERE id = {contract_id}")
```

### TypeScript

- **TypeScript strict mode**
- **ESLint** с конфигурацией `@typescript-eslint/recommended`
- **Async/await** — без raw promises
- **Имена:** camelCase для переменных, PascalCase для типов

---

## Pull Request Process

1. Создайте ветку: `feature/my-new-tool` или `fix/issue-description`
2. Убедитесь, что:
   - Добавлены тесты (pytest для Python, vitest для TypeScript)
   - Все существующие тесты проходят
   - SQL-запросы параметризованы
   - Документация обновлена
3. Откройте PR в `main`
4. Дождитесь code review
5. После аппрува — squash merge
