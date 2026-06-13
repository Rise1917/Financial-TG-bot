import os
from datetime import datetime
from io import BytesIO

import pytest
import pytest_asyncio
from openpyxl import Workbook

os.environ.setdefault("BOT_TOKEN", "0000000000:test_token_for_pytest")

from bot.database import init_db
from bot.services.statements.models import ParsedTransaction


def _current_month_dates() -> tuple[str, str, str]:
    now = datetime.now()
    base = now.strftime("%Y-%m")
    return (
        f"{base}-09 14:30:00",
        f"{base}-08 10:00:00",
        f"{base}-07 10:00:00",
    )


@pytest_asyncio.fixture
async def test_db(tmp_path, monkeypatch):
    """Изолированная SQLite-база для каждого теста."""
    db_path = tmp_path / "test_finance.db"
    monkeypatch.setattr("bot.database.DATABASE_PATH", db_path)
    await init_db()
    return db_path


@pytest.fixture
def sample_transactions() -> list[ParsedTransaction]:
    d1, d2, d3 = _current_month_dates()
    return [
        ParsedTransaction(
            date=d1,
            amount=2500.0,
            is_expense=True,
            description="Magnum CU-1",
            bank_category="Покупки",
        ),
        ParsedTransaction(
            date=d2,
            amount=50000.0,
            is_expense=False,
            description="Перевод от Ивана",
            bank_category="Поступления",
        ),
        ParsedTransaction(
            date=d3,
            amount=850.5,
            is_expense=True,
            description="Yandex Go",
            bank_category="Покупки",
        ),
    ]


@pytest.fixture
def kaspi_excel_bytes() -> bytes:
    """Excel, имитирующий конвертированную выписку Kaspi (2 листа + шапка)."""
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Page1"
    ws1.append(["Kaspi Gold"])
    ws1.append(["Баланс на счету", "150 000", "KZT"])
    ws1.append(["Курс USD", "512.45"])
    ws1.append(["Дата", "Описание", "Сумма"])
    ws1.append(["09.06.2025 14:30", "Magnum CU-1", "-2 500,00"])
    ws1.append(["08.06.2025", "Перевод от Ивана", "+50 000,00"])

    ws2 = wb.create_sheet("Page2")
    ws2.append(["Выписка за период"])
    ws2.append(["07.06.2025 10:00", "Yandex Go", "-850,50"])

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
