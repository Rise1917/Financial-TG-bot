import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN, setup_logging
from bot.database import init_db
from bot.handlers import setup_routers

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()
    logger.info("Запуск финансового бота...")

    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(setup_routers())

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот запущен. Ожидание сообщений...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановка по запросу пользователя.")
