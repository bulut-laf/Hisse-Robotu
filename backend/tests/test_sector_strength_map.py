from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from backend.app.analysis.fundamental_quality import (
    FundamentalQualityComponent,
    FundamentalQualityScore,
)
from backend.app.analysis.sector_reference import SectorReference
from backend.app.analysis.sector_strength_map import (
    SectorStrengthMapError,
    build_sector_strength_map,
    sector_direction,
    sector_strength_rows,
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


def stored(symbol, total, period_key, period_end, locked=False):
    score = FundamentalQualityScore(
        symbol=symbol,
        period_key=period_key,
        total_score=total,
        profitability=component("Kârlılık", 20, 25),
        growth=component("Büyüme", 20, 25),
        leverage=component("Borçluluk", 15, 20),
        liquidity=component("Likidite", 12, 15),
        cash_flow=component("Nakit akışı", 13, 15),
        locked=locked,
        explanation="test",
    )
    return StoredFundamentalScore(
        symbol=symbol,
        period_key=period_key,
        period_end=period_end,
        data_identity=f"id-{symbol}-{period_key}",
        score=score,
        calculated_at=datetime.now(timezone.utc),
    )


def references():
    return {
        "AAA": SectorReference("AAA", "Sanayi"),
        "BBB": SectorReference("BBB", "Sanayi"),
        "CCC": SectorReference("CCC", "Sanayi"),
        "DDD": SectorReference("DDD", "Bankacılık"),
        "EEE": SectorReference("EEE", "Bankacılık"),
        "FFF": SectorReference("FFF", "Bankacılık"),
    }


def current_scores():
    q2 = date(2026, 6, 30)
    q1 = date(2026, 3, 31)
    return (
        stored("AAA", 80, "2026Q2", q2),
        stored("BBB", 70, "2026Q2", q2),
        stored("CCC", 60, "2026Q2", q2),
        stored("DDD", 65, "2026Q2", q2),
        stored("EEE", 55, "2026Q2", q2),
        stored("FFF", 45, "2026Q2", q2),
        stored("AAA", 70, "2026Q1", q1),
        stored("BBB", 65, "2026Q1", q1),
        stored("CCC", 55, "2026Q1", q1),
        stored("DDD", 70, "2026Q1", q1),
        stored("EEE", 60, "2026Q1", q1),
        stored("FFF", 50, "2026Q1", q1),
    )


def test_sektorler_medyan_skoruna_gore_siralanir():
    result = build_sector_strength_map(
        current_scores(),
        references(),
    )

    assert tuple(item.sector for item in result.items) == (
        "Sanayi",
        "Bankacılık",
    )
    assert result.items[0].median_score == 70.0
    assert result.items[1].median_score == 55.0


def test_sirket_sinifi_dagilimi_hesaplanir():
    result = build_sector_strength_map(
        current_scores(),
        references(),
    )
    sanayi = result.items[0]

    assert sanayi.strong_count == 1
    assert sanayi.balanced_count == 1
    assert sanayi.watch_count == 1
    assert sanayi.weak_count == 0


def test_donemsel_sektor_degisim_yonu_hesaplanir():
    result = build_sector_strength_map(
        current_scores(),
        references(),
    )

    assert result.items[0].median_change == 5.0
    assert result.items[0].direction == "Güçleniyor"
    assert result.items[1].median_change == -5.0
    assert result.items[1].direction == "Zayıflıyor"


@pytest.mark.parametrize(
    ("change", "expected"),
    (
        (3.0, "Güçleniyor"),
        (2.9, "Yatay"),
        (-2.9, "Yatay"),
        (-3.0, "Zayıflıyor"),
        (None, "Önceki dönem yok"),
    ),
)
def test_sektor_yonu_esikleri(change, expected):
    assert sector_direction(change) == expected


def test_asgari_sirket_sayisi_olmayan_sektor_dislanir():
    refs = references()
    scores = tuple(
        item
        for item in current_scores()
        if item.symbol not in {"CCC"}
    )

    result = build_sector_strength_map(scores, refs)

    assert tuple(item.sector for item in result.items) == (
        "Bankacılık",
    )


def test_kilitli_skor_haritaya_alinmaz():
    q2 = date(2026, 6, 30)
    scores = (
        stored("AAA", 80, "2026Q2", q2),
        stored("BBB", 70, "2026Q2", q2),
        stored("CCC", 60, "2026Q2", q2, locked=True),
    )

    with pytest.raises(
        SectorStrengthMapError,
        match="yeterli şirket",
    ):
        build_sector_strength_map(scores, references())


def test_harita_satirlari_uretilir():
    result = build_sector_strength_map(
        current_scores(),
        references(),
    )
    rows = sector_strength_rows(result)

    assert rows[0]["Sektör"] == "Sanayi"
    assert rows[0]["Yön"] == "Güçleniyor"
