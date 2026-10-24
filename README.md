# 🎫 Event Service — Telegram-бот бронирования билетов

Telegram-бот для просмотра расписания мероприятий и оформления заявок на бронирование билетов. Поддерживает категории событий, пошаговое бронирование с расчётом стоимости, выбор способа оплаты (заглушка), подтверждение броней администратором и отзывы пользователей.

---

## 📋 Содержание

- [Возможности](#-возможности)
- [Стек технологий](#-стек-технологий)
- [Структура проекта](#-структура-проекта)
- [Быстрый старт](#-быстрый-старт)
- [Настройка `.env`](#-настройка-env)
- [Команды бота](#-команды-бота)
- [Схема базы данных](#-схема-базы-данных)
- [Настройка прокси](#-настройка-прокси)
- [Деплой на VDS](#-деплой-на-vds)
- [Резервное копирование](#-резервное-копирование)
- [Обновление на сервере](#-обновление-на-сервере)
- [Устранение неполадок](#-устранение-неполадок)
- [Лицензия](#-лицензия)

---

## ✨ Возможности

- **📅 Расписание мероприятий** — просмотр с фильтром по категориям (концерты, фильмы, спектакли, дегустации).
- **🎫 Бронирование билетов** — пошаговый FSM-сценарий: выбор события → количество билетов → пожелания → подтверждение → способ оплаты.
- **💰 Расчёт стоимости** — итоговая сумма = цена билета × количество.
- **💳 Способы оплаты** — онлайн / наличными (заглушка, выбор сохраняется в БД).
- **🎫 Мои брони** — просмотр статусов (⏳ ожидает / ✅ подтверждена / ❌ отменена) и отмена.
- **⭐ Отзывы** — оценка 1–5 и текстовый отзыв по подтверждённым броням.
- **🛠 Админ-панель** — команда `/admin` для подтверждения броней (доступ по `ADMIN_IDS`).
- **🔌 Поддержка прокси** — включается/отключается через `.env` (socks5h / socks5 / http).
- **✅ Валидация ввода** — защита от не-чисел, отрицательных значений и превышения свободных мест.

---

## 🛠 Стек технологий

| Компонент | Технология |
|---|---|
| Язык | Python 3.10+ |
| Telegram API | [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) |
| База данных | SQLite |
| Конфигурация | python-dotenv |
| Прокси (опционально) | PySocks |
| Деплой | systemd + Ubuntu 22.04 |

---

## 📁 Структура проекта

```
event-service/
├── bot.py             # точка входа, все хендлеры бота
├── config.py          # настройки из .env (токен, прокси и т.д.)
├── database.py        # работа с SQLite (CRUD)
├── keyboards.py       # клавиатуры (inline + reply)
├── seed.py            # наполнение БД примерами мероприятий
├── requirements.txt
├── .env               # секреты (НЕ коммитится)
├── .env.example       # шаблон переменных окружения
├── .gitignore
├── README.md
└── tickets.db         # создаётся автоматически
```

---

## 🚀 Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/USERNAME/event-service.git
cd event-service
```

### 2. Создать виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows
```

### 3. Установить зависимости

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Получить токен бота

1. Открой Telegram → **@BotFather** → `/newbot`.
2. Придумай имя и username (должен заканчиваться на `bot`).
3. Скопируй токен вида `123456789:AAH...`.
4. Свой Telegram ID узнай у **@userinfobot** — пригодится для `ADMIN_IDS`.

### 5. Настроить `.env`

```bash
cp .env.example .env
nano .env
```

Заполни минимум `BOT_TOKEN` и `ADMIN_IDS` (см. раздел [Настройка `.env`](#-настройка-env)).

### 6. Инициализировать БД примерами

```bash
python seed.py
```

### 7. Запустить бота

```bash
python bot.py
```

В консоли увидишь:

```
[proxy] Отключён — прямое соединение
Бот запущен...
```

Открой своего бота в Telegram и отправь `/start`.

---

## ⚙️ Настройка `.env`

| Переменная | Обяз. | По умолчанию | Описание |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | — | Токен бота от @BotFather |
| `DB_PATH` | ❌ | `tickets.db` | Путь к файлу SQLite |
| `ADMIN_IDS` | ❌ | пусто | Telegram ID администраторов через запятую |
| `USE_PROXY` | ❌ | `false` | Включает прокси (`true`/`false`) |
| `PROXY_TYPE` | ❌ | `socks5h` | `socks5h` / `socks5` / `http` / `https` |
| `PROXY_HOST` | ❌ | `127.0.0.1` | Адрес прокси |
| `PROXY_PORT` | ❌ | `10808` | Порт прокси |

**Пример `.env`:**

```env
BOT_TOKEN=123456789:AAH_your_real_token_here
DB_PATH=tickets.db
ADMIN_IDS=111111111,222222222

USE_PROXY=false
PROXY_TYPE=socks5h
PROXY_HOST=127.0.0.1
PROXY_PORT=10808
```

---

## 💬 Команды бота

| Команда / кнопка | Описание |
|---|---|
| `/start` | Регистрация (имя + телефон) и главное меню |
| `/admin` | Список pending-броней с кнопкой подтверждения (только для `ADMIN_IDS`) |
| 📅 Расписание | Категории → список мероприятий → карточка события |
| 🎫 Мои брони | Список броней со статусом, кнопка «Отменить» |
| ⭐ Оставить отзыв | Выбор подтверждённой брони → оценка → текст |
| ℹ️ Помощь | Краткая справка |

**Кнопки в карточке мероприятия:**
- `🎫 Забронировать` — начало FSM бронирования
- `⭐ Отзывы` — средняя оценка и последние 10 отзывов
- `⬅️ К списку` — возврат к списку событий

---

## 🗄 Схема базы данных

### `users` — пользователи

| Поле | Тип | Описание |
|---|---|---|
| `user_id` | INTEGER PK | Telegram ID |
| `username` | TEXT | @username |
| `full_name` | TEXT | Имя |
| `phone` | TEXT | Телефон |
| `created_at` | TEXT | Дата регистрации |

### `events` — мероприятия

| Поле | Тип | Описание |
|---|---|---|
| `id` | INTEGER PK | ID |
| `title` | TEXT | Название |
| `category` | TEXT | `concert` / `movie` / `theater` / `tasting` |
| `date` | TEXT | Дата и время |
| `price` | REAL | Цена за билет |
| `total_seats` | INTEGER | Всего мест |
| `booked_seats` | INTEGER | Занято мест |
| `description` | TEXT | Описание |

### `bookings` — брони

| Поле | Тип | Описание |
|---|---|---|
| `id` | INTEGER PK | ID брони |
| `user_id` | INTEGER FK | Кто бронирует |
| `event_id` | INTEGER FK | Мероприятие |
| `guests` | INTEGER | Количество билетов |
| `notes` | TEXT | Пожелания |
| `total_price` | REAL | Итоговая стоимость |
| `payment_method` | TEXT | `online` / `cash` |
| `status` | TEXT | `pending` / `confirmed` / `cancelled` |
| `confirmed_by_organizer` | INTEGER | 0/1 — подтверждено организатором |
| `created_at` | TEXT | Дата создания |

### `reviews` — отзывы

| Поле | Тип | Описание |
|---|---|---|
| `id` | INTEGER PK | ID |
| `user_id` | INTEGER FK | Автор |
| `event_id` | INTEGER FK | Мероприятие |
| `rating` | INTEGER | Оценка 1–5 |
| `text` | TEXT | Текст отзыва |
| `created_at` | TEXT | Дата |

---

## 🔌 Настройка прокси

Прокси нужен, если Telegram API недоступен напрямую (например, работаешь из страны с блокировкой). На VDS обычно **не нужен**.

**Локально с прокси** (например, через V2Ray/Clash на порту 10808):

```env
USE_PROXY=true
PROXY_TYPE=socks5h
PROXY_HOST=127.0.0.1
PROXY_PORT=10808
```

При запуске в консоли будет:

```
[proxy] Включён: socks5h://127.0.0.1:10808
```

**На сервере (без прокси):**

```env
USE_PROXY=false
```

```
[proxy] Отключён — прямое соединение
```

> ⚠️ Если `USE_PROXY=true`, но прокси не запущен — бот не сможет подключиться к Telegram API. Для работы SOCKS обязателен пакет `PySocks` (уже включён в `requirements.txt`).

---

## 🖥 Деплой на VDS

### Требования к серверу

- Ubuntu 22.04 LTS (минимум 1 CPU, 1 GB RAM, 10 GB SSD).
- Открытый порт 22 (SSH).

### 1. Первичная настройка сервера

```bash
ssh root@IP_СЕРВЕРА

apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git nano ufw

adduser botuser
usermod -aG sudo botuser

ufw allow OpenSSH
ufw enable

su - botuser
```

### 2. Клонирование проекта

```bash
cd ~
git clone https://github.com/USERNAME/event-service.git
cd event-service

cp .env.example .env
nano .env                # вписать BOT_TOKEN, ADMIN_IDS, USE_PROXY=false
chmod 600 .env
```

### 3. Установка зависимостей и БД

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

python seed.py
```

### 4. Автозапуск через systemd

Создать unit-файл:

```bash
sudo nano /etc/systemd/system/event-service.service
```

Содержимое:

```ini
[Unit]
Description=Telegram Event Service Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/event-service
Environment="PATH=/home/botuser/event-service/venv/bin"
ExecStart=/home/botuser/event-service/venv/bin/python /home/botuser/event-service/bot.py
Restart=always
RestartSec=5
StandardOutput=append:/home/botuser/event-service/bot.log
StandardError=append:/home/botuser/event-service/bot.log

[Install]
WantedBy=multi-user.target
```

Активировать и запустить:

```bash
sudo systemctl daemon-reload
sudo systemctl enable event-service
sudo systemctl start event-service
sudo systemctl status event-service
```

Смотреть логи в реальном времени:

```bash
tail -f ~/event-service/bot.log
```

### 5. Проверка после деплоя

- Бот отвечает на `/start`.
- Работает расписание, бронирование, «Мои брони».
- `/admin` показывает новые заявки.
- Бот пережил перезагрузку сервера (`sudo reboot`, затем снова `/start`).

---

## 💾 Резервное копирование

Простой cron-скрипт (ежедневно в 03:00):

```bash
mkdir -p ~/backup
crontab -e
```

Добавить строку:

```cron
0 3 * * * cp /home/botuser/event-service/tickets.db /home/botuser/backup/tickets_$(date +\%F).db
```

Восстановление:

```bash
sudo systemctl stop event-service
cp ~/backup/tickets_2024-08-15.db ~/event-service/tickets.db
sudo systemctl start event-service
```


---

## 🔄 Обновление на сервере

```bash
cd ~/event-service
git pull
source venv/bin/activate
pip install -r requirements.txt    # если менялись зависимости
sudo systemctl restart event-service
sudo systemctl status event-service
```

---

## 🩺 Устранение неполадок

| Проблема | Причина / Решение |
|---|---|
| `InvalidSchema: Missing dependencies for SOCKS support` | Установи `PySocks`: `pip install PySocks` |
| Бот молчит после запуска | Проверь `bot.log`. Если `USE_PROXY=true` и прокси не работает — переключи на `false` |
| `telebot.apihelper.ApiTelegramException: 401 Unauthorized` | Неверный `BOT_TOKEN` в `.env` |
| `sqlite3.OperationalError: unable to open database file` | Проверь права на папку проекта и путь в `DB_PATH` |
| Не приходят уведомления админу | Пользователь не нажал `/start` у бота; ID неверный |
| `422 Repository creation failed` на GitHub | Убери «невидимые» символы в поле Description или оставь его пустым |
| `Author identity unknown` при коммите | `git config --global user.name "..."` и `git config --global user.email "..."` |

Логи systemd:

```bash
journalctl -u event-service -f
```

---


---

## 📄 Лицензия

MIT — используй свободно, указывай авторство.
