"""
Внутренний конвертер PDF → нормализованная таблица операций.

Извлекает данные из PDF (в т.ч. Kaspi Gold), отбрасывает шапку
(баланс, курсы валют) и собирает операции со всех страниц.
"""

import io
import logging
from typing import Any

import pdfplumber

from bot.services.statements.models import ParsedTransaction, ParseResult
from bot.services.statements.parsers.kaspi import (
    extract_transactions_from_grid,
    extract_transactions_from_text_lines,
    normalize_pdf_pages_to_grid,
)
from bot.services.statements.parsers.utils import detect_period

logger = logging.getLogger(__name__)

_TABLE_SETTINGS = (
    {"vertical_strategy": "lines", "horizontal_strategy": "lines", "snap_tolerance": 4},
    {"vertical_strategy": "text", "horizontal_strategy": "text", "snap_tolerance": 5},
    {"vertical_strategy": "lines_strict", "horizontal_strategy": "lines", "snap_tolerance": 3},
)


def convert_pdf_to_transactions(content: bytes, bank: str = "") -> ParseResult:
    """Главная функция: PDF → список операций."""
    result = ParseResult(bank_detected=bank or "PDF")
    all_tables: list[list[list[str]]] = []
    all_text_lines: list[str] = []
    full_text_parts: list[str] = []

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                if page_text:
                    full_text_parts.append(page_text)
                    all_text_lines.extend(page_text.splitlines())

                page_tables = _extract_page_tables(page)
                if page_tables:
                    all_tables.append(page_tables)
                    logger.debug(
                        "PDF стр.%d: таблиц=%d, строк текста=%d",
                        page_num,
                        len(page_tables),
                        len(page_text.splitlines()),
                    )
    except Exception as exc:
        logger.exception("Ошибка чтения PDF")
        result.errors.append(f"Не удалось прочитать PDF: {exc}")
        return result

    if not all_text_lines and not all_tables:
        result.errors.append("PDF не содержит извлекаемого текста")
        return result

    full_text = "\n".join(full_text_parts)
    if not bank:
        result.bank_detected = _detect_bank(full_text)
    else:
        result.bank_detected = bank

    transactions: list[ParsedTransaction] = []
    seen: set[tuple[str, float, str]] = set()

    def _add(txs: list[ParsedTransaction], source: str) -> None:
        added = 0
        for tx in txs:
            key = (tx.date[:10], tx.amount, tx.description[:60])
            if key not in seen:
                seen.add(key)
                transactions.append(tx)
                added += 1
        if added:
            logger.info("PDF %s: +%d операций", source, added)

    if all_tables:
        grid = normalize_pdf_pages_to_grid(all_tables)
        _add(extract_transactions_from_grid(grid, result.bank_detected), "таблицы")

    _add(
        extract_transactions_from_text_lines(all_text_lines, result.bank_detected),
        "текст",
    )

    if not transactions:
        _add(_extract_from_words_layout(content), "layout")

    dates = [tx.date for tx in transactions]
    result.transactions = transactions
    result.period_from, result.period_to = detect_period(dates)

    if not transactions:
        result.errors.append(
            "В PDF не найдено операций. Убедитесь, что это выписка Kaspi Gold "
            "с операциями за выбранный период."
        )
    else:
        logger.info(
            "PDF конвертирован: bank=%s, операций=%d, период=%s — %s",
            result.bank_detected,
            len(transactions),
            result.period_from,
            result.period_to,
        )

    return result


def _extract_page_tables(page: Any) -> list[list[str]]:
    best_rows: list[list[str]] = []

    for settings in _TABLE_SETTINGS:
        try:
            tables = page.extract_tables(table_settings=settings) or []
        except Exception:
            continue

        rows: list[list[str]] = []
        for table in tables:
            for row in table:
                if row and any(cell and str(cell).strip() for cell in row):
                    rows.append([str(cell or "").strip() for cell in row])

        if len(rows) > len(best_rows):
            best_rows = rows

    if not best_rows:
        try:
            table = page.extract_table()
            if table:
                best_rows = [
                    [str(cell or "").strip() for cell in row]
                    for row in table
                    if row and any(cell and str(cell).strip() for cell in row)
                ]
        except Exception:
            pass

    return best_rows


def _extract_from_words_layout(content: bytes) -> list[ParsedTransaction]:
    """Запасной способ: группировка слов по координатам Y."""
    lines: list[str] = []

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False,
                )
                if not words:
                    continue

                rows_by_y: dict[int, list[str]] = {}
                for word in words:
                    y_key = round(word["top"] / 3) * 3
                    rows_by_y.setdefault(y_key, []).append(word)

                for y_key in sorted(rows_by_y.keys()):
                    row_words = sorted(rows_by_y[y_key], key=lambda w: w["x0"])
                    line = " ".join(w["text"] for w in row_words).strip()
                    if line:
                        lines.append(line)
    except Exception:
        logger.debug("Layout-извлечение не удалось", exc_info=True)
        return []

    return extract_transactions_from_text_lines(lines, "Kaspi")


def _detect_bank(text: str) -> str:
    lower = text.lower()
    if "kaspi" in lower:
        return "Kaspi"
    if "halyk" in lower or "халык" in lower:
        return "Halyk"
    if "freedom" in lower:
        return "Freedom"
    if "jusan" in lower or "жусан" in lower:
        return "Jusan"
    return "PDF"
