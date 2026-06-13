import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import SUPPORTED_BANKS
from bot.database import (
    delete_statement,
    get_statement_by_id,
    get_user_statements,
    save_statement,
    statement_exists,
)
from bot.keyboards import (
    back_to_menu_keyboard,
    banks_keyboard,
    delete_statement_confirm_keyboard,
    statements_list_keyboard,
)
from bot.services.statements import file_hash, parse_statement
from bot.services.statements.parser import detect_file_type
from bot.states import StatementStates

logger = logging.getLogger(__name__)
router = Router(name="statements")

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".pdf", ".txt"}


@router.callback_query(F.data == "upload_statement")
async def start_upload(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(StatementStates.waiting_for_file)
    await callback.message.edit_text(
        "🏦 <b>Загрузка банковской выписки</b>\n\n"
        "Выберите банк, из которого экспортирована выписка:\n\n"
        "<i>Поддерживаемые форматы:</i>\n"
        "• PDF — Kaspi Gold (рекомендуется, разбирается напрямую)\n"
        "• Excel (.xlsx) — Kaspi Pay, конвертированные выписки\n"
        "• 1C (.txt) — Halyk, Kaspi Pay, ЦентрКредит\n"
        "• CSV — универсальный формат",
        reply_markup=banks_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    StatementStates.waiting_for_file,
    F.data.startswith("bank:"),
)
async def select_bank(callback: CallbackQuery, state: FSMContext) -> None:
    bank_code = callback.data.split(":", maxsplit=1)[1]
    if bank_code not in SUPPORTED_BANKS:
        await callback.answer("Неизвестный банк", show_alert=True)
        return

    await state.update_data(bank=bank_code)
    bank_name = SUPPORTED_BANKS[bank_code]

    await callback.message.edit_text(
        f"🏦 Банк: <b>{bank_name}</b>\n\n"
        "Отправьте файл выписки как <b>документ</b> (скрепка → Файл).\n\n"
        "💡 Для Kaspi Gold лучше отправлять <b>оригинальный PDF</b> — "
        "бот сам извлечёт операции и отфильтрует баланс и курсы валют.\n\n"
        "Бот сохранит выписку в базу и добавит расходы в статистику.",
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer()


@router.message(StatementStates.waiting_for_file, F.document)
async def process_statement_file(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    document = message.document
    if not document:
        return

    filename = document.file_name or "statement"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext and ext not in ALLOWED_EXTENSIONS:
        await message.answer(
            "❌ Неподдерживаемый формат файла.\n"
            "Отправьте CSV, Excel (.xlsx), PDF или файл 1C (.txt).",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    data = await state.get_data()
    bank_code = data.get("bank", "auto")
    bank_name = SUPPORTED_BANKS.get(bank_code, "Автоопределение")
    user_id = message.from_user.id

    status_msg = await message.answer("⏳ Обрабатываю выписку...")

    try:
        file = await bot.get_file(document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        content = file_bytes.read()
    except Exception:
        logger.exception("Ошибка скачивания файла от user_id=%s", user_id)
        await status_msg.edit_text(
            "⚠️ Не удалось скачать файл. Попробуйте ещё раз.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    content_hash = file_hash(content)

    if await statement_exists(user_id, content_hash):
        await state.clear()
        await status_msg.edit_text(
            "ℹ️ Эта выписка уже была загружена ранее.\n"
            "Повторный импорт пропущен, чтобы не дублировать расходы.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    parse_result = parse_statement(content, filename, bank_code)

    if not parse_result.transactions:
        hints = [
            "❌ В выписке не найдено операций.\n",
            "\n".join(parse_result.errors) if parse_result.errors else "",
            "\n<b>Что попробовать:</b>",
            "• Отправьте оригинальный PDF из Kaspi (не конвертированный)",
            "• Выберите банк «Kaspi» при загрузке",
            "• Убедитесь, что в выписке есть операции за период",
        ]
        await status_msg.edit_text(
            "\n".join(line for line in hints if line),
            reply_markup=back_to_menu_keyboard(),
        )
        return

    file_type = detect_file_type(filename, content)
    detected_bank = parse_result.bank_detected or bank_name

    try:
        summary = await save_statement(
            user_id=user_id,
            bank=detected_bank,
            filename=filename,
            file_type=file_type,
            file_hash=content_hash,
            transactions=parse_result.transactions,
            period_from=parse_result.period_from,
            period_to=parse_result.period_to,
        )
    except Exception:
        logger.exception("Ошибка сохранения выписки user_id=%s", user_id)
        await status_msg.edit_text(
            "⚠️ Не удалось сохранить выписку в базу данных.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    await state.clear()
    await status_msg.edit_text(
        _format_import_summary(filename, detected_bank, summary, parse_result.errors),
        reply_markup=back_to_menu_keyboard(),
    )


@router.message(StatementStates.waiting_for_file)
async def wrong_statement_input(message: Message) -> None:
    await message.answer(
        "📎 Пожалуйста, отправьте файл выписки как <b>документ</b>, "
        "а не как фото или текст.",
        reply_markup=back_to_menu_keyboard(),
    )


@router.callback_query(F.data == "my_statements")
async def show_statements(callback: CallbackQuery) -> None:
    await _render_statements_list(callback)


@router.callback_query(F.data.startswith("del_stmt:"))
async def confirm_delete_statement(callback: CallbackQuery) -> None:
    statement_id = int(callback.data.split(":", maxsplit=1)[1])
    user_id = callback.from_user.id

    statement = await get_statement_by_id(user_id, statement_id)
    if not statement:
        await callback.answer("Выписка не найдена", show_alert=True)
        return

    await callback.message.edit_text(
        "⚠️ <b>Удалить выписку?</b>\n\n"
        f"🏦 Банк: <b>{statement['bank']}</b>\n"
        f"📄 Файл: <code>{statement['filename']}</code>\n"
        f"📋 Операций: {statement['transactions_count']}\n\n"
        "Будут удалены все операции из этой выписки и связанные "
        "расходы в статистике «Мои расходы».\n"
        "<i>Ручные расходы не затрагиваются.</i>",
        reply_markup=delete_statement_confirm_keyboard(statement_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_stmt_yes:"))
async def delete_statement_confirmed(callback: CallbackQuery) -> None:
    statement_id = int(callback.data.split(":", maxsplit=1)[1])
    user_id = callback.from_user.id

    try:
        result = await delete_statement(user_id, statement_id)
    except Exception:
        logger.exception(
            "Ошибка удаления выписки user_id=%s id=%s", user_id, statement_id
        )
        await callback.message.edit_text(
            "⚠️ Не удалось удалить выписку. Попробуйте позже.",
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    if not result:
        await callback.answer("Выписка не найдена", show_alert=True)
        return

    await callback.message.edit_text(
        "✅ <b>Выписка удалена</b>\n\n"
        f"📄 <code>{result['filename']}</code>\n"
        f"Убрано из статистики расходов: <b>{result['expenses_removed']}</b>",
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer("Выписка удалена")


async def _render_statements_list(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    try:
        statements = await get_user_statements(user_id)
    except Exception:
        logger.exception("Ошибка загрузки выписок user_id=%s", user_id)
        await callback.message.edit_text(
            "⚠️ Не удалось загрузить список выписок.",
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    if not statements:
        await callback.message.edit_text(
            "📁 <b>Мои выписки</b>\n\n"
            "Загруженных выписок пока нет.\n"
            "Нажмите «Загрузить выписку», чтобы импортировать операции из банка.",
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    lines = [
        "📁 <b>Мои выписки</b>\n",
        "Нажмите на выписку, чтобы удалить её:\n",
    ]
    for stmt in statements:
        period = ""
        if stmt["period_from"] and stmt["period_to"]:
            period = f" | {stmt['period_from']} — {stmt['period_to']}"
        lines.append(
            f"• <b>{stmt['bank']}</b> — {stmt['filename']}\n"
            f"   Операций: {stmt['transactions_count']} | "
            f"Расходы: {stmt['total_expenses']:,.2f} ₸"
            f"{period}"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=statements_list_keyboard(statements),
    )
    await callback.answer()


def _format_import_summary(
    filename: str,
    bank: str,
    summary: dict,
    warnings: list[str],
) -> str:
    period = ""
    if summary.get("period_from") and summary.get("period_to"):
        period = (
            f"\n📅 Период: {summary['period_from']} — {summary['period_to']}"
        )

    lines = [
        "✅ <b>Выписка успешно обработана!</b>\n",
        f"🏦 Банк: <b>{bank}</b>",
        f"📄 Файл: <code>{filename}</code>{period}",
        f"📋 Операций: <b>{summary['transactions_count']}</b>",
        f"📉 Расходов: <b>{summary['expenses_count']}</b> "
        f"на сумму <b>{summary['total_expenses']:,.2f} ₸</b>",
        f"📈 Поступлений: <b>{summary['income_count']}</b> "
        f"на сумму <b>{summary['total_income']:,.2f} ₸</b>",
        f"\n💾 Сохранено в базу. "
        f"<b>{summary['imported_expenses']}</b> расходов добавлено в статистику.",
    ]

    if warnings:
        lines.append("\n⚠️ " + "; ".join(warnings))

    return "\n".join(lines)
