from datetime import date, datetime
from decimal import Decimal

import pytest

from backend.app.analysis.market_multiples import MarketMultiplesError, calculate_market_multiples
from backend.app.analysis.ownership_float import OwnershipFloatError, assess_ownership_float
from backend.app.analysis.relative_valuation import assess_relative_valuation
from backend.app.data.historical_financial_series import HistoricalFinancialPoint, HistoricalFinancialSeries
from backend.app.models.valuation_foundation_models import MarketSnapshot, MultipleSnapshot, OwnershipSnapshot


def D(v: str) -> Decimal:
    return Decimal(v)


def series() -> HistoricalFinancialSeries:
    pub = datetime(2026, 8, 4, 18, 24, 32)
    def p(code, value, kind, start, end):
        return HistoricalFinancialPoint(
            symbol="TUPRS", metric_code=code, statement="BALANCE_SHEET" if kind == "INSTANT" else "INCOME_STATEMENT",
            source_label=code, value=D(value), period_kind=kind, period_start=start, period_end=end,
            comparison_role="X", published_at=pub, consolidation_scope="KONSOLIDE", currency="TRY", currency_scale=D("1000"),
            disclosure_id="1643116", source_sha256="x"
        )
    pts = [
        p("PARENT_EQUITY","456139125","INSTANT",None,date(2026,6,30)),
        p("CASH_EQUIVALENTS","195840940","INSTANT",None,date(2026,6,30)),
        p("SHORT_TERM_BORROWINGS","17579248","INSTANT",None,date(2026,6,30)),
        p("CURRENT_PORTION_LT_DEBT","14178331","INSTANT",None,date(2026,6,30)),
        p("LONG_TERM_BORROWINGS","36443100","INSTANT",None,date(2026,6,30)),
        p("REVENUE","662788010","DURATION",date(2026,1,1),date(2026,6,30)),
        p("REVENUE","464119398","DURATION",date(2025,1,1),date(2025,6,30)),
        p("REVENUE","1010000000","DURATION",date(2025,1,1),date(2025,12,31)),
        p("PARENT_NET_INCOME","49847684","DURATION",date(2026,1,1),date(2026,6,30)),
        p("PARENT_NET_INCOME","11872237","DURATION",date(2025,1,1),date(2025,6,30)),
        p("PARENT_NET_INCOME","34765910","DURATION",date(2025,1,1),date(2025,12,31)),
    ]
    return HistoricalFinancialSeries("TUPRS","KONSOLIDE","TRY",D("1000"),tuple(pts))


def ownership(**kw):
    base = dict(symbol="TUPRS", as_of_date=date(2026,8,4), published_at=datetime(2026,8,4,18,30), total_shares=D("1926795773"), free_float_ratio=D("0.49"), effective_free_float_ratio=D("0.46"), major_shareholder_ratio=D("0.51"))
    base.update(kw)
    return OwnershipSnapshot(**base)


def test_fin006_assesses_float_without_calling_low_float_bad_company():
    r = assess_ownership_float(ownership())
    assert r.float_liquidity_risk == "MODERATE"
    assert r.ownership_concentration == "HIGH"
    assert r.free_float_shares == D("1926795773") * D("0.46")


def test_fin006_point_in_time_fail_closed():
    with pytest.raises(OwnershipFloatError):
        assess_ownership_float(ownership(), as_of=datetime(2026,8,4,17,0))


def test_fin007_market_multiples_use_ttm_and_parent_equity():
    m = calculate_market_multiples(series(), ownership(), MarketSnapshot("TUPRS",date(2026,8,4),D("150")), as_of=datetime(2026,8,5))
    expected_ttm = (D("49847684") + D("34765910") - D("11872237")) * D("1000")
    assert m.earnings_basis == expected_ttm
    assert m.pe == m.market_cap / expected_ttm
    assert m.pb == m.market_cap / (D("456139125") * D("1000"))
    assert "EV_EBITDA_NOT_EVALUATED_WITHOUT_RELIABLE_EBITDA" in m.data_flags


def test_fin007_ev_ebitda_requires_explicit_reliable_ebitda():
    m = calculate_market_multiples(series(), ownership(), MarketSnapshot("TUPRS",date(2026,8,4),D("150")), ebitda_ttm=D("90000000000"))
    assert m.ev_ebitda is not None


def test_fin007_symbol_mismatch_fails_closed():
    with pytest.raises(MarketMultiplesError):
        calculate_market_multiples(series(), ownership(symbol="OTHER"), MarketSnapshot("TUPRS",date(2026,8,4),D("150")))


def snap(symbol, pe, pb, ev, day):
    return MultipleSnapshot(symbol, date(2026,1,day), D(pe) if pe else None, D(pb) if pb else None, D(ev) if ev else None, None, None, None, None, D("1"), D("1"), D("1"), D("1"), D("1") if ev else None, None, None)


def test_fin008_historical_and_peer_discount_premium_are_separate():
    cur = snap("TUPRS","8","1.4","5",20)
    hist = [snap("TUPRS","10","1.8","6",10), snap("TUPRS","12","2.0","7",15)]
    peers = [snap("FROTO","9","2.2","7",18), snap("SISE","11","1.6","6",19)]
    r = assess_relative_valuation(cur, history=hist, peers=peers)
    assert r.historical_medians["pe"] == D("11")
    assert r.peer_medians["pe"] == D("10")
    assert r.historical_discount_premium["pe"] < 0
    assert r.peer_discount_premium["pe"] < 0
    assert r.confidence in {"MEDIUM","HIGH"}


def test_fin008_does_not_claim_cheap_without_reference_data():
    cur = snap("TUPRS","8","1.4",None,20)
    r = assess_relative_valuation(cur)
    assert r.confidence == "LOW"
    assert "HISTORICAL_MULTIPLE_HISTORY_UNAVAILABLE" in r.warnings
    assert "PEER_SET_UNAVAILABLE" in r.warnings
