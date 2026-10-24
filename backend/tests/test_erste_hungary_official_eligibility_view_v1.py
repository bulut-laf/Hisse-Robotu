from backend.app.funds.international.erste_hungary_rank_seed import build_rank_seed
from _discovery.erste_hungary.build_official_eligibility_view_v1 import build_eligibility_view


def test_officially_ineligible_funds_are_excluded_from_discovery_view():
    seed = [
        {"isin": "LU0011850392", "category_raw": "Rszvny", "rank_position": 1},
        {"isin": "LU0113311731", "category_raw": "Rszvny", "rank_position": 2},
        {"isin": "LU0117895796", "category_raw": "Rszvny", "rank_position": 3},
        {"isin": "LU0823403356", "category_raw": "Rszvny", "rank_position": 4},
        {"isin": "LU9999999999", "category_raw": "Rszvny", "rank_position": 5},
    ]
    review = {
        "records": [
            {"isin": "LU0011850392", "ranking_eligible": False},
            {"isin": "LU0113311731", "ranking_eligible": False},
            {"isin": "LU0117895796", "ranking_eligible": False},
            {"isin": "LU0823403356", "ranking_eligible": False},
        ],
        "trade_authority": "NONE",
        "forced_fill": False,
        "production_decisions_modified": False,
        "rank_history_modified": False,
    }

    original_seed = [dict(row) for row in seed]
    result = build_eligibility_view(seed, review)

    assert result["original_seed_count"] == 5
    assert result["excluded_count"] == 4
    assert result["excluded_match_count"] == 4
    assert result["eligible_view_count"] == 1
    assert [row["isin"] for row in result["eligible_records"]] == ["LU9999999999"]
    assert seed == original_seed
    assert result["trade_authority"] == "NONE"
    assert result["forced_fill"] is False
    assert result["production_decisions_modified"] is False
    assert result["rank_history_modified"] is False


def test_missing_seed_isin_does_not_remove_unrelated_records():
    seed = [{"isin": "LU9999999999", "rank_position": 1}]
    review = {
        "records": [
            {"isin": "LU0000000001", "ranking_eligible": False},
        ],
    }

    result = build_eligibility_view(seed, review)

    assert result["excluded_count"] == 1
    assert result["excluded_match_count"] == 0
    assert result["eligible_view_count"] == 1
