from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from backend.app.analysis.fundamental_quality import (
    FundamentalQualityComponent,
    FundamentalQualityScore,
)
from backend.app.analysis.sector_reference import SectorReference
from backend.app.analysis.sector_score_ranking import (
    SectorScoreRankingError,
    build_sector_score_ranking,
    quality_class,
    relative_position,
    sector_score_ranking_rows,
)
from backend.app.data.fundamental_score_store import (
    StoredFundamentalScore,
)


def component(name: str, score: int, maximum: int):
    return FundamentalQualityComponent(
        name=name,
        score=score,
        maximum_score=maximum,
        reasons=(),
        risks=(),
    )


def stored(
    symbol: str,
    total: int,
    *,
    period_key: str = "2026Q2",
    period_end: date = date(2026, 6, 30),
    locked: bool = False,
):
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
        data_identity=f"id-{symbol}",
        score=score,
        calculated_at=datetime.now(timezone.utc),
    )


def references():
    return {
        "AAA": SectorReference("AAA", "Sanayi"),
        "BBB": SectorReference("BBB", "Sanayi"),
        "CCC": SectorReference("CCC", "Sanayi"),
        "DDD": SectorReference("DDD", "Bankacılık"),
    }


@pytest.mark.parametrize(
    ("score", "expected"),
    (
        (80, "Güçlü"),
        (65, "Dengeli"),
        (50, "İzlenmeli"),
        (49, "Zayıf"),
    ),
)
def test_kalite_sinifi_esikleri(score, expected):
    assert quality_class(score) == expected


def test_sektor_skorlari_azalan_siralanir():
    ranking = build_sector_score_ranking(
        (
            stored("AAA", 70),
            stored("BBB", 85),
            stored("CCC", 55),
        ),
        references(),
        "Sanayi",
    )

    assert tuple(item.symbol for item in ranking.items) == (
        "BBB",
        "AAA",
        "CCC",
    )
    assert tuple(item.rank for item in ranking.items) == (
        1,
        2,
        3,
    )
    assert ranking.sector_median == 70.0


def test_alt_skorlar_siralama_satirinda_gosterilir():
    ranking = build_sector_score_ranking(
        (
            stored("AAA", 70),
            stored("BBB", 85),
            stored("CCC", 55),
        ),
        references(),
        "Sanayi",
    )

    row = sector_score_ranking_rows(ranking)[0]

    assert row["Kârlılık"] == 20
    assert row["Büyüme"] == 20
    assert row["Borçluluk"] == 15
    assert row["Likidite"] == 12
    assert row["Nakit akışı"] == 13


def test_eski_donem_ayni_siralamaya_alinmaz():
    ranking = build_sector_score_ranking(
        (
            stored("AAA", 70),
            stored("BBB", 85),
            stored("CCC", 55),
            stored(
                "DDD",
                95,
                period_key="2026Q1",
                period_end=date(2026, 3, 31),
            ),
        ),
        {
            **references(),
            "DDD": SectorReference("DDD", "Sanayi"),
        },
        "Sanayi",
    )

    assert ranking.peer_count == 3
    assert all(item.symbol != "DDD" for item in ranking.items)


def test_kilitli_skor_siralamaya_alinmaz():
    with pytest.raises(
        SectorScoreRankingError,
        match="en az 3 şirket",
    ):
        build_sector_score_ranking(
            (
                stored("AAA", 70),
                stored("BBB", 85),
                stored("CCC", 55, locked=True),
            ),
            references(),
            "Sanayi",
        )


def test_asgari_sirket_sayisi_korunur():
    with pytest.raises(
        SectorScoreRankingError,
        match="en az 3 şirket",
    ):
        build_sector_score_ranking(
            (
                stored("AAA", 70),
                stored("BBB", 85),
            ),
            references(),
            "Sanayi",
        )


def test_medyan_goreli_konumu_tarafsiz_yazar():
    assert (
        relative_position(85, 70.0)
        == "Sektör medyanının belirgin üzerinde"
    )
    assert (
        relative_position(55, 70.0)
        == "Sektör medyanının belirgin altında"
    )
    assert (
        relative_position(72, 70.0)
        == "Sektör medyanına yakın"
    )
