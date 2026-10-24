from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.app.analysis.fundamental_analysis import (
    build_fundamental_snapshot,
)
from backend.app.analysis.fundamental_quality import (
    apply_optional_fundamental_filter,
    calculate_fundamental_quality,
)
from backend.app.data.fundamental_data import (
    FundamentalFreshnessResult,
)
from backend.app.models.fundamental_models import FinancialPeriod


def period(year, quarter, end, **overrides):
    values = {
        "symbol": "AAA",
        "period_end": end,
        "fiscal_year": year,
        "fiscal_quarter": quarter,
        "currency": "TRY",
        "revenue": "1000",
        "gross_profit": "350",
        "operating_profit": "220",
        "ebitda": "250",
        "net_income": "180",
        "total_assets": "2200",
        "total_equity": "1000",
        "total_debt": "500",
        "cash_and_equivalents": "300",
        "current_assets": "900",
        "current_liabilities": "500",
        "operating_cash_flow": "220",
        "capital_expenditure": "70",
        "shares_outstanding": "100",
    }
    values.update(overrides)
    return FinancialPeriod(**values)


def freshness(locked=False):
    return FundamentalFreshnessResult(
        status="Güncel" if not locked else "Eski bilanço",
        latest_period_end=date(2026, 6, 30),
        age_days=30,
        locked=locked,
        explanation="test",
    )


def test_guclu_finansallar_yuksek_kalite_skoru_uretir():
    snapshot = build_fundamental_snapshot(
        [
            period(2026, 2, date(2026, 6, 30)),
            period(
                2025,
                2,
                date(2025, 6, 30),
                revenue="800",
                ebitda="180",
                net_income="120",
                operating_cash_flow="160",
            ),
        ]
    )

    score = calculate_fundamental_quality(
        snapshot,
        freshness(),
    )

    assert score.locked is False
    assert score.total_score is not None
    assert 0 <= score.total_score <= 100
    assert score.total_score >= 65


def test_eski_bilancoda_skor_uretilmez():
    snapshot = build_fundamental_snapshot(
        [period(2026, 2, date(2026, 6, 30))]
    )

    score = calculate_fundamental_quality(
        snapshot,
        freshness(locked=True),
    )

    assert score.locked is True
    assert score.total_score is None


def test_filtre_kapaliyken_adaylar_degisimez():
    candidates = ("AAA.IS", "BBB.IS")

    result = apply_optional_fundamental_filter(
        candidates,
        symbol_getter=lambda item: item,
        scores={},
        enabled=False,
        minimum_score=60,
    )

    assert result.accepted == candidates
    assert result.rejected == ()
    assert result.missing == ()


def test_filtre_acikken_esik_alti_ve_eksik_veri_ayrilir():
    snapshot = build_fundamental_snapshot(
        [
            period(2026, 2, date(2026, 6, 30)),
            period(
                2025,
                2,
                date(2025, 6, 30),
                revenue="800",
            ),
        ]
    )
    score = calculate_fundamental_quality(snapshot, freshness())

    result = apply_optional_fundamental_filter(
        ("AAA.IS", "BBB.IS"),
        symbol_getter=lambda item: item,
        scores={"AAA": score},
        enabled=True,
        minimum_score=0,
    )

    assert result.accepted == ("AAA.IS",)
    assert result.missing == ("BBB.IS",)
