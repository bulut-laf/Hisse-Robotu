from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from backend.app.analysis.fundamental_analysis import (
    build_fundamental_snapshot,
    calculate_growth,
    calculate_ratios,
)
from backend.app.models.fundamental_models import FinancialPeriod


def period(year, quarter, end, **overrides):
    values = {
        "symbol": "THYAO",
        "period_end": end,
        "fiscal_year": year,
        "fiscal_quarter": quarter,
        "currency": "TRY",
        "revenue": "1000",
        "gross_profit": "300",
        "operating_profit": "180",
        "ebitda": "200",
        "net_income": "100",
        "total_assets": "2500",
        "total_equity": "1000",
        "total_debt": "700",
        "cash_and_equivalents": "200",
        "current_assets": "900",
        "current_liabilities": "600",
        "operating_cash_flow": "160",
        "capital_expenditure": "40",
        "shares_outstanding": "100",
    }
    values.update(overrides)
    return FinancialPeriod(**values)


def test_temel_oranlar_hesaplanir():
    result = calculate_ratios(
        period(2026, 2, date(2026, 6, 30))
    )

    assert result.gross_margin == Decimal("30.00")
    assert result.ebitda_margin == Decimal("20.00")
    assert result.roe == Decimal("10.00")
    assert result.current_ratio == Decimal("1.50")
    assert result.net_debt == Decimal("500.00")
    assert result.free_cash_flow == Decimal("120.00")


def test_büyüme_oranlari_hesaplanir():
    previous = period(
        2025,
        2,
        date(2025, 6, 30),
        revenue="800",
        net_income="80",
    )
    current = period(
        2026,
        2,
        date(2026, 6, 30),
        revenue="1000",
        net_income="100",
    )

    growth = calculate_growth(current, previous)

    assert growth.revenue_growth == Decimal("25.00")
    assert growth.net_income_growth == Decimal("25.00")


def test_snapshot_onceki_ceyrek_ve_yillik_donemi_bulur():
    latest = period(2026, 2, date(2026, 6, 30))
    previous_quarter = period(
        2026,
        1,
        date(2026, 3, 31),
        revenue="900",
    )
    previous_year = period(
        2025,
        2,
        date(2025, 6, 30),
        revenue="800",
    )

    snapshot = build_fundamental_snapshot(
        [previous_year, latest, previous_quarter],
        source_metadata={"provider": "test"},
    )

    assert snapshot.latest.period_key == "2026Q2"
    assert snapshot.previous_quarter == previous_quarter
    assert snapshot.previous_year_same_quarter == previous_year
    assert snapshot.quarter_growth is not None
    assert snapshot.annual_growth is not None
    assert snapshot.source_metadata["provider"] == "test"


def test_negatif_nakit_akisi_kalite_bayragi_uretir():
    latest = period(
        2026,
        2,
        date(2026, 6, 30),
        operating_cash_flow="-20",
        capital_expenditure="40",
    )

    snapshot = build_fundamental_snapshot([latest])

    assert (
        "İşletme faaliyetlerinden nakit akışı negatif."
        in snapshot.quality_flags
    )
    assert (
        "Serbest nakit akışı negatif."
        in snapshot.quality_flags
    )


def test_farkli_para_birimleri_ayni_snapshotta_reddedilir():
    first = period(2026, 2, date(2026, 6, 30))
    second = period(
        2026,
        1,
        date(2026, 3, 31),
        currency="USD",
    )

    with pytest.raises(ValueError, match="para birimi"):
        build_fundamental_snapshot([first, second])
