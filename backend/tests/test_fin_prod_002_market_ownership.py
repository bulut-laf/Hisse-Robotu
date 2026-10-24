from decimal import Decimal
from app.data.market_ownership_canonical import from_dict


def test_bist_valuation_unit_contract_for_tuprs():
    x = from_dict({
        "symbol": "TUPRS",
        "as_of_date": "2026-08-04",
        "published_at": "2026-08-04T18:24:32",
        "issued_capital_try": "1926795598",
        "quote_nominal_unit_try": "1",
        "valuation_units": "1926795598",
        "legal_share_nominal_try": "0.01",
        "legal_share_piece_count": "192679559800",
        "free_float_ratio": "49.43",
        "effective_free_float_ratio": "49.43",
        "controlling_group_ratio": "50.7"
    })
    assert x.valuation_units == Decimal("1926795598")
    assert x.legal_share_piece_count == Decimal("192679559800")
    assert x.effective_float_ratio == Decimal("0.4943")
    assert x.controlling_group_ratio == Decimal("0.507")


def test_market_cap_uses_valuation_units_not_legal_piece_count():
    x = from_dict({
        "symbol": "TUPRS",
        "as_of_date": "2026-08-04",
        "issued_capital_try": "1926795598",
        "quote_nominal_unit_try": "1",
        "valuation_units": "1926795598",
        "legal_share_nominal_try": "0.01",
        "legal_share_piece_count": "192679559800",
        "free_float_ratio": "49.43",
        "price_try": "250",
        "price_date": "2026-08-04"
    })
    assert x.market_cap_try == Decimal("481698899500")
    assert x.market_cap_try != Decimal("250") * x.legal_share_piece_count
