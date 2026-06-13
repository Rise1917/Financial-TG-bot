import logging
from datetime import datetime
from typing import Any

import aiosqlite

from bot.config import DATABASE_PATH
from bot.services.statements.categorizer import categorize_description
from bot.services.statements.models import ParsedTransaction

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Создаёт директорию и таблицы, если их ещё нет."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                statement_id INTEGER
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS statements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bank TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                period_from TEXT,
                period_to TEXT,
                total_expenses REAL DEFAULT 0,
                total_income REAL DEFAULT 0,
                transactions_count INTEGER DEFAULT 0
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS statement_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                statement_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                operation_date TEXT NOT NULL,
                amount REAL NOT NULL,
                is_expense INTEGER NOT NULL,
                description TEXT,
                bank_category TEXT,
                mapped_category TEXT,
                FOREIGN KEY (statement_id) REFERENCES statements(id) ON DELETE CASCADE
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_user_date "
            "ON expenses (user_id, date)"
        )
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_statements_user_hash "
            "ON statements (user_id, file_hash)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_stmt_tx_user_date "
            "ON statement_transactions (user_id, operation_date)"
        )
        await _migrate_expenses_columns(db)
        await db.commit()

    logger.info("База данных инициализирована: %s", DATABASE_PATH)


async def _migrate_expenses_columns(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("PRAGMA table_info(expenses)")
    columns = {row[1] for row in await cursor.fetchall()}

    if "source" not in columns:
        await db.execute(
            "ALTER TABLE expenses ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'"
        )
    if "statement_id" not in columns:
        await db.execute("ALTER TABLE expenses ADD COLUMN statement_id INTEGER")


async def add_expense(
    user_id: int,
    category: str,
    amount: float,
    date_str: str | None = None,
    source: str = "manual",
    statement_id: int | None = None,
) -> int:
    """Сохраняет расход и возвращает id записи."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO expenses (user_id, category, amount, date, source, statement_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, category, amount, date_str, source, statement_id),
        )
        await db.commit()
        expense_id = cursor.lastrowid

    logger.info(
        "Расход добавлен: user_id=%s, category=%s, amount=%.2f, source=%s",
        user_id,
        category,
        amount,
        source,
    )
    return expense_id


async def statement_exists(user_id: int, file_hash: str) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM statements WHERE user_id = ? AND file_hash = ?",
            (user_id, file_hash),
        )
        return await cursor.fetchone() is not None


async def save_statement(
    user_id: int,
    bank: str,
    filename: str,
    file_type: str,
    file_hash: str,
    transactions: list[ParsedTransaction],
    period_from: str = "",
    period_to: str = "",
) -> dict[str, Any]:
    """Сохраняет выписку, все операции и импортирует расходы в общую статистику."""
    uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expenses = [tx for tx in transactions if tx.is_expense]
    income = [tx for tx in transactions if not tx.is_expense]
    total_expenses = sum(tx.amount for tx in expenses)
    total_income = sum(tx.amount for tx in income)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO statements (
                user_id, bank, filename, file_type, file_hash, uploaded_at,
                period_from, period_to, total_expenses, total_income, transactions_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                bank,
                filename,
                file_type,
                file_hash,
                uploaded_at,
                period_from,
                period_to,
                total_expenses,
                total_income,
                len(transactions),
            ),
        )
        statement_id = cursor.lastrowid

        imported_expenses = 0
        for tx in transactions:
            mapped_category = (
                categorize_description(tx.description, tx.bank_category)
                if tx.is_expense
                else ""
            )
            await db.execute(
                """
                INSERT INTO statement_transactions (
                    statement_id, user_id, operation_date, amount, is_expense,
                    description, bank_category, mapped_category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    statement_id,
                    user_id,
                    tx.date,
                    tx.amount,
                    int(tx.is_expense),
                    tx.description,
                    tx.bank_category,
                    mapped_category,
                ),
            )

            if tx.is_expense:
                await db.execute(
                    """
                    INSERT INTO expenses (
                        user_id, category, amount, date, source, statement_id
                    ) VALUES (?, ?, ?, ?, 'statement', ?)
                    """,
                    (user_id, mapped_category, tx.amount, tx.date, statement_id),
                )
                imported_expenses += 1

        await db.commit()

    logger.info(
        "Выписка сохранена: user_id=%s, statement_id=%s, ops=%d, expenses=%d",
        user_id,
        statement_id,
        len(transactions),
        imported_expenses,
    )

    return {
        "statement_id": statement_id,
        "transactions_count": len(transactions),
        "expenses_count": len(expenses),
        "income_count": len(income),
        "total_expenses": total_expenses,
        "total_income": total_income,
        "imported_expenses": imported_expenses,
        "period_from": period_from,
        "period_to": period_to,
    }


async def get_statement_by_id(
    user_id: int, statement_id: int
) -> dict[str, Any] | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, bank, filename, uploaded_at, period_from, period_to,
                   total_expenses, total_income, transactions_count
            FROM statements
            WHERE id = ? AND user_id = ?
            """,
            (statement_id, user_id),
        )
        row = await cursor.fetchone()
    return dict(row) if row else None


async def delete_statement(user_id: int, statement_id: int) -> dict[str, Any] | None:
    """
    Удаляет выписку, её операции и связанные расходы из статистики.

    Возвращает сводку удаления или None, если выписка не найдена.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT id, bank, filename, transactions_count
            FROM statements
            WHERE id = ? AND user_id = ?
            """,
            (statement_id, user_id),
        )
        statement = await cursor.fetchone()
        if not statement:
            return None

        cursor = await db.execute(
            """
            SELECT COUNT(*) AS cnt FROM expenses
            WHERE user_id = ? AND statement_id = ?
            """,
            (user_id, statement_id),
        )
        expenses_row = await cursor.fetchone()
        expenses_removed = expenses_row["cnt"] if expenses_row else 0

        await db.execute(
            "DELETE FROM expenses WHERE user_id = ? AND statement_id = ?",
            (user_id, statement_id),
        )
        await db.execute(
            """
            DELETE FROM statement_transactions
            WHERE user_id = ? AND statement_id = ?
            """,
            (user_id, statement_id),
        )
        await db.execute(
            "DELETE FROM statements WHERE id = ? AND user_id = ?",
            (statement_id, user_id),
        )
        await db.commit()

    logger.info(
        "Выписка удалена: user_id=%s, statement_id=%s, expenses_removed=%d",
        user_id,
        statement_id,
        expenses_removed,
    )

    return {
        "statement_id": statement_id,
        "bank": statement["bank"],
        "filename": statement["filename"],
        "transactions_count": statement["transactions_count"],
        "expenses_removed": expenses_removed,
    }


async def get_user_statements(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, bank, filename, uploaded_at, period_from, period_to,
                   total_expenses, total_income, transactions_count
            FROM statements
            WHERE user_id = ?
            ORDER BY uploaded_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_statement_transactions(
    user_id: int, statement_id: int, limit: int = 5
) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT operation_date, amount, is_expense, description, mapped_category
            FROM statement_transactions
            WHERE user_id = ? AND statement_id = ?
            ORDER BY operation_date DESC
            LIMIT ?
            """,
            (user_id, statement_id, limit),
        )
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_monthly_stats(user_id: int) -> dict[str, Any]:
    """Возвращает сумму расходов за текущий месяц по категориям."""
    now = datetime.now()
    month_prefix = now.strftime("%Y-%m")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT category, SUM(amount) AS total
            FROM expenses
            WHERE user_id = ? AND date LIKE ?
            GROUP BY category
            ORDER BY total DESC
            """,
            (user_id, f"{month_prefix}%"),
        )
        rows = await cursor.fetchall()

        total_cursor = await db.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS grand_total
            FROM expenses
            WHERE user_id = ? AND date LIKE ?
            """,
            (user_id, f"{month_prefix}%"),
        )
        total_row = await total_cursor.fetchone()

        stmt_cursor = await db.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM expenses
            WHERE user_id = ? AND date LIKE ? AND source = 'statement'
            """,
            (user_id, f"{month_prefix}%"),
        )
        stmt_row = await stmt_cursor.fetchone()

    categories = {row["category"]: row["total"] for row in rows}
    grand_total = total_row["grand_total"] if total_row else 0.0
    from_statements = stmt_row["cnt"] if stmt_row else 0

    return {
        "month": now.strftime("%B %Y"),
        "month_ru": _month_name_ru(now.month),
        "year": now.year,
        "categories": categories,
        "grand_total": grand_total,
        "from_statements": from_statements,
    }


def _month_name_ru(month: int) -> str:
    names = {
        1: "Январь",
        2: "Февраль",
        3: "Март",
        4: "Апрель",
        5: "Май",
        6: "Июнь",
        7: "Июль",
        8: "Август",
        9: "Сентябрь",
        10: "Октябрь",
        11: "Ноябрь",
        12: "Декабрь",
    }
    return names.get(month, str(month))
