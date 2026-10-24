from __future__ import annotations

from datetime import date

from backend.app.data.fundamental_store import FundamentalJsonStore
from backend.app.models.fundamental_models import FinancialPeriod


def period(**overrides):
    values = {
        "symbol": "THYAO",
        "period_end": date(2026, 6, 30),
        "fiscal_year": 2026,
        "fiscal_quarter": 2,
        "currency": "TRY",
        "revenue": 1000,
        "gross_profit": 300,
        "operating_profit": 180,
        "ebitda": 220,
        "net_income": 120,
        "total_assets": 2500,
        "total_equity": 1000,
        "total_debt": 700,
        "cash_and_equivalents": 200,
        "current_assets": 900,
        "current_liabilities": 600,
        "operating_cash_flow": 160,
        "capital_expenditure": 40,
        "shares_outstanding": 100,
        "source": "KAP",
        "published_at": date(2026, 7, 20),
    }
    values.update(overrides)
    return FinancialPeriod(**values)


def test_ilk_kayit_eklenir(tmp_path):
    store = FundamentalJsonStore(tmp_path / "fundamentals.json")

    result = store.upsert([period()])

    assert result.inserted == 1
    assert result.total_records == 1


def test_ayni_donem_tekrar_eklenmez(tmp_path):
    store = FundamentalJsonStore(tmp_path / "fundamentals.json")
    store.upsert([period()])

    result = store.upsert([period()])

    assert result.unchanged == 1
    assert result.inserted == 0


def test_ayni_donem_degisirse_guncellenir(tmp_path):
    store = FundamentalJsonStore(tmp_path / "fundamentals.json")
    store.upsert([period()])

    result = store.upsert([period(revenue=1100)])

    assert result.updated == 1
    assert result.total_records == 1
