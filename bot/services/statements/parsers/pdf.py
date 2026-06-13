"""Парсер PDF-выписок — делегирует внутреннему конвертеру."""

from bot.services.statements.models import ParseResult
from bot.services.statements.parsers.pdf_converter import convert_pdf_to_transactions


def parse_pdf(content: bytes, bank: str = "") -> ParseResult:
    return convert_pdf_to_transactions(content, bank)
