from __future__ import annotations

from datetime import date

from backend.app.analysis.fundamental_analysis import (
    build_fundamental_snapshot,
)
from backend.app.analysis.fundamental_quality import (
    calculate_fundamental_quality,
)
from backend.app.data.fundamental_data import (
    FundamentalFreshnessResult,
)
from backend.app.data.fundamental_score_store import (
    FundamentalScoreJsonStore,
    financial_periods_identity,
)
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
    }
    values.update(overrides)
    return FinancialPeriod(**values)


def score(periods):
    snapshot = build_fundamental_snapshot(list(periods))
    freshness = FundamentalFreshnessResult(
        status="Güncel",
        latest_period_end=date(2026, 6, 30),
        age_days=30,
        locked=False,
        explanation="test",
    )
    return calculate_fundamental_quality(snapshot, freshness)


def test_ayni_veri_kimligi_tekrar_kaydedilmez(tmp_path):
    periods = (
        period(),
        period(
            period_end=date(2025, 6, 30),
            fiscal_year=2025,
            revenue=800,
            ebitda=160,
            net_income=80,
        ),
    )
    store = FundamentalScoreJsonStore(
        tmp_path / "scores.json"
    )

    first = store.save(periods=periods, score=score(periods))
    second = store.save(periods=periods, score=score(periods))

    assert first.inserted == 1
    assert second.unchanged == 1
    assert financial_periods_identity(periods)


def test_finansal_veri_degisirse_skor_kaydi_guncellenir(
    tmp_path,
):
    first_periods = (
        period(),
        period(
            period_end=date(2025, 6, 30),
            fiscal_year=2025,
            revenue=800,
            ebitda=160,
            net_income=80,
        ),
    )
    changed_periods = (
        period(revenue=1100),
        first_periods[1],
    )
    store = FundamentalScoreJsonStore(
        tmp_path / "scores.json"
    )
    store.save(
        periods=first_periods,
        score=score(first_periods),
    )

    result = store.save(
        periods=changed_periods,
        score=score(changed_periods),
    )

    assert result.updated == 1


def test_guncel_kayitli_skor_otomatik_okunur(tmp_path):
    periods = (
        period(),
        period(
            period_end=date(2025, 6, 30),
            fiscal_year=2025,
            revenue=800,
            ebitda=160,
            net_income=80,
        ),
    )
    store = FundamentalScoreJsonStore(
        tmp_path / "scores.json"
    )
    store.save(periods=periods, score=score(periods))

    loaded = store.load_latest_scores(
        today=date(2026, 7, 30)
    )

    assert "THYAO" in loaded
    assert loaded["THYAO"].total_score is not None


def test_eski_kayitli_skor_kullanilmaz(tmp_path):
    old_periods = (
        period(
            period_end=date(2025, 6, 30),
            fiscal_year=2025,
        ),
        period(
            period_end=date(2024, 6, 30),
            fiscal_year=2024,
            revenue=800,
        ),
    )
    store = FundamentalScoreJsonStore(
        tmp_path / "scores.json"
    )
    store.save(
        periods=old_periods,
        score=score(old_periods),
    )

    loaded = store.load_latest_scores(
        today=date(2026, 7, 30),
        maximum_age_days=190,
    )

    assert loaded == {}
