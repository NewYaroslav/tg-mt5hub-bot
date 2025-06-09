# tg-mt5hub-bot

Бот-хаб для централизованного учета, контроля и мониторинга торговых роботов (ботов) на платформе MetaTrader 5. Подходит для связки с несколькими ботами, работающими независимо, и обеспечивает:

- сбор сигналов, балансов, статусов;
- управление торговлей (разрешить/запретить);
- визуализацию отчётов через Telegram (*в перспективе*)
- HTTP API для ботов на стороне MT5.

---

## 🚀 Основные возможности

- 🛰️ Получение heartbeat и сигналов от нескольких ботов через HTTP
- 💰 Учёт баланса и профита каждого бота
- 👮 Контроль торговли: разрешить / остановить торговлю на уровне бота
- 📊 Отчёты в Telegram с авто-группировкой по времени
- 🧾 Логирование, шаблоны на Jinja2, модульная архитектура
- 💾 Хранит статус бота и историю в БД.

---

## ⚙️ Конфигурации

### 🔒 `.env` — чувствительные переменные окружения

Файл `.env` содержит приватные переменные окружения:

```
TG_BOT_TOKEN=...          # Токен Telegram бота
ROOT_ADMIN_ID=...         # Telegram ID главного администратора
ADMIN_CHAT_ID=...         # Чат для отчета администратору
FORWARD_CHAT_IDS=...      # Список чатов для дублирования отчетов, через запятую
MT5_SECRET_KEY=...        # Ключ для генерации и проверки HMAC-подписей от MT5-ботов
BALANCE_API_KEY=...       # Ключ для доступа к `/api/v1/last_balance`
LOG_LEVEL=DEBUG           # Уровень логирования (`DEBUG`, `INFO`, `WARNING`)
```

Создай `.env` файл в корне проекта.

### 📁 `config/` — YAML-файлы с параметрами

#### config/ui\_config.yaml

Содержит настройки меню команд и интерфейса Telegram:

```yaml
telegram_menu:
  - command: allow_trade
    description: "▶️ Разрешить торговлю"
  - command: block_trade
    description: "❌ Остановить торговлю"
  ...
```

#### config/auth.yaml

Настройки авторизации и контроля времени:

```yaml
auth:
  login_mismatch_threshold_sec: 10   # максимально допустимая разница login
  max_allowed_delay_sec: 60          # максимальное время без пинга
```

#### config/runtime.yaml

Настройки выполнения:

```yaml
bot_runtime:
  message_batch_delay_sec: 5     # задержка перед отправкой пакета сигналов или балансов
  heartbeat_timeout_sec: 30      # сколько секунд бот считается "в сети" после последнего пинга
  report_delay_sec: 5            # задержка перед отправкой connection report
  bot_ids: [1, 2, 4]             # список ID отслеживаемых ботов
  total_balance_offset: 0.0      # смещение суммы баланса (например, скрыть часть суммы)
  total_profit_offset: 0.0       # смещение общего профита (например, скрыть часть доходности)
http_server:
  port: 8080                     # порт сервера
```

---

## 🛠 Запуск

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

2. Убедитесь, что `.env` и конфиги на месте.
3. Запустите бота:

```bash
python mt5hub_bot.py
```

---

## 📡 HTTP API для MT5 ботов

### 📤 Поддерживаемые HTTP-запросы

- `POST /api/v1/bot/heartbeat` — пинг с данными
- `POST /api/v1/bot/balance` — передача баланса/профита
- `POST /api/v1/bot/signal` — сигналы по рынку

Все запросы: `POST`, формат тела — JSON.
Каждый запрос должен содержать заголовки:

* `x-bot-id`: ID бота
* `x-mt5-login`: номер логина
* `x-mt5-time`: UNIX-время (секунды)
* `x-mt5-signature`: подпись HMAC SHA-256


#### 1. `/api/v1/bot/heartbeat`

```json
{
  "broker": "DemoBroker",
  "leverage": 100
}
```

#### 2. `/api/v1/bot/balance`

```json
{
  "balance": 1234.56,
  "profit": -78.90
}
```

#### 3. `/api/v1/bot/signal`

```json
[
  {
    "timestamp": 1717733449000,
    "symbol": "EURUSD",
    "spread": 8,
    "volume": 0.5,
    "direction": 1
  }
]
```

### 📥 `GET /api/v1/last_balance` — экспорт последних баланса и профита

Этот эндпоинт используется для получения **последней записи** из истории балансов в формате CSV. Подходит для интеграции с Google Sheets, Excel и другими инструментами, поддерживающими `IMPORTDATA()`.

Пример запроса:

```plaintext
GET /api/v1/last_balance?key=YOUR_SECRET_KEY
```

Пример ответа:

```csv
timestamp,datetime,profit,balance
1717920000,2025-06-09 05:00:00,452.17,10234.65
```

Можно использовать в Google Sheets:

```excel
=IMPORTDATA("https://yourhost/api/v1/last_balance?key=YOUR_SECRET_KEY")
```

> 🔐 **Аутентификация:** требуется передача `?key=...` — простой секрет, задаваемый через переменную окружения `BALANCE_API_KEY`.

> ℹ️ **Примечание:** баланс и профит записываются в базу данных только в том случае, если **все боты находятся онлайн** в момент обновления. Это предотвращает искажение общей статистики.


### 🔐 HMAC-подпись

Каждый запрос типа `/api/v1/bot/...` подписан через HMAC (SHA256) с использованием общего секрета (`MT5_SECRET_KEY`).

```python
def generate_signature(secret: str, bot_id: int, login: int, timestamp: int, body: str) -> str:
    bucket = timestamp // 60
    msg = f"{bot_id}:{login}:{bucket}:{body}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
```

* `timestamp` округляется до минуты (`timestamp // 60`) для предотвращения replay-атак и обеспечения гибкости.
* `body` — JSON-строка запроса.
* Проверка осуществляется на сервере в `verify_signature()` аналогично.

---

## 📜 Лицензия

MIT
