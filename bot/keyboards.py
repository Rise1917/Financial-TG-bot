from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import MANUAL_EXPENSE_CATEGORIES, SUPPORTED_BANKS


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить расход",
                    callback_data="add_expense",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Мои расходы",
                    callback_data="my_expenses",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📄 Загрузить выписку",
                    callback_data="upload_statement",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📁 Мои выписки",
                    callback_data="my_statements",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💱 Курс валют",
                    callback_data="currency_rates",
                )
            ],
        ]
    )


def banks_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=label,
                callback_data=f"bank:{code}",
            )
        ]
        for code, label in SUPPORTED_BANKS.items()
    ]
    buttons.append(
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def categories_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=category, callback_data=f"cat:{category}")]
        for category in MANUAL_EXPENSE_CATEGORIES
    ]
    buttons.append(
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_to_menu")]
        ]
    )


def statements_list_keyboard(statements: list[dict]) -> InlineKeyboardMarkup:
    """Список выписок с кнопками удаления."""
    buttons: list[list[InlineKeyboardButton]] = []

    for stmt in statements:
        label = f"🗑 {stmt['bank']} — {stmt['filename'][:28]}"
        if len(stmt["filename"]) > 28:
            label += "…"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"del_stmt:{stmt['id']}",
                )
            ]
        )

    buttons.append(
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_to_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def delete_statement_confirm_keyboard(statement_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"del_stmt_yes:{statement_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="my_statements",
                ),
            ]
        ]
    )
