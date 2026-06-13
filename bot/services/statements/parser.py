"""Единая точка входа для разбора банковских выписок."""

import hashlib
import logging
from pathlib import Path

from bot.config import SUPPORTED_BANKS
from bot.services.statements.models import ParseResult
from bot.services.statements.parsers.onec import parse_onec
from bot.services.statements.parsers.pdf import parse_pdf
from bot.services.statements.parsers.spreadsheet import parse_csv, parse_excel

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

_EXTENSION_MAP = {
    ".csv": "csv",
    ".xlsx": "excel",
    ".xls": "excel",
    ".pdf": "pdf",
    ".txt": "onec",
}


def file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def detect_file_type(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext in _EXTENSION_MAP:
        file_type = _EXTENSION_MAP[ext]
        if file_type == "onec" and b"1CClientBankExchange" not in content[:4096]:
            text_sample = content[:4096].decode("utf-8", errors="ignore")
            if "СекцияДокумент" not in text_sample:
                return "csv" if ext == ".txt" else file_type
        return file_type

    sample = content[:4096]
    if b"%PDF" in sample:
        return "pdf"
    if b"1CClientBankExchange" in sample or "СекцияДокумент" in sample.decode(
        "utf-8", errors="ignore"
    ):
        return "onec"
    return "csv"


def parse_statement(content: bytes, filename: str, bank: str) -> ParseResult:
    if len(content) > MAX_FILE_SIZE:
        return ParseResult(errors=["Файл слишком большой (максимум 10 МБ)"])

    bank_label = SUPPORTED_BANKS.get(bank, bank)
    file_type = detect_file_type(filename, content)
    logger.info(
        "Разбор выписки: bank=%s, file=%s, type=%s, size=%d",
        bank_label,
        filename,
        file_type,
        len(content),
    )

    try:
        if file_type == "csv":
            result = parse_csv(content, bank_label)
        elif file_type == "excel":
            result = parse_excel(content, bank_label)
        elif file_type == "pdf":
            result = parse_pdf(content, bank_label)
        elif file_type == "onec":
            text = content.decode("utf-8", errors="ignore")
            result = parse_onec(text, bank_label)
        else:
            return ParseResult(errors=[f"Неподдерживаемый формат: {filename}"])
    except Exception as exc:
        logger.exception("Ошибка парсинга выписки %s", filename)
        return ParseResult(errors=[f"Ошибка чтения файла: {exc}"])

    if not result.bank_detected:
        result.bank_detected = bank_label

    logger.info(
        "Результат разбора: операций=%d, ошибки=%s",
        len(result.transactions),
        result.errors or "нет",
    )
    return result
