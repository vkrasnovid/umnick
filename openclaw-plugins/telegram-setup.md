# Настройка Telegram-бота для Умник

## 1. Создание бота через BotFather

1. Откройте Telegram, найдите @BotFather
2. Отправьте команду `/newbot`
3. Введите имя: `Умник`
4. Введите username: `umnik_ai_bot` (или другой свободный)
5. Сохраните полученный токен

## 2. Настройка OpenClaw Gateway

Добавьте в конфигурацию OpenClaw:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "agent_id": "umnik",
      "polling": true
    }
  }
}
```

## 3. Команды бота

Через BotFather настройте меню команд:
```
/start — Возможности Умника
/watchers — Активные наблюдатели
/pause — Приостановить наблюдатель
```

## 4. Переменные окружения

Добавьте в .env:
```
TELEGRAM_BOT_TOKEN=your_token_here
OPENCLAW_API_KEY=your_openclaw_key
```
