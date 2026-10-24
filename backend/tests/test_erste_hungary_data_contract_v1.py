from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from backend.app.funds.international.contract import (
    canonical_isin_fund_id,
    normalize_isin,
)
from backend.app.funds.international.erste_hungary_adapter import (
    normalize_erste_hungary_row,
)


def test_canonical_isin_identity_is_provider_independent():
    assert canonical_isin_fund_id("hu0000704200") == "fund:isin:HU0000704200"


def test_invalid_isin_is_rejected():
    with pytest.raises(ValueError, match="INVALID_ISIN"):
        normalize_isin("HU123")


def test_erste_hungary_row_normalizes_localized_values():
    snapshot = normalize_erste_hungary_row(
        {
            "isin": "HU0000704200",
            "name": "Sample Erste Hungary Fund",
            "fund_manager": "Sample Manager",
            "category": "RГ©szvГ©nyalap",
            "currency": "huf",
            "risk": "5",
            "nav": "1.234,56",
            "nav_date": "2026.09.22.",
            "return_1m": "1,25%",
            "return_3m": "3,50%",
            "return_6m": "7,00%",
            "return_1y": "11,00%",
            "volatility_1y": "12,50%",
            "max_drawdown_1y": "-8,20%",
            "total_expense_ratio": "1,80%",
            "settlement": "T+2",
            "erste_access_status": "AVAILABLE",
            "source_url": "https://example.invalid/fund/HU0000704200",
            "source_date": "22.09.2026",
        },
        fetched_at=datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc),
    )

    assert snapshot.canonical_fund_id == "fund:isin:HU0000704200"
    assert snapshot.market == "HU"
    assert snapshot.distribution == "ERSTE_HUNGARY"
    assert snapshot.instrument_type == "FUND"
    assert snapshot.currency == "HUF"
    assert snapshot.nav == Decimal("1234.56")
    assert snapshot.nav_date.isoformat() == "2026-09-22"
    assert snapshot.return_1m == Decimal("0.0125")
    assert snapshot.return_3m == Decimal("0.035")
    assert snapshot.return_6m == Decimal("0.07")
    assert snapshot.return_1y == Decimal("0.11")
    assert snapshot.volatility_1y == Decimal("0.125")
    assert snapshot.max_drawdown_1y == Decimal("-0.082")
    assert snapshot.total_expense_ratio == Decimal("0.018")
    assert snapshot.settlement == "T+2"
    assert snapshot.erste_access_status == "AVAILABLE"


def test_name_and_source_are_required():
    base = {
        "isin": "HU0000704200",
        "source_url": "https://example.invalid/fund/HU0000704200",
    }

    with pytest.raises(ValueError, match="FUND_NAME_MISSING"):
        normalize_erste_hungary_row(base)

    with pytest.raises(ValueError, match="SOURCE_URL_MISSING"):
        normalize_erste_hungary_row(
            {"isin": "HU0000704200", "name": "Sample Fund"}
        )
