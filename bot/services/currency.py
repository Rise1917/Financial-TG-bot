import logging
from typing import Any

import aiohttp

from bot.config import CURRENCY_API_URL, CURRENCY_TARGETS

logger = logging.getLogger(__name__)


class CurrencyAPIError(Exception):
    """Ошибка при получении курсов валют."""


async def fetch_exchange_rates() -> dict[str, Any]:
    """
    Запрашивает курсы валют относительно KZT.

    API возвращает, сколько единиц валюты даёт 1 KZT.
    Для отображения инвертируем: 1 USD = X KZT.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                CURRENCY_API_URL,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    raise CurrencyAPIError(
                        f"API вернул статус {response.status}"
                    )
                data = await response.json()
    except aiohttp.ClientError as exc:
        logger.exception("Сетевая ошибка при запросе курсов валют")
        raise CurrencyAPIError("Не удалось подключиться к API курсов валют") from exc

    if data.get("result") != "success":
        raise CurrencyAPIError("API вернул неуспешный результат")

    rates = data.get("rates", {})
    kzt_rates: dict[str, float] = {}

    for currency in CURRENCY_TARGETS:
        rate_per_kzt = rates.get(currency)
        if not rate_per_kzt or rate_per_kzt <= 0:
            logger.warning("Курс для %s не найден или некорректен", currency)
            continue
        kzt_rates[currency] = round(1 / rate_per_kzt, 2)

    if not kzt_rates:
        raise CurrencyAPIError("Не удалось получить курсы валют")

    return {
        "rates": kzt_rates,
        "updated": data.get("time_last_update_utc", "неизвестно"),
    }


def format_rates_message(data: dict[str, Any]) -> str:
    """Форматирует курсы валют для отправки пользователю."""
    labels = {
        "USD": "🇺🇸 USD (доллар)",
        "EUR": "🇪🇺 EUR (евро)",
        "RUB": "🇷🇺 RUB (рубль)",
    }

    lines = ["💱 <b>Курс валют к тенге (KZT)</b>\n"]
    for currency, kzt_value in data["rates"].items():
        label = labels.get(currency, currency)
        lines.append(f"{label}: <b>{kzt_value:,.2f} ₸</b>")

    lines.append(f"\n<i>Обновлено: {data['updated']}</i>")
    return "\n".join(lines)
