import pytest

from bot.services.statements.categorizer import categorize_description


@pytest.mark.parametrize(
    "description,expected",
    [
        ("Оплата Magnum CU-1", "Продукты"),
        ("Yandex Go поездка", "Транспорт"),
        ("KFC Almaty", "Кафе"),
        ("Неизвестный магазин XYZ", "Банк"),
    ],
)
def test_categorize_description(description: str, expected: str) -> None:
    assert categorize_description(description) == expected
