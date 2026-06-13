"""Парсер формата 1C Client-Bank Exchange (Halyk, Kaspi Pay, ЦентрКредит и др.)."""

import re

from bot.services.statements.models import ParsedTransaction, ParseResult
from bot.services.statements.parsers.utils import detect_period, parse_amount, parse_date


def parse_onec(content: str, bank: str = "") -> ParseResult:
    result = ParseResult(bank_detected=bank or "1C")

    if "1CClientBankExchange" not in content and "СекцияДокумент" not in content:
        result.errors.append("Файл не похож на формат 1C")
        return result

    documents = re.split(r"СекцияДокумент=", content)
    dates: list[str] = []

    for block in documents[1:]:
        doc_type_match = re.match(r"([^\r\n]+)", block)
        doc_type = doc_type_match.group(1).strip() if doc_type_match else ""

        fields = _extract_fields(block)
        date_str = parse_date(fields.get("Дата", ""))
        amount = parse_amount(fields.get("Сумма", ""))
        description = (
            fields.get("НазначениеПлатежа")
            or fields.get("Назначение")
            or fields.get("Детали")
            or doc_type
        ).strip()

        if not date_str or not amount:
            continue

        is_expense = _is_expense_document(doc_type, fields, bank)
        dates.append(date_str)

        result.transactions.append(
            ParsedTransaction(
                date=date_str,
                amount=amount,
                is_expense=is_expense,
                description=description[:500],
                bank_category=doc_type,
            )
        )

    result.period_from, result.period_to = detect_period(dates)
    if not result.transactions:
        result.errors.append("В файле 1C не найдено операций")
    return result


def _extract_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and key != "КонецДокумента":
            fields[key] = value
    return fields


def _is_expense_document(doc_type: str, fields: dict[str, str], bank: str) -> bool:
    doc_lower = doc_type.lower()
    expense_types = (
        "платеж", "списан", "перевод", "покупк", "оплат", "комисси", "снят",
    )
    income_types = ("поступлен", "зачислен", "возврат", "пополнен")

    for marker in income_types:
        if marker in doc_lower:
            return False
    for marker in expense_types:
        if marker in doc_lower:
            return True

    debit = parse_amount(fields.get("Дебет", ""))
    credit = parse_amount(fields.get("Кредит", ""))
    if debit and not credit:
        return True
    if credit and not debit:
        return False

    direction = fields.get("Направление", "").lower()
    if "спис" in direction or "расход" in direction:
        return True
    if "поступ" in direction or "приход" in direction:
        return False

    return True
