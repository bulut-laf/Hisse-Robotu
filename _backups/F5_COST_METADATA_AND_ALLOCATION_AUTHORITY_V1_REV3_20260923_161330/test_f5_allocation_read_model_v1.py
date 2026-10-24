from datetime import date, datetime, timezone
from decimal import Decimal

from backend.app.funds.contracts import DataQualityState
from backend.app.funds.portfolio_tracking import (
    FundPortfolioPosition,
    FundPortfolioSnapshot,
    FundPortfolioSnapshotJsonStore,
)
from backend.app.funds import f5_allocation_read_model

def test_allocation_known_requires_valid_positions(tmp_path, monkeypatch):
    store = FundPortfolioSnapshotJsonStore(tmp_path / "portfolio.json")
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
    store.upsert((snap,))
    monkeypatch.setattr(
        f5_allocation_read_model,
        "fund_portfolio_snapshot_store",
        lambda: store,
    )
    result = f5_allocation_read_model.allocation_known_by_fund()
    assert result["fund:tefas:PHE"] is True
