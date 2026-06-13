import logging
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import add_expense
from bot.keyboards import back_to_menu_keyboard, categories_keyboard
from bot.states import ExpenseStates

logger = logging.getLogger(__name__)
router = Router(name="expenses")


@router.callback_query(F.data == "add_expense")
async def start_add_expense(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "📂 Выберите категорию расхода:",
        reply_markup=categories_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def select_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":", maxsplit=1)[1]
    await state.set_state(ExpenseStates.waiting_for_amount)
    await state.update_data(category=category)

    await callback.message.edit_text(
        f"💰 Категория: <b>{category}</b>\n\n"
        "Введите сумму расхода в тенге (₸).\n"
        "Например: <code>1500</code> или <code>1500.50</code>",
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer()


@router.message(ExpenseStates.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext) -> None:
    amount = _parse_amount(message.text)

    if amount is None:
        await message.answer(
            "❌ Некорректная сумма.\n\n"
            "Введите число больше нуля, например:\n"
            "• <code>500</code>\n"
            "• <code>1250.75</code>\n"
            "• <code>1 500,50</code>",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    if amount <= 0:
        await message.answer(
            "❌ Сумма должна быть больше нуля. Попробуйте ещё раз:",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    if amount > 999_999_999:
        await message.answer(
            "❌ Слишком большая сумма. Введите реалистичное значение:",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    data = await state.get_data()
    category = data.get("category", "Без категории")
    user_id = message.from_user.id

    try:
        expense_id = await add_expense(user_id, category, amount)
    except Exception:
        logger.exception("Ошибка сохранения расхода для user_id=%s", user_id)
        await message.answer(
            "⚠️ Не удалось сохранить расход. Попробуйте позже.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    await state.clear()
    await message.answer(
        f"✅ Расход сохранён!\n\n"
        f"📂 Категория: <b>{category}</b>\n"
        f"💵 Сумма: <b>{amount:,.2f} ₸</b>\n"
        f"🆔 Запись №{expense_id}",
        reply_markup=back_to_menu_keyboard(),
    )


def _parse_amount(text: str | None) -> float | None:
    """Парсит сумму из текста пользователя."""
    if not text:
        return None

    cleaned = text.strip().replace(" ", "").replace(",", ".")
    cleaned = re.sub(r"[^\d.]", "", cleaned)

    if not cleaned or cleaned.count(".") > 1:
        return None

    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None
