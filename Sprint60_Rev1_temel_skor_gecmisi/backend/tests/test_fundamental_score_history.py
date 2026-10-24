from __future__ import annotations

from datetime import date, datetime, timezone

from backend.app.analysis.fundamental_quality import (
    FundamentalQualityComponent,
    FundamentalQualityScore,
)
from backend.app.analysis.fundamental_score_history import (
    calculate_score_change,
    comparison_rows,
    history_rows,
    latest_score_change,
)
from backend.app.data.fundamental_score_store import (
    StoredFundamentalScore,
)


def stored(period_key, period_end, total, profitability):
    score = FundamentalQualityScore(
        symbol="AAA",
        period_key=period_key,
        total_score=total,
        profitability=FundamentalQualityComponent(
            "Kârlılık", profitability, 25, (), ()
        ),
        growth=FundamentalQualityComponent(
            "Büyüme", 20, 25, (), ()
        ),
        leverage=FundamentalQualityComponent(
            "Borçluluk", 15, 20, (), ()
        ),
        liquidity=FundamentalQualityComponent(
            "Likidite", 12, 15, (), ()
        ),
        cash_flow=FundamentalQualityComponent(
            "Nakit akışı", 13, 15, (), ()
        ),
        locked=False,
        explanation="test",
    )
    return StoredFundamentalScore(
        symbol="AAA",
        period_key=period_key,
        period_end=period_end,
        data_identity="id",
        score=score,
        calculated_at=datetime.now(timezone.utc),
    )


def test_skor_degisimini_ve_guclenen_bilesenleri_bulur():
    previous = stored(
        "2026Q1",
        date(2026, 3, 31),
        70,
        15,
    )
    current = stored(
        "2026Q2",
        date(2026, 6, 30),
        76,
        21,
    )

    change = calculate_score_change(current, previous)

    assert change.total_change == 6
    assert change.profitability_change == 6
    assert change.improving_components == ("Kârlılık",)
    assert change.weakening_components == ()


def test_tek_donemde_son_degisim_yoktur():
    item = stored(
        "2026Q2",
        date(2026, 6, 30),
        76,
        21,
    )

    assert latest_score_change((item,)) is None


def test_tablo_satirlari_uretilir():
    item = stored(
        "2026Q2",
        date(2026, 6, 30),
        76,
        21,
    )

    assert history_rows((item,))[0]["Toplam skor"] == 76
    assert comparison_rows((item,))[0]["Temel skor"] == 76
