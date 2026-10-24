from datetime import date
from decimal import Decimal

from backend.app.funds.analysis_engine import FundAnalysisClass, FundAnalysisResult
from backend.app.funds.outcome import FundPricePoint, evaluate_forward_outcomes


def analysis():
    return FundAnalysisResult("fund:tefas:AAA", "equity", FundAnalysisClass.B, "GELŞEN", ("F1", "F2"), ("F3",), (), (), "DEV", "x")


def test_1h_1a_3a_forward_identity_and_states():
    prices = (FundPricePoint("fund:tefas:AAA", date(2026, 1, 8), Decimal("110")),)
    rows = evaluate_forward_outcomes(analysis(), selection_date=date(2026, 1, 1), start_price=Decimal("100"), prices=prices, as_of=date(2026, 1, 10))
    assert tuple(x.horizon.value for x in rows) == ("1H", "1A", "3A")
    assert rows[0].status == "OBSERVED" and rows[0].absolute_return == Decimal("0.1")
    assert rows[1].status == rows[2].status == "PENDING"
    assert all(x.tuning_authority == "NONE" for x in rows)


def test_due_but_absent_is_missing_not_synthetic():
    rows = evaluate_forward_outcomes(analysis(), selection_date=date(2026, 1, 1), start_price=Decimal("100"), prices=(), as_of=date(2026, 5, 1))
    assert all(x.status == "MISSING" and x.end_price is None for x in rows)
