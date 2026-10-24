from __future__ import annotations

from datetime import date

from backend.app.data.fundamental_score_store import FundamentalScoreJsonStore
from backend.tests.test_fundamental_score_history_store import write_record


def test_tum_gecerli_skorlar_donem_ve_sembole_gore_okunur(tmp_path):
    store = FundamentalScoreJsonStore(tmp_path / "scores.json")
    write_record(
        store,
        symbol="BBB",
        period_key="2026Q2",
        period_end=date(2026, 6, 30),
        total=70,
    )
    write_record(
        store,
        symbol="AAA",
        period_key="2026Q1",
        period_end=date(2026, 3, 31),
        total=65,
    )

    result = store.load_all_valid_scores(
        today=date(2026, 7, 31)
    )

    assert tuple(
        (item.period_key, item.symbol)
        for item in result
    ) == (
        ("2026Q1", "AAA"),
        ("2026Q2", "BBB"),
    )


def test_eski_skor_tum_gecerli_kayitlara_alinmaz(tmp_path):
    store = FundamentalScoreJsonStore(tmp_path / "scores.json")
    write_record(
        store,
        symbol="AAA",
        period_key="2023Q4",
        period_end=date(2023, 12, 31),
        total=60,
    )

    result = store.load_all_valid_scores(
        today=date(2026, 7, 31),
        maximum_age_days=365,
    )

    assert result == ()
