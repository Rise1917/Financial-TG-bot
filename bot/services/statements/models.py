from dataclasses import dataclass, field


@dataclass
class ParsedTransaction:
    date: str
    amount: float
    is_expense: bool
    description: str
    bank_category: str = ""


@dataclass
class ParseResult:
    transactions: list[ParsedTransaction] = field(default_factory=list)
    bank_detected: str = ""
    period_from: str = ""
    period_to: str = ""
    errors: list[str] = field(default_factory=list)
