"""
Извлечение операций из выписок Kaspi Gold.

Работает с «сырыми» таблицами из PDF, с Excel после конвертации PDF
(несколько листов, мусор в шапке) и с обычными таблицами.
"""

import logging
import re
from typing import Any

from bot.services.statements.models import ParsedTransaction
from bot.services.statements.parsers.utils import (
    cell_to_str,
    find_amount_in_text,
    find_date_in_text,
    parse_amount_signed,
    parse_date,
    strip_financial_tokens,
)

logger = logging.getLogger(__name__)

_CATEGORY_MARKERS = (
    "покупки",
    "переводы",
    "поступления",
    "пополнения",
    "снятия",
    "платежи",
    "комиссии",
    "возвраты",
    "оплаты",
)

_JUNK_MARKERS = (
    "баланс на",
    "остаток на",
    "доступно на",
    "доступная сумма",
    "курс валют",
    "курс usd",
    "курс eur",
    "курс rub",
    "эквивалент в",
    "equivalent",
    "выписка за период",
    "выписка по счету",
    "справка о",
    "номер счета",
    "номер счёта",
    "иин ",
    "бик ",
    "банк получателя",
    "kaspi gold",
    "kaspi.kz",
    "страница ",
    "page ",
    "итого за период",
    "итого по операциям",
    "всего операций",
    "дата формирования",
    "дата составления",
    "валюта счета",
    "валюта счёта",
)

_INCOME_MARKERS = (
    "поступлен",
    "пополнен",
    "зачислен",
    "возврат",
    "перевод от",
    "перевод с",
    "зарплат",
    "cashback",
    "кэшбэк",
)

_DATE_ONLY_RE = re.compile(r"^\d{1,2}[./]\d{1,2}[./]\d{2,4}$")
_CATEGORY_HEADER_RE = re.compile(
    r"^(" + "|".join(_CATEGORY_MARKERS) + r")\s*:?\s*$",
    re.IGNORECASE,
)


def extract_transactions_from_grid(
    rows: list[tuple[Any, ...] | list[Any]],
    bank: str = "Kaspi",
) -> list[ParsedTransaction]:
    """Извлекает операции из двумерной сетки ячеек (Excel / таблица PDF)."""
    transactions: list[ParsedTransaction] = []
    seen: set[tuple[str, float, str]] = set()
    current_category = ""

    for raw_row in rows:
        cells = [cell_to_str(c) for c in raw_row]
        if not any(cells):
            continue

        row_text = " | ".join(c for c in cells if c).strip()
        if not row_text:
            continue

        category_match = _detect_category_header(row_text, cells)
        if category_match:
            current_category = category_match
            continue

        if _is_junk_row(row_text, cells):
            continue

        tx = _extract_from_cells(cells, current_category)
        if not tx:
            tx = _extract_from_text(row_text, current_category)

        if not tx:
            continue

        key = (tx.date[:10], tx.amount, tx.description[:60])
        if key in seen:
            continue
        seen.add(key)
        transactions.append(tx)

    logger.info(
        "Kaspi grid: строк=%d, операций=%d, bank=%s",
        len(rows),
        len(transactions),
        bank,
    )
    return transactions


def extract_transactions_from_text_lines(
    lines: list[str],
    bank: str = "Kaspi",
) -> list[ParsedTransaction]:
    """Извлекает операции из текста PDF построчно и из многострочных блоков."""
    transactions: list[ParsedTransaction] = []
    seen: set[tuple[str, float, str]] = set()
    current_category = ""
    buffer: list[str] = []

    def flush_buffer() -> None:
        nonlocal buffer
        if not buffer:
            return
        combined = " ".join(buffer)
        tx = _extract_from_text(combined, current_category)
        if tx:
            key = (tx.date[:10], tx.amount, tx.description[:60])
            if key not in seen:
                seen.add(key)
                transactions.append(tx)
        buffer = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line or len(line) < 4:
            continue

        if _detect_category_header(line, [line]):
            flush_buffer()
            current_category = _detect_category_header(line, [line]) or current_category
            continue

        if _is_junk_row(line, [line]):
            flush_buffer()
            continue

        tx_direct = _extract_from_text(line, current_category)
        if tx_direct:
            flush_buffer()
            key = (tx_direct.date[:10], tx_direct.amount, tx_direct.description[:60])
            if key not in seen:
                seen.add(key)
                transactions.append(tx_direct)
            continue

        if find_date_in_text(line) or buffer:
            buffer.append(line)
            combined = " ".join(buffer)
            if find_date_in_text(combined) and find_amount_in_text(combined):
                tx = _extract_from_text(combined, current_category)
                if tx:
                    key = (tx.date[:10], tx.amount, tx.description[:60])
                    if key not in seen:
                        seen.add(key)
                        transactions.append(tx)
                    buffer = []
            elif len(buffer) > 4:
                buffer = buffer[-2:]

    flush_buffer()

    logger.info(
        "Kaspi text: строк=%d, операций=%d, bank=%s",
        len(lines),
        len(transactions),
        bank,
    )
    return transactions


def normalize_pdf_pages_to_grid(pages_data: list[list[list[str]]]) -> list[list[str]]:
    """
    Объединяет таблицы со всех страниц PDF в одну сетку,
    убирая повторяющиеся шапки и служебные строки.
    """
    grid: list[list[str]] = []
    for page_rows in pages_data:
        for row in page_rows:
            cells = [str(c).strip() if c else "" for c in row]
            row_text = " | ".join(c for c in cells if c)
            if not row_text or _is_junk_row(row_text, cells):
                continue
            if _is_repeated_header(row_text):
                continue
            grid.append(cells)
    return grid


def _detect_category_header(row_text: str, cells: list[str]) -> str | None:
    lower = row_text.lower().strip()
    if _CATEGORY_HEADER_RE.match(lower):
        return row_text.strip().rstrip(":")

    for marker in _CATEGORY_MARKERS:
        if lower == marker or lower == f"{marker}:":
            return row_text.strip().rstrip(":")

    if len(cells) == 1 and any(marker in lower for marker in _CATEGORY_MARKERS):
        if not find_date_in_text(lower) and not find_amount_in_text(lower):
            return row_text.strip().rstrip(":")

    return None


def _is_repeated_header(row_text: str) -> bool:
    lower = row_text.lower()
    header_words = ("дата", "описание", "сумма", "date", "amount", "description")
    matches = sum(1 for word in header_words if word in lower)
    return matches >= 2 and not find_date_in_text(row_text)


def _is_junk_row(row_text: str, cells: list[str]) -> bool:
    lower = row_text.lower()

    for marker in _JUNK_MARKERS:
        if marker in lower:
            return True

    if re.match(r"^(страница|page)\s*\d+", lower):
        return True

    if re.match(r"^\d{1,2}$", lower.strip()):
        return True

    has_date = bool(find_date_in_text(row_text))
    has_amount = bool(find_amount_in_text(row_text))

    if not has_date and not has_amount:
        if any(
            word in lower
            for word in ("баланс", "остаток", "курс", "usd", "eur", "rub", "gbp")
        ):
            return True
        if "₸" in row_text and len(cells) <= 2 and not has_date:
            return True

    if has_amount and not has_date:
        if any(word in lower for word in ("курс", "usd", "eur", "rub", "эквивалент")):
            return True

    return False


def _extract_from_cells(cells: list[str], category: str) -> ParsedTransaction | None:
    date_str: str | None = None
    amount_info: tuple[float, bool] | None = None
    amount_cell_idx = -1
    date_cell_idx = -1

    for idx, cell in enumerate(cells):
        if not cell:
            continue

        if date_str is None:
            if isinstance(cell, str) and _DATE_ONLY_RE.match(cell.strip()):
                date_str = parse_date(cell)
            else:
                date_str = find_date_in_text(cell)

        if date_str and date_cell_idx < 0 and find_date_in_text(cell):
            date_cell_idx = idx

        parsed_amount = parse_amount_signed(cell)
        if parsed_amount:
            if amount_info is None or parsed_amount[0] >= amount_info[0]:
                amount_info = parsed_amount
                amount_cell_idx = idx

    if not date_str or not amount_info:
        joined = " ".join(cells)
        return _extract_from_text(joined, category)

    desc_parts: list[str] = []
    for idx, cell in enumerate(cells):
        if idx in (date_cell_idx, amount_cell_idx) or not cell:
            continue
        if find_date_in_text(cell) and idx == date_cell_idx:
            continue
        if parse_amount_signed(cell) and idx == amount_cell_idx:
            continue
        desc_parts.append(cell)

    description = " ".join(desc_parts).strip() or category or "Операция Kaspi"
    amount, is_expense = amount_info
    is_expense = _resolve_expense(is_expense, description, category)

    return ParsedTransaction(
        date=date_str,
        amount=amount,
        is_expense=is_expense,
        description=description[:500],
        bank_category=category,
    )


def _extract_from_text(text: str, category: str) -> ParsedTransaction | None:
    date_str = find_date_in_text(text)
    amount_info = find_amount_in_text(text)

    if not date_str or not amount_info:
        return None

    amount, is_expense = amount_info

    description = strip_financial_tokens(text)

    if not description or len(description) < 2:
        description = category or "Операция Kaspi"

    is_expense = _resolve_expense(is_expense, description, category)

    return ParsedTransaction(
        date=date_str,
        amount=amount,
        is_expense=is_expense,
        description=description[:500],
        bank_category=category,
    )


def _resolve_expense(default: bool, description: str, category: str) -> bool:
    lower = f"{description} {category}".lower()
    if any(marker in lower for marker in _INCOME_MARKERS):
        return False
    if any(marker in lower for marker in ("покупк", "оплат", "списан", "снятие")):
        return True
    if category and any(
        marker in category.lower()
        for marker in ("поступлен", "пополнен")
    ):
        return False
    return default
