
from datetime import date
import pandas as pd

from backend.app.analysis import fin_prod_v5_short_term_context_adapter as m

class Recovery:
    def __init__(self, veri):
        self.veri = veri

def test_price_reference_excludes_future_rows(monkeypatch):
    frame = pd.DataFrame(
        {
            "Close": [100.0, 101.0, 150.0],
            "Volume": [10.0, 11.0, 99.0],
        },
        index=pd.to_datetime(["2026-08-03", "2026-08-04", "2026-09-04"]),
    )
    monkeypatch.setattr(
        m,
        "guvenli_fiyat_verisi_getir",
        lambda *a, **k: Recovery(frame),
    )
    ref, warnings, blockers = m._price_reference(
        "TUPRS",
        as_of_date=date(2026, 8, 4),
    )
    assert blockers == []
    assert ref["date"] == "2026-08-04"
    assert ref["close"] == "101.0"
    assert "FUTURE_MARKET_ROWS_EXCLUDED" in warnings

def test_price_reference_fails_closed_when_no_historical_row(monkeypatch):
    frame = pd.DataFrame(
        {"Close": [150.0], "Volume": [99.0]},
        index=pd.to_datetime(["2026-09-04"]),
    )
    monkeypatch.setattr(
        m,
        "guvenli_fiyat_verisi_getir",
        lambda *a, **k: Recovery(frame),
    )
    ref, warnings, blockers = m._price_reference(
        "TUPRS",
        as_of_date=date(2026, 8, 4),
    )
    assert ref is None
    assert "POINT_IN_TIME_PRICE_REFERENCE_MISSING" in blockers
