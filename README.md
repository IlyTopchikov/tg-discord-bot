# Discord ↔ Telegram Events Bot

Discord бот, который по команде `/event` обращается к Telegram-боту
`@FunTimeEventsBot_bot`, получает список текущих ивентов и постит их в Discord.

## Как это работает

```
Пользователь /event в Discord
        ↓
Discord бот (discord.py)
        ↓
Telethon (твой TG аккаунт) → пишет "Текущие ивенты" → @FunTimeEventsBot_bot
        ↓
Ждёт ответа (до 15 сек)
        ↓
Постит ответ в Discord канал embed-ом
```

---

## Шаг 1 — Получи токены

### Discord
1. Зайди на https://discord.com/developers/applications
2. **New Application** → придумай имя
3. Вкладка **Bot** → **Add Bot** → скопируй **Token**
4. Там же включи: `Message Content Intent` (в Privileged Gateway Intents)
5. Вкладка **OAuth2 → URL Generator**: отметь `bot` + права `Send Messages`, `Read Messages`
6. Открой сгенерированную ссылку и добавь бота на свой сервер

### Telegram API
1. Зайди на https://my.telegram.org
2. **API development tools** → создай приложение
3. Сохрани `api_id` и `api_hash`

---

## Шаг 2 — Настрой .env

```bash
cp .env.example .env
```

Открой `.env` и заполни все значения (см. комментарии внутри файла).

Чтобы узнать `DISCORD_CHANNEL_ID`:
- В Discord: Настройки → Расширенные → включи **Режим разработчика**
- Правой кнопкой на нужный канал → **Копировать ID**

---

## Шаг 3 — Авторизуйся в Telegram (один раз, локально)

```bash
pip install -r requirements.txt
python auth_session.py
```

Введи номер телефона и код из Telegram. Появится файл `session.session`.

---

## Шаг 4 — Деплой на Railway

1. Создай аккаунт на https://railway.app
2. **New Project → Deploy from GitHub repo** (или **Empty Project**)
3. Загрузи файлы проекта (включая `session.session`!)
4. В разделе **Variables** добавь все переменные из `.env`
5. Railway сам найдёт `Procfile` и запустит `python bot.py`

> ⚠️ **Важно:** файл `session.session` содержит доступ к твоему TG-аккаунту.
> Не публикуй его в открытых репозиториях!

### Альтернатива — запуск на VPS

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск (рекомендуется через screen или systemd)
screen -S eventbot
python bot.py
# Ctrl+A, D — отсоединиться от screen
```

---

## Использование

В любом канале Discord сервера:
```
/event
```
Бот ответит "⏳ Запрашиваю..." и через несколько секунд запостит ивенты
в канал, указанный в `DISCORD_CHANNEL_ID`.

---

## Возможные проблемы

| Проблема | Решение |
|---|---|
| Бот не отвечает на `/event` | Проверь `DISCORD_TOKEN` и что бот добавлен на сервер |
| "Таймаут: бот TG не ответил" | Увеличь `TG_RESPONSE_WAIT` до 30, или проверь `TG_TRIGGER_MSG` |
| Ошибка авторизации Telegram | Удали `session.session` и запусти `auth_session.py` снова |
| FloodWaitError в TG | Слишком частые запросы — добавь паузу между вызовами `/event` |
