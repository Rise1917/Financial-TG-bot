<div align="center">
  <a href="#-русский">🇷🇺 Русский</a> | <a href="#-english">🇬🇧 English</a>
</div>

---

# 🇷🇺 Русский

## Финансовый Telegram-бот (KZT)

Персональный финансовый помощник на Python с учётом расходов в тенге, месячной статистикой и курсом валют.

### Возможности

- **Добавление расходов** — категории: Продукты, Кафе, Транспорт, Жильё, Развлечения, Банк
- **Загрузка выписок** — Kaspi, Halyk, Freedom, Jusan, ЦентрКредит (Excel, PDF, CSV, формат 1C)
- **Сохранение выписок** — все операции в БД, расходы автоматически попадают в статистику
- **Удаление выписок** — с подтверждением; убирает операции и связанные расходы из статистики
- **Статистика** — сумма трат за текущий месяц по категориям
- **Курс валют** — актуальный курс USD, EUR и RUB к KZT (API [open.er-api.com](https://open.er-api.com))

### Структура проекта

```text
├── main.py                 # Точка входа
├── bot/
│   ├── config.py           # Конфигурация и .env
│   ├── database.py         # SQLite (aiosqlite)
│   ├── keyboards.py        # Инлайн-клавиатуры
│   ├── states.py           # FSM-состояния
│   ├── handlers/           # Обработчики команд и кнопок
│   └── services/
│       ├── currency.py     # Запросы к API курсов
│       └── statements/     # Парсеры банковских выписок
├── data/                   # База данных (создаётся автоматически)
├── requirements.txt
└── .env                    # Токен бота (создайте вручную)
```

### Быстрый старт

**1. Клонирование и виртуальное окружение**

```bash
cd "Финансовый бот тг"
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

**2. Установка зависимостей**

```bash
pip install -r requirements.txt
```

**3. Настройка `.env`**

Скопируйте пример и укажите токен от [@BotFather](https://t.me/BotFather):

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Содержимое `.env`:
```env
BOT_TOKEN=ваш_токен_от_BotFather
```

**4. Запуск бота**

```bash
python main.py
```
В консоли появятся логи работы бота. Откройте Telegram и отправьте боту команду `/start`.

### Загрузка банковской выписки

1. В приложении банка скачайте выписку (Excel, PDF или формат 1C).
2. В боте нажмите **«Загрузить выписку»** → выберите банк.
3. Отправьте файл как документ (скрепка → Файл).

Бот сохранит выписку в таблицу `statements`, все операции — в `statement_transactions`, а расходы автоматически добавит в общую статистику. Повторная загрузка того же файла не дублирует данные.

**Kaspi Gold PDF:** бот сам конвертирует PDF внутри кода — извлекает таблицы со всех страниц, отбрасывает баланс и курсы валют, собирает операции. Конвертировать PDF в Excel вручную не обязательно.

| Банк | Рекомендуемый формат |
|------|----------------------|
| Kaspi Gold | **PDF напрямую** (рекомендуется) или Excel |
| Halyk | Excel или 1C (.txt) |
| Freedom, Jusan, ЦентрКредит | Excel, CSV или 1C |

### Команды

| Команда   | Описание              |
|-----------|-----------------------|
| `/start`  | Приветствие и меню    |
| `/menu`   | Вернуть главное меню  |

### Удаление выписки

1. **Мои выписки** → нажмите на нужную выписку (🗑)
2. Подтвердите удаление

Удаляются операции выписки и импортированные расходы. Ручные записи остаются.

### Тесты

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Подробный разбор архитектуры: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

### Технологии

- [aiogram 3.x](https://docs.aiogram.dev/) — Telegram Bot API
- [aiosqlite](https://github.com/omnilib/aiosqlite) — асинхронная SQLite
- [aiohttp](https://docs.aiohttp.org/) — HTTP-запросы к API курсов
- [python-dotenv](https://github.com/theskumar/python-dotenv) — переменные окружения

---

# 🇬🇧 English

## Financial Telegram Bot (KZT)

A personal financial assistant in Python for tracking expenses in KZT (Kazakhstani Tenge), viewing monthly statistics, and tracking currency exchange rates.

### Features

- **Add Expenses** — categories: Groceries, Cafes, Transport, Housing, Entertainment, Bank
- **Upload Bank Statements** — Kaspi, Halyk, Freedom, Jusan, CenterCredit (Excel, PDF, CSV, 1C format)
- **Save Statements** — all transactions are saved to the database, expenses automatically count towards statistics
- **Delete Statements** — with confirmation; removes transactions and associated expenses from statistics
- **Statistics** — total spending for the current month grouped by category
- **Exchange Rates** — current rates for USD, EUR, and RUB against KZT (API [open.er-api.com](https://open.er-api.com))

### Project Structure

```text
├── main.py                 # Entry point
├── bot/
│   ├── config.py           # Configuration and .env loading
│   ├── database.py         # SQLite (aiosqlite) queries
│   ├── keyboards.py        # Inline keyboards
│   ├── states.py           # FSM states
│   ├── handlers/           # Command and callback handlers
│   └── services/
│       ├── currency.py     # Currency API requests
│       └── statements/     # Bank statement parsers
├── data/                   # Database folder (created automatically)
├── requirements.txt
└── .env                    # Bot token (create manually)
```

### Quick Start

**1. Clone and Virtual Environment**

```bash
cd "Финансовый бот тг"
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

**2. Install Dependencies**

```bash
pip install -r requirements.txt
```

**3. Configure `.env`**

Copy the example file and provide your token from [@BotFather](https://t.me/BotFather):

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

`.env` content:
```env
BOT_TOKEN=your_token_from_BotFather
```

**4. Run the Bot**

```bash
python main.py
```
Bot logs will appear in the console. Open Telegram and send the `/start` command to your bot.

### Uploading a Bank Statement

1. Download a statement in your bank's app (Excel, PDF, or 1C format).
2. In the bot, tap **"Upload statement"** → choose your bank.
3. Send the file as a document (paperclip → File).

The bot will save the statement to the `statements` table, all transactions to `statement_transactions`, and automatically include expenses in your total stats. Uploading the same file again will not duplicate the data.

**Kaspi Gold PDF:** the bot parses the PDF internally — extracts tables from all pages, skips the balance and exchange rates, and gathers transactions. No need to manually convert PDF to Excel.

| Bank | Recommended Format |
|------|----------------------|
| Kaspi Gold | **PDF directly** (recommended) or Excel |
| Halyk | Excel or 1C (.txt) |
| Freedom, Jusan, CenterCredit | Excel, CSV or 1C |

### Commands

| Command   | Description              |
|-----------|-----------------------|
| `/start`  | Greeting and main menu |
| `/menu`   | Return to the main menu |

### Deleting a Statement

1. **My statements** → tap the desired statement (🗑)
2. Confirm deletion

This deletes the statement operations and imported expenses. Manually added records remain untouched.

### Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Detailed architecture breakdown (in Russian): [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

### Technologies

- [aiogram 3.x](https://docs.aiogram.dev/) — Telegram Bot API
- [aiosqlite](https://github.com/omnilib/aiosqlite) — Asynchronous SQLite
- [aiohttp](https://docs.aiohttp.org/) — HTTP requests for currency API
- [python-dotenv](https://github.com/theskumar/python-dotenv) — Environment variables
