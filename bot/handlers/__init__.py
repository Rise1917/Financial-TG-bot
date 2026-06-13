from aiogram import Router

from bot.handlers import currency, expenses, start, statements, stats


def setup_routers() -> Router:
    root_router = Router()
    root_router.include_router(start.router)
    root_router.include_router(expenses.router)
    root_router.include_router(statements.router)
    root_router.include_router(stats.router)
    root_router.include_router(currency.router)
    return root_router
