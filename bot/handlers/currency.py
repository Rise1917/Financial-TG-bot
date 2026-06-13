import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.keyboards import back_to_menu_keyboard
from bot.services.currency import (
    CurrencyAPIError,
    fetch_exchange_rates,
    format_rates_message,
)

logger = logging.getLogger(__name__)
router = Router(name="currency")


@router.callback_query(F.data == "currency_rates")
async def show_currency_rates(callback: CallbackQuery) -> None:
    await callback.answer("Загружаю курсы...")

    try:
        data = await fetch_exchange_rates()
        text = format_rates_message(data)
    except CurrencyAPIError as exc:
        logger.warning("Ошибка API курсов: %s", exc)
        await callback.message.edit_text(
            "⚠️ Не удалось получить курс валют.\n"
            "Проверьте интернет-соединение и попробуйте позже.",
            reply_markup=back_to_menu_keyboard(),
        )
        return
    except Exception:
        logger.exception("Непредвиденная ошибка при запросе курсов")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при загрузке курсов.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
