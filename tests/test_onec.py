from bot.services.statements.parsers.onec import parse_onec

ONEC_SAMPLE = """1CClientBankExchange
СекцияДокумент=Платежное поручение
Дата=15.03.2024
Сумма=1500.00
НазначениеПлатежа=Оплата в Magnum
КонецДокумента
СекцияДокумент=Поступление
Дата=16.03.2024
Сумма=50000.00
НазначениеПлатежа=Зарплата
КонецДокумента
"""


def test_parse_onec() -> None:
    result = parse_onec(ONEC_SAMPLE, "Halyk")
    assert len(result.transactions) == 2
    assert result.transactions[0].is_expense
    assert not result.transactions[1].is_expense
