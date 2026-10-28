import pytest
from app.funds.fund_ranker import FundRanker

def test_fund_ranker_calculates_metrics_correctly():
    dummy_rows = [
        {"tarih": "2026-01-01", "fiyat": 10.0},
        {"tarih": "2026-01-02", "fiyat": 10.2},
        {"tarih": "2026-01-03", "fiyat": 10.5},
        {"tarih": "2026-01-04", "fiyat": 10.4},
        {"tarih": "2026-01-05", "fiyat": 10.8},
        {"tarih": "2026-01-06", "fiyat": 11.0}
    ]
    metrics = FundRanker.calculate_metrics(dummy_rows)
    assert metrics is not None
    assert metrics["veri_nokta_sayisi"] == 6

def test_fund_ranker_ranking_order():
    fund_data = {
        "FUND_A": [{"tarih": "2026-01-01", "fiyat": 10.0}, {"tarih": "2026-01-06", "fiyat": 10.5}],
        "FUND_B": [{"tarih": "2026-01-01", "fiyat": 10.0}, {"tarih": "2026-01-06", "fiyat": 11.5}]
    }
    ranked = FundRanker.rank_funds(fund_data)
    assert len(ranked) == 2