import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import init_db
from bot.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="start")


WELCOME_TEXT = (
    "👋 <b>Добро пожаловать в финансового помощника!</b>\n\n"
    "Я помогу вам отслеживать расходы в тенге (₸), "
    "загружать выписки из Kaspi и других банков, "
    "смотреть статистику за месяц и проверять курс валют.\n\n"
    "Выберите действие:"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await init_db()

    user = message.from_user
    logger.info("Пользователь %s (%s) запустил бота", user.id, user.username)

    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_keyboard())
    await callback.answer()
