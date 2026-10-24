from datetime import datetime, timezone
from decimal import Decimal

from backend.app.funds.contracts import DataQualityState, FundCostAndMetadata
from backend.app.funds.f5_metadata_store import FundCostMetadataJsonStore

def test_f5_cost_metadata_roundtrip(tmp_path):
    store = FundCostMetadataJsonStore(tmp_path / "f5.json")
    now = datetime.now(timezone.utc)
    record = FundCostAndMetadata(
        canonical_fund_id="fund:tefas:PHE",
        management_fee=None,
        total_expense_ratio=Decimal("0.014"),
        risk_value=None,
        benchmark=None,
        inception_date=None,
        settlement_terms=None,
        minimum_transaction_amount=None,
        umbrella_fund=None,
        founder=None,
        manager=None,
        tax_metadata=None,
        provider="KAP",
        source_as_of=now,
        fetched_at=now,
        data_quality_state=DataQualityState.VALID,
    )
    store.upsert((record,))
    rows = store.list_records()
    assert len(rows) == 1
    assert rows[0].total_expense_ratio == Decimal("0.014")
