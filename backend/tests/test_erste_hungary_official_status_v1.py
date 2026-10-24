import json

import pytest

from backend.app.funds.erste_hungary_official_status import (
    load_erste_hungary_official_status,
)


def test_official_status_loads_four_ineligible_funds(tmp_path):
    payload = {
        "records": [
            {
                "isin": "LU0011850392",
                "status": "STALE_NAV_DORMANT_SHARE",
                "last_nav_date": "2022-02-28",
                "ranking_eligible": False,
                "source": "https://example.com/fund",
            }
        ],
        "trade_authority": "NONE",
        "forced_fill": False,
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = load_erste_hungary_official_status(path)

    assert result["LU0011850392"]["ranking_eligible"] is False
    assert result["LU0011850392"]["status"] == "STALE_NAV_DORMANT_SHARE"
    assert result["LU0011850392"]["last_nav_date"] == "2022-02-28"
    assert result["LU0011850392"]["source"] == "https://example.com/fund"


def test_duplicate_isin_is_rejected(tmp_path):
    payload = {
        "records": [
            {"isin": "LU0011850392", "ranking_eligible": False},
            {"isin": "lu0011850392", "ranking_eligible": False},
        ],
        "trade_authority": "NONE",
        "forced_fill": False,
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="DUPLICATE_OFFICIAL_STATUS_ISIN"):
        load_erste_hungary_official_status(path)


def test_trade_authority_violation_is_rejected(tmp_path):
    payload = {
        "records": [],
        "trade_authority": "BUY",
        "forced_fill": False,
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="TRADE_AUTHORITY_NOT_NONE"):
        load_erste_hungary_official_status(path)
