from __future__ import annotations

from datetime import date, datetime, timezone

from backend.app.analysis.fundamental_quality import (
    FundamentalQualityComponent,
    FundamentalQualityScore,
)
from backend.app.analysis.sector_reference import SectorReference
from backend.app.analysis.sector_score_ranking import (
    build_sector_score_ranking,
    quality_class,
)
from backend.app.analysis.sector_strength_map import (
    build_sector_strength_map,
    sector_direction,
)
from backend.app.data.fundamental_score_store import StoredFundamentalScore


def component(name: str, score: int, maximum: int):
    return FundamentalQualityComponent(
        name=name,
        score=score,
        maximum_score=maximum,
        reasons=(),
        risks=(),
    )


def stored(symbol: str, total: int, period_key: str, period_end: date):
    return StoredFundamentalScore(
        symbol=symbol,
        period_key=period_key,
        period_end=period_end,
        data_identity=f"{symbol}-{period_key}",
        calculated_at=datetime.now(timezone.utc),
        score=FundamentalQualityScore(
            symbol=symbol,
            period_key=period_key,
            total_score=total,
            profitability=component("Kârlılık", 20, 25),
            growth=component("Büyüme", 20, 25),
            leverage=component("Borçluluk", 15, 20),
            liquidity=component("Likidite", 12, 15),
            cash_flow=component("Nakit akışı", 13, 15),
            locked=False,
            explanation="test",
        ),
    )


def test_ozel_kalite_esikleri_siniflandirmayi_degistirir():
    assert quality_class(82) == "Güçlü"
    assert quality_class(
        82,
        strong_threshold=85,
        balanced_threshold=70,
        watch_threshold=55,
    ) == "Dengeli"


def test_ozel_esikler_sektor_siralamasina_uygulanir():
    q2 = date(2026, 6, 30)
    refs = {
        symbol: SectorReference(symbol, "Sanayi")
        for symbol in ("AAA", "BBB", "CCC")
    }
    ranking = build_sector_score_ranking(
        (
            stored("AAA", 82, "2026Q2", q2),
            stored("BBB", 72, "2026Q2", q2),
            stored("CCC", 58, "2026Q2", q2),
        ),
        refs,
        "Sanayi",
        strong_threshold=85,
        balanced_threshold=70,
        watch_threshold=55,
    )

    assert tuple(
        item.quality_class for item in ranking.items
    ) == ("Dengeli", "Dengeli", "İzlenmeli")


def test_ozel_sektor_degisim_esigi_yonu_degistirir():
    assert sector_direction(4.0) == "Güçleniyor"
    assert sector_direction(
        4.0,
        change_threshold=5.0,
    ) == "Yatay"


def test_ozel_ayarlar_guc_haritasina_uygulanir():
    q2 = date(2026, 6, 30)
    q1 = date(2026, 3, 31)
    refs = {
        symbol: SectorReference(symbol, "Sanayi")
        for symbol in ("AAA", "BBB", "CCC")
    }
    scores = (
        stored("AAA", 82, "2026Q2", q2),
        stored("BBB", 72, "2026Q2", q2),
        stored("CCC", 58, "2026Q2", q2),
        stored("AAA", 78, "2026Q1", q1),
        stored("BBB", 68, "2026Q1", q1),
        stored("CCC", 54, "2026Q1", q1),
    )

    result = build_sector_strength_map(
        scores,
        refs,
        strong_threshold=85,
        balanced_threshold=70,
        watch_threshold=55,
        change_threshold=5.0,
    )

    item = result.items[0]
    assert item.strong_count == 0
    assert item.balanced_count == 2
    assert item.watch_count == 1
    assert item.direction == "Yatay"
