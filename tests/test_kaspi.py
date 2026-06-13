from bot.services.statements.parsers.kaspi import (
    extract_transactions_from_grid,
    extract_transactions_from_text_lines,
)
from bot.services.statements.parsers.spreadsheet import parse_excel


def test_kaspi_text_lines() -> None:
    lines = [
        "Kaspi Gold - Выписка",
        "Баланс: 150 000 KZT",
        "Курс USD: 512.45",
        "Покупки",
        "09.06.2025 12:34 Magnum -1 500,00 KZT",
        "08.06.2025 Пополнение +25 000,00",
    ]
    txs = extract_transactions_from_text_lines(lines, "Kaspi")
    assert len(txs) == 2
    assert txs[0].amount == 1500.0 and txs[0].is_expense
    assert txs[1].amount == 25000.0 and not txs[1].is_expense


def test_kaspi_grid_skips_balance() -> None:
    rows = [
        ("Kaspi Gold",),
        ("Баланс на счету", "150 000"),
        ("Курс USD", "512.45"),
        ("09.06.2025", "Magnum", "-2 500,00"),
    ]
    txs = extract_transactions_from_grid(rows, "Kaspi")
    assert len(txs) == 1
    assert txs[0].amount == 2500.0


def test_kaspi_excel_multisheet(kaspi_excel_bytes: bytes) -> None:
    result = parse_excel(kaspi_excel_bytes, "Kaspi")
    assert len(result.transactions) >= 3
    amounts = sorted(tx.amount for tx in result.transactions)
    assert 850.5 in amounts
    assert 2500.0 in amounts
