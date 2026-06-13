import pytest

from bot.database import (
    add_expense,
    delete_statement,
    get_monthly_stats,
    get_user_statements,
    save_statement,
    statement_exists,
)
from bot.services.statements.models import ParsedTransaction


@pytest.mark.asyncio
async def test_save_and_list_statement(test_db, sample_transactions) -> None:
    summary = await save_statement(
        user_id=1,
        bank="Kaspi",
        filename="test.pdf",
        file_type="pdf",
        file_hash="hash123",
        transactions=sample_transactions,
        period_from="2025-06-07",
        period_to="2025-06-09",
    )
    assert summary["transactions_count"] == 3
    assert summary["imported_expenses"] == 2

    statements = await get_user_statements(1)
    assert len(statements) == 1
    assert statements[0]["bank"] == "Kaspi"


@pytest.mark.asyncio
async def test_statement_duplicate_hash(test_db, sample_transactions) -> None:
    await save_statement(
        user_id=1,
        bank="Kaspi",
        filename="a.pdf",
        file_type="pdf",
        file_hash="same_hash",
        transactions=sample_transactions,
    )
    assert await statement_exists(1, "same_hash")


@pytest.mark.asyncio
async def test_delete_statement_removes_expenses(test_db, sample_transactions) -> None:
    summary = await save_statement(
        user_id=1,
        bank="Kaspi",
        filename="del.pdf",
        file_type="pdf",
        file_hash="del_hash",
        transactions=sample_transactions,
    )
    statement_id = summary["statement_id"]

    stats_before = await get_monthly_stats(1)
    assert stats_before["grand_total"] > 0

    result = await delete_statement(1, statement_id)
    assert result is not None
    assert result["expenses_removed"] == 2

    stats_after = await get_monthly_stats(1)
    assert stats_after["grand_total"] == 0
    assert await get_user_statements(1) == []


@pytest.mark.asyncio
async def test_delete_statement_wrong_user(test_db, sample_transactions) -> None:
    summary = await save_statement(
        user_id=1,
        bank="Kaspi",
        filename="x.pdf",
        file_type="pdf",
        file_hash="x_hash",
        transactions=sample_transactions,
    )
    result = await delete_statement(999, summary["statement_id"])
    assert result is None
    assert len(await get_user_statements(1)) == 1


@pytest.mark.asyncio
async def test_manual_expense_not_deleted_with_statement(test_db, sample_transactions) -> None:
    await add_expense(1, "Кафе", 500.0)
    summary = await save_statement(
        user_id=1,
        bank="Kaspi",
        filename="mix.pdf",
        file_type="pdf",
        file_hash="mix_hash",
        transactions=sample_transactions,
    )

    await delete_statement(1, summary["statement_id"])

    stats = await get_monthly_stats(1)
    assert stats["grand_total"] == 500.0
