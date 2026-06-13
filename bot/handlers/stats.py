import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database import get_monthly_stats
from bot.keyboards import back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="stats")


@router.callback_query(F.data == "my_expenses")
async def show_monthly_stats(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    try:
        stats = await get_monthly_stats(user_id)
    except Exception:
        logger.exception("Ошибка получения статистики для user_id=%s", user_id)
        await callback.message.edit_text(
            "⚠️ Не удалось загрузить статистику. Попробуйте позже.",
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    text = _format_stats_message(stats)
    await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()


def _format_stats_message(stats: dict) -> str:
    month_label = f"{stats['month_ru']} {stats['year']}"
    categories = stats["categories"]
    grand_total = stats["grand_total"]

    if not categories:
        return (
            f"📊 <b>Мои расходы за {month_label}</b>\n\n"
            "За этот месяц расходов пока нет.\n"
            "Нажмите «Добавить расход», чтобы начать учёт."
        )

    lines = [f"📊 <b>Мои расходы за {month_label}</b>\n"]

    for category, total in categories.items():
        lines.append(f"• {category}: <b>{total:,.2f} ₸</b>")

    lines.append(f"\n💰 <b>Итого: {grand_total:,.2f} ₸</b>")

    from_statements = stats.get("from_statements", 0)
    if from_statements:
        lines.append(
            f"\n<i>Из выписок: {from_statements} операций</i>"
        )

    return "\n".join(lines)
