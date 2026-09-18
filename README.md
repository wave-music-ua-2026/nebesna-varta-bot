# Небесна Варта | Україна — Telegram alert bot

Бот читає активні цивільні тривоги з alerts.in.ua і публікує зміни стану в `@NebesnaVartaUA`.

## 1. Безпека
Токен Telegram, який був показаний на скриншоті, потрібно відкликати в BotFather і використовувати новий. Не публікуйте `.env`.

## 2. Налаштування
Потрібен Python 3.10+.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```

Відкрийте `.env` і вставте новий BotFather token та alerts.in.ua token. Бот `@SkyGuardUkraine_bot` має бути адміністратором каналу з правом публікувати повідомлення.

## 3. Запуск
```bash
python bot.py
```

Під час першого запуску бот лише запам'ятовує поточні активні тривоги, щоб не засипати канал старими повідомленнями. Далі публікуються тільки зміни.

## Важливо
- Джерело: `GET https://api.alerts.in.ua/v1/alerts/active.json`, Bearer token.
- За замовчуванням перевірка кожні 10 секунд (6 запитів/хв), що не перевищує показаний у документації soft limit 8–10 запитів/хв.
- Обробляються HTTP 304, 401/403, 429, мережеві помилки та exponential backoff.
- Ця версія публікує типи загроз, які безпосередньо повертає active-alerts API. Вона не вигадує маршрути/координати ракет чи БпЛА.
- Канал не повинен замінювати офіційні системи оповіщення.

## 24/7
Для постійної роботи розгорніть каталог на VPS/хостингу як worker/background process з командою `python bot.py` і додайте ті самі environment variables у панелі хостингу.
