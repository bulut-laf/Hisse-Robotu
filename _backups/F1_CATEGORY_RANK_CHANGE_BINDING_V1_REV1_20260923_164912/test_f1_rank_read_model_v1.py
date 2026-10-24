from datetime import date
from decimal import Decimal

from backend.app.funds.f1_rank_history import (
    FundCategoryRankHistoryJsonStore,
    FundCategoryRankObservation,
)
from backend.app.funds import f1_rank_read_model


def test_f1_rank_metrics_lower_rank_is_better(tmp_path, monkeypatch):
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
            category_rank=176,
            category_fund_count=200,
        ),
    ))

    monkeypatch.setattr(
        f1_rank_read_model,
        "fund_category_rank_history_store",
        lambda: store,
    )

    metrics = f1_rank_read_model.f1_rank_metrics_by_fund()
    percentile, change = metrics["fund:tefas:PHE"]

    assert percentile == Decimal("0.125")
    assert change == -155
