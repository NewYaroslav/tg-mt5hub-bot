# 🔒 Руководство по защите сервера MT5Hub

## Цель:

* Установка nginx как фронт для aiohttp
* Ограничение частоты запросов (глобально и для отдельных маршрутов)
* Защита fail2ban
* Файрвол ufw

## Параметры:

* Порт MT5HUB: `9125`.
* Порт OpenSSH: `44123`.
* Пример IP: 123.123.123.123
* Пример запроса: [http://123.123.123.123:9125/api/v1/bot/heartbeat](http://123.123.123.123:9125/api/v1/bot/heartbeat)

---

## Шаг 1: Установка nginx

```bash
sudo apt update
sudo apt install nginx
```

## Шаг 2: Создаем nginx config

Открой основной конфиг nginx.conf:

```bash
sudo nano /etc/nginx/nginx.conf
```

Найди блок http { ... } и внутри него добавь:

```nginx
limit_req_zone $http_x_bot_id zone=bot_limit:10m rate=2r/s;        # лимит по bot-id
limit_req_zone $binary_remote_addr zone=public_limit:1m rate=5r/m; # лимит по IP
```

* `bot_limit` - ограничения частоты запросов по `x-bot-id`
* `public_limit` - отдельный лимит для `/api/v1/last_balance`;

Примерно так должно выглядеть:

```nginx
http {
    limit_req_zone $http_x_bot_id zone=bot_limit:10m rate=2r/s;
    limit_req_zone $binary_remote_addr zone=public_limit:1m rate=5r/m;

    sendfile on;
    tcp_nopush on;
    types_hash_max_size 2048;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Включаем сайты
    include /etc/nginx/sites-enabled/*;
}
```

### Настройка сайта mt5hub:

Создай файл:

```bash
sudo nano /etc/nginx/sites-available/mt5hub
```

Вставь:

```nginx
server {
    listen 9125;
    server_name 123.123.123.123;

	# Ограничение по x-bot-id для всех остальных
    location / {
		proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

		limit_req zone=bot_limit burst=15 nodelay;
    }
	
	# Ограничение по IP для публичного запроса — /api/v1/last_balance
	location = /api/v1/last_balance {
		proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		limit_req zone=public_limit burst=2 nodelay;
    }

	# Логи
    access_log /var/log/nginx/mt5hub_access.log;
    error_log  /var/log/nginx/mt5hub_error.log;
}
```

* перенаправление запросов на aiohttp-сервер (`127.0.0.1:8080`)

После изменений если nginx уже включен:

```bash
sudo nginx -t # проверить конфиг
sudo systemctl reload nginx
```

Иначе включаем сайт и nginx:

```bash
sudo ln -s /etc/nginx/sites-available/mt5hub /etc/nginx/sites-enabled/mt5hub
```

И делаем проверку и перезапуск

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Шаг 3: Файрвол UFW

```bash
sudo apt install ufw -y
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 9125/tcp  # Порт MT5HUB
sudo ufw allow 44123/tcp # SSH порт (измененный)
sudo ufw allow 8181/tcp  # Python API, если внешний
sudo ufw enable
sudo ufw status
```

---

## Шаг 5: Установка и настройка fail2ban

```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

Создай кастомный конфиг, чтобы сохранить локальные изменения:

```bash
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```

Затем отредактируй `/etc/fail2ban/jail.local`:

```ini
[sshd]
enabled = true
port    = 44123
logpath = /var/log/auth.log
backend = systemd
maxretry = 5
bantime = 600
findtime = 300
```

Это позволит ограничить неудачные подключения по SSH.

Рестарт и проверка:

```bash
sudo systemctl restart fail2ban
sudo fail2ban-client status sshd
```

---

## Шаг 6: Фильтр для 429 (nginx flood)

Создать фильтр:

```bash
sudo nano /etc/fail2ban/filter.d/nginx-req-limit.conf
```

Вставить:

```ini
[Definition]
failregex = ^<HOST> -.*"(GET|POST|HEAD).*" 429 .*$
ignoreregex =
```

Открыть файл `jail.local`:

```bash
sudo nano /etc/fail2ban/jail.local
```

Добавить:

```ini
[nginx-req-limit]
enabled = true
port = 9125
filter = nginx-req-limit
logpath = /var/log/nginx/mt5hub_access.log
maxretry = 10
findtime = 10
bantime = 600
```

fail2ban будет читать файл логов `/var/log/nginx/mt5hub_access.log` и банить по IP, если есть ошибка.

Рестарт и проверка:

```bash
sudo systemctl restart fail2ban
sudo fail2ban-client status nginx-req-limit
```

---

## Шаг 9: Тест

```bash
curl http://<IP>:9100/api/v1/bot/heartbeat
# Зацикли 20+ раз и получи 429
```

---

## Готово.

Теперь nginx защищает aiohttp, лимитирует `/api/v1/last_balance` отдельно, а fail2ban банит подозрительные IP.
