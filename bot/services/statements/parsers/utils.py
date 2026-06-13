import re
from datetime import datetime

_DATE_IN_TEXT = re.compile(
    r"\b(\d{1,2}[./]\d{1,2}[./]\d{2,4})"
    r"(?:\s+(\d{1,2}:\d{2}(?::\d{2})?))?\b"
)
_AMOUNT_IN_TEXT = re.compile(
    r"([-−+]?\s*\d[\d\s\u00a0]*(?:[.,]\d{1,2})?)\s*(?:₸|KZT|тг|T|〒)?",
    re.IGNORECASE,
)


def parse_amount(value: str | float | int | None) -> float | None:
    signed = parse_amount_signed(value)
    return signed[0] if signed else None


def parse_amount_signed(
    value: str | float | int | None,
) -> tuple[float, bool] | None:
    """Возвращает (сумма, is_expense) или None."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        amount = float(value)
        if amount == 0:
            return None
        return round(abs(amount), 2), amount < 0

    text = str(value).strip().replace("\u00a0", " ")
    if not text:
        return None

    is_expense = text.startswith("-") or text.startswith("−")
    is_income = text.startswith("+")

    cleaned = text.replace(" ", "").replace("₸", "").replace("KZT", "")
    cleaned = cleaned.replace("тг", "").replace("T", "").replace(",", ".")

    sign_stripped = cleaned.lstrip("+-−")
    sign_stripped = re.sub(r"[^\d.]", "", sign_stripped)

    if not sign_stripped:
        return None

    try:
        amount = float(sign_stripped)
    except ValueError:
        return None

    if amount == 0:
        return None

    if is_income:
        return round(amount, 2), False
    if is_expense:
        return round(amount, 2), True
    return round(amount, 2), True


def parse_date(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    text = str(value).strip()
    if not text:
        return None

    match = _DATE_IN_TEXT.search(text)
    if match:
        text = match.group(1)
        time_part = match.group(2)
        if time_part:
            text = f"{text} {time_part}"

    formats = (
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%d.%m.%y %H:%M:%S",
        "%d.%m.%y %H:%M",
        "%d.%m.%y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


def find_date_in_text(text: str) -> str | None:
    return parse_date(text)


def find_amount_in_text(text: str) -> tuple[float, bool] | None:
    """Находит наиболее вероятную сумму операции (не путая с датой/временем)."""
    text_wo_date = _DATE_IN_TEXT.sub(" ", text)
    candidates: list[tuple[int, float, bool]] = []

    for match in _AMOUNT_IN_TEXT.finditer(text_wo_date):
        raw = match.group(1)
        parsed = parse_amount_signed(raw)
        if not parsed:
            continue

        amount, is_expense = parsed
        score = 0
        raw_stripped = raw.strip()

        if re.search(r"[.,]\d{2}", raw):
            score += 4
        if raw_stripped.startswith(("+", "-", "−")):
            score += 4
        context = text[max(0, match.start() - 3) : match.end() + 4].lower()
        if any(token in context for token in ("₸", "kzt", "тг")):
            score += 3
        if amount >= 50:
            score += 1
        if re.fullmatch(r"\d{1,2}", raw_stripped):
            score -= 5

        candidates.append((score, amount, is_expense))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_score, best_amount, best_expense = candidates[0]
    if best_score < 1:
        return None
    return best_amount, best_expense


def detect_period(dates: list[str]) -> tuple[str, str]:
    if not dates:
        return "", ""
    sorted_dates = sorted(dates)
    return sorted_dates[0][:10], sorted_dates[-1][:10]


def strip_financial_tokens(text: str) -> str:
    """Убирает дату и сумму из строки, оставляя описание операции."""
    cleaned = re.sub(
        r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?\b",
        "",
        text,
    )
    cleaned = _AMOUNT_IN_TEXT.sub("", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" |-—")


def cell_to_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value).strip()
