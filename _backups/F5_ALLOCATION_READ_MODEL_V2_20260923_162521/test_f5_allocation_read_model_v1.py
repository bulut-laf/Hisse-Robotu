from datetime import date, datetime, timezone
from decimal import Decimal

from backend.app.funds.contracts import DataQualityState
from backend.app.funds.portfolio_tracking import FundPortfolioPosition, FundPortfolioSnapshot
from backend.app.funds import f5_allocation_read_model


class _FakeSnapshotStore:
    def __init__(self, records):
        self._records = tuple(records)

    def list_records(self):
        return self._records


def test_allocation_known_requires_valid_positions(monkeypatch):
    snap = FundPortfolioSnapshot(
        canonical_fund_id="fund:tefas:PHE",
        portfolio_date=date(2026, 7, 31),
        publication_date=date(2026, 8, 5),
        ingested_at=datetime.now(timezone.utc),
        provider="KAP",
        positions=(
            FundPortfolioPosition(
                canonical_fund_id="fund:tefas:PHE",
                portfolio_date=date(2026, 7, 31),
                symbol="AKSEN",
                asset_type="EQUITY",
                market_value=Decimal("1"),
                portfolio_weight=Decimal("0.01"),
            ),
        ),
        data_quality_state=DataQualityState.VALID,
    )
    fake = _FakeSnapshotStore((snap,))
    monkeypatch.setattr(
        f5_allocation_read_model,
        "fund_portfolio_snapshot_store",
        lambda: fake,
    )
    result = f5_allocation_read_model.allocation_known_by_fund()
    assert result["fund:tefas:PHE"] is True
