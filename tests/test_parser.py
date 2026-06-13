from bot.services.statements.parser import detect_file_type, file_hash, parse_statement


def test_file_hash_stable() -> None:
    assert file_hash(b"abc") == file_hash(b"abc")
    assert file_hash(b"abc") != file_hash(b"abcd")


def test_detect_file_type_pdf() -> None:
    assert detect_file_type("stmt.pdf", b"%PDF-1.4 content") == "pdf"


def test_detect_file_type_onec() -> None:
    content = b"1CClientBankExchange\n\xd0\xa1\xd0\xb5\xd0\xba\xd1\x86\xd0\xb8\xd1\x8f"
    assert detect_file_type("stmt.txt", content) == "onec"


def test_parse_csv_statement() -> None:
    csv = (
        "Дата;Описание;Сумма\n"
        "15.03.2024;Magnum;-1500.00\n"
    ).encode("utf-8")
    result = parse_statement(csv, "test.csv", "auto")
    assert len(result.transactions) == 1
    assert result.transactions[0].amount == 1500.0
