from datetime import date

from backend.app.funds.f1_rank_history import (
    FundCategoryRankHistoryJsonStore,
    FundCategoryRankObservation,
)

def test_f1_rank_history_roundtrip_and_upsert(tmp_path):
    store = FundCategoryRankHistoryJsonStore(tmp_path / "rank.json")
    store.upsert((
        FundCategoryRankObservation(
            canonical_fund_id="fund:tefas:PHE",
            observation_date=date(2026, 9, 8),
            category_rank=21,
            category_fund_count=200,
        ),
        FundCategoryRankObservation(
            canonical_fund_id="fund:tefas:PHE",
            observation_date=date(2026, 9, 23),
            category_rank=19,
            category_fund_count=201,
        ),
    ))
    rows = store.list_records()
    assert len(rows) == 2
    assert rows[0].category_rank == 21
    assert rows[1].category_rank == 19
