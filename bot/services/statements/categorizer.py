"""Автоматическое сопоставление описания операции с категорией расходов."""

from bot.config import EXPENSE_CATEGORIES

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Продукты": (
        "magnum", "small", "ашан", "продукт",
        "супермаркет", "grocery", "market", "metro", "metro cash",
        "арбуз", "green", "carefood", "fix price", "minimarket",
    ),
    "Кафе": (
        "кафе", "ресторан", "coffee", "кофе", "mcdonald", "kfc",
        "burger", "pizza", "starbucks", "dodo", "wolt", "glovo",
        "yandex food", "еда", "обед", "lanzhou", "chicken",
    ),
    "Транспорт": (
        "такси", "yandex go", "uber", "bolt", "indriver", "индрайвер",
        "бензин", "заправ", "petrol", "азс", "парков", "metro kz",
        "автобус", "жд", "railway", "transport",
    ),
    "Жилье": (
        "аренд", "коммунал", "квартплат", "ипотек", "жкх", "электр",
        "водоканал", "отоплен", "kaspi qr оплата жк", "дом.кз",
    ),
    "Развлечения": (
        "кино", "cinema", "kinopark", "chaplin", "игр", "steam",
        "playstation", "netflix", "spotify", "youtube", "подписк",
        "концерт", "театр", "развлеч",
    ),
}

_DEFAULT_CATEGORY = "Банк"


def categorize_description(description: str, bank_category: str = "") -> str:
    text = f"{description} {bank_category}".lower()

    for category in EXPENSE_CATEGORIES:
        keywords = _KEYWORDS.get(category, ())
        if any(keyword in text for keyword in keywords):
            return category

    if bank_category:
        bank_lower = bank_category.lower()
        for category in EXPENSE_CATEGORIES:
            if category.lower() in bank_lower:
                return category

    return _DEFAULT_CATEGORY
