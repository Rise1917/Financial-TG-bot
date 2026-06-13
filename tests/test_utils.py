import pytest

from bot.services.statements.parsers.utils import (
    find_amount_in_text,
    find_date_in_text,
    parse_amount,
    parse_amount_signed,
    parse_date,
    strip_financial_tokens,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1500", 1500.0),
        ("1 500,50", 1500.5),
        ("-2 500,00", 2500.0),
        ("+50 000,00", 50000.0),
        ("₸1250.75", 1250.75),
        ("abc", None),
    ],
)
def test_parse_amount(raw: str, expected: float | None) -> None:
    assert parse_amount(raw) == expected


def test_parse_amount_signed_expense() -> None:
    result = parse_amount_signed("-1 500,00")
    assert result == (1500.0, True)


def test_parse_amount_signed_income() -> None:
    result = parse_amount_signed("+25 000,00")
    assert result == (25000.0, False)


@pytest.mark.parametrize(
    "raw",
    ["09.06.2025 14:30", "09.06.2025", "2025-06-09"],
)
def test_parse_date(raw: str) -> None:
    assert parse_date(raw) is not None
    assert parse_date(raw).startswith("2025-06-09") or parse_date(raw).startswith("2025")


def test_find_amount_ignores_date_parts() -> None:
    result = find_amount_in_text("09.06.2025 12:34 Magnum -1 500,00 KZT")
    assert result == (1500.0, True)


def test_strip_financial_tokens() -> None:
    text = strip_financial_tokens("09.06.2025 12:34 Magnum -1 500,00 KZT")
    assert "Magnum" in text
    assert "2025" not in text
    assert "1500" not in text
