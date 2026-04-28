# messages_ru.py — Все строковые константы на русском

# Общие сообщения
TENANT_ID_REQUIRED = "X-Tenant-Id заголовок обязателен"
TENANT_NOT_FOUND = "Арендатор не найден"
INTERNAL_ERROR = "Внутренняя ошибка сервера"
NOT_FOUND = "Ресурс не найден"
VALIDATION_ERROR = "Проверьте правильность заполнения полей"
UNAUTHORIZED = "Требуется аутентификация"
FORBIDDEN = "Недостаточно прав"
RATE_LIMITED = "Слишком много запросов. Попробуйте позже"

# Синхронизация
SYNC_ALREADY_RUNNING = "Синхронизация уже выполняется"
SYNC_TRIGGERED = "Синхронизация запущена"
SYNC_CONNECTION_OK = "Подключение к 1С успешно установлено"
SYNC_CONNECTION_FAILED = "Не удалось подключиться к серверу 1С"
SYNC_LOG_EMPTY = "История синхронизаций пуста"
SYNC_STATUS_OK = "Синхронизация работает"
SYNC_STATUS_ERROR = "Ошибка синхронизации"
SYNC_STATUS_RUNNING = "Синхронизация выполняется..."

# Watchers
WATCHER_CREATED = "Watcher успешно создан"
WATCHER_UPDATED = "Watcher успешно обновлён"
WATCHER_DELETED = "Watcher успешно удалён"
WATCHER_NOT_FOUND = "Watcher не найден"
WATCHER_CRON_INVALID = "Некорректное cron-выражение"
WATCHER_SNOOZED = "Watcher приостановлен на {hours} ч."
WATCHER_NO_ALERTS = "Нет алертов за последние 24 часа"
WATCHERS_EMPTY = "Нет watchers. Создайте первый watcher для отслеживания."

# Tools
TOOL_NOT_FOUND = "Tool не найден"
TOOL_ERROR = "Ошибка выполнения tool"
TOOL_TIMEOUT = "Tool не ответил за отведённое время"

# Подключение 1С
CONNECTION_SETTINGS_SAVED = "Настройки сохранены"
CONNECTION_TEST_SUCCESS = "Подключение успешно"
CONNECTION_TEST_FAILED = "Ошибка подключения"
CONNECTION_ACTIVE = "Подключение активно"
CONNECTION_DISCONNECTED = "Подключение не настроено"

# Async tasks
ASYNC_TASK_STARTED = "Задача поставлена в очередь"
CORRELATION_ID_LOG = "correlation_id"

# Имена сущностей
ENTITY_ORDER = "Заказы"
ENTITY_INVOICE = "Счета"
ENTITY_PAYMENT = "Платежи"
ENTITY_CONTRACT = "Договоры"
ENTITY_COUNTERPARTY = "Контрагенты"
ENTITY_PRODUCT = "Товары"
ENTITY_EMPLOYEE = "Сотрудники"
ENTITY_FULL = "Полная синхронизация"

ENTITY_LABELS = {
    "orders": ENTITY_ORDER,
    "invoices": ENTITY_INVOICE,
    "payments": ENTITY_PAYMENT,
    "contracts": ENTITY_CONTRACT,
    "counterparties": ENTITY_COUNTERPARTY,
    "products": ENTITY_PRODUCT,
    "employees": ENTITY_EMPLOYEE,
    "full_reconciliation": ENTITY_FULL,
}
