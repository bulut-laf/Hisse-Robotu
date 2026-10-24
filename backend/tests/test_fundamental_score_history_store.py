from __future__ import annotations

from datetime import date, datetime, timezone

from backend.app.analysis.fundamental_quality import (
    FundamentalQualityComponent,
    FundamentalQualityScore,
)
from backend.app.data.fundamental_score_store import (
    FundamentalScoreJsonStore,
)


def component(name: str, score: int, maximum: int):
    return FundamentalQualityComponent(
        name=name,
        score=score,
        maximum_score=maximum,
        reasons=(),
        risks=(),
    )


def score(symbol: str, period_key: str, total: int):
    return FundamentalQualityScore(
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
    )


def write_record(
    store,
    *,
    symbol,
    period_key,
    period_end,
    total,
):
    records = store._read()
    records[f"{symbol}|{period_key}"] = {
        "symbol": symbol,
        "period_key": period_key,
        "period_end": period_end.isoformat(),
        "data_identity": f"id-{symbol}-{period_key}",
        "calculated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "score": {
            "symbol": symbol,
            "period_key": period_key,
            "total_score": total,
            "locked": False,
            "explanation": "test",
            "profitability": {
                "name": "Kârlılık",
                "score": 20,
                "maximum_score": 25,
                "reasons": [],
                "risks": [],
            },
            "growth": {
                "name": "Büyüme",
                "score": 20,
                "maximum_score": 25,
                "reasons": [],
                "risks": [],
            },
            "leverage": {
                "name": "Borçluluk",
                "score": 15,
                "maximum_score": 20,
                "reasons": [],
                "risks": [],
            },
            "liquidity": {
                "name": "Likidite",
                "score": 12,
                "maximum_score": 15,
                "reasons": [],
                "risks": [],
            },
            "cash_flow": {
                "name": "Nakit akışı",
                "score": 13,
                "maximum_score": 15,
                "reasons": [],
                "risks": [],
            },
        },
    }
    store.path.parent.mkdir(parents=True, exist_ok=True)
    import json
    store.path.write_text(
        json.dumps(records, ensure_ascii=False),
        encoding="utf-8",
    )


def test_sirket_skor_gecmisi_donem_sirasiyla_okunur(tmp_path):
    store = FundamentalScoreJsonStore(tmp_path / "scores.json")
    write_record(
        store,
        symbol="AAA",
        period_key="2025Q4",
        period_end=date(2025, 12, 31),
        total=65,
    )
    write_record(
        store,
        symbol="AAA",
        period_key="2026Q1",
        period_end=date(2026, 3, 31),
        total=72,
    )

    history = store.load_history(
        "AAA",
        today=date(2026, 7, 30),
    )

    assert tuple(item.period_key for item in history) == (
        "2025Q4",
        "2026Q1",
    )


def test_eski_skor_gecmise_alinmaz(tmp_path):
    store = FundamentalScoreJsonStore(tmp_path / "scores.json")
    write_record(
        store,
        symbol="AAA",
        period_key="2023Q4",
        period_end=date(2023, 12, 31),
        total=60,
    )

    history = store.load_history(
        "AAA",
        today=date(2026, 7, 30),
        maximum_age_days=365,
    )

    assert history == ()


def test_sirket_karsilastirmasi_ayni_en_yeni_donemi_kullanir(
    tmp_path,
):
    store = FundamentalScoreJsonStore(tmp_path / "scores.json")
    write_record(
        store,
        symbol="AAA",
        period_key="2026Q2",
        period_end=date(2026, 6, 30),
        total=80,
    )
    write_record(
        store,
        symbol="BBB",
        period_key="2026Q2",
        period_end=date(2026, 6, 30),
        total=70,
    )
    write_record(
        store,
        symbol="CCC",
        period_key="2026Q1",
        period_end=date(2026, 3, 31),
        total=90,
    )

    comparable = store.load_comparable_latest(
        today=date(2026, 7, 30)
    )

    assert tuple(item.symbol for item in comparable) == (
        "AAA",
        "BBB",
    )
