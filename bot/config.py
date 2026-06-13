import logging
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден. Создайте файл .env и укажите BOT_TOKEN=ваш_токен"
    )

DATABASE_PATH = BASE_DIR / "data" / "finance.db"

CURRENCY_API_URL = "https://open.er-api.com/v6/latest/KZT"
CURRENCY_TARGETS = ("USD", "EUR", "RUB")

MANUAL_EXPENSE_CATEGORIES = (
    "Продукты",
    "Кафе",
    "Транспорт",
    "Жилье",
    "Развлечения",
)

EXPENSE_CATEGORIES = MANUAL_EXPENSE_CATEGORIES + ("Банк",)

SUPPORTED_BANKS = {
    "kaspi": "Kaspi",
    "halyk": "Halyk",
    "centercredit": "ЦентрКредит",
    "auto": "Автоопределение",
}


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
