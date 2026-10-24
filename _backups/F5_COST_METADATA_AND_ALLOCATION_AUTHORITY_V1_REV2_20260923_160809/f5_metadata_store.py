from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Iterable

from .contracts import DataQualityState, FundCostAndMetadata
from .kap_fund_cost import fetch_latest_kap_fund_cost_metrics

DEFAULT_F5_METADATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "funds"
    / "f5_cost_metadata.json"
)

class FundCostMetadataStoreError(RuntimeError):
    pass

class FundCostMetadataJsonStore:
    def __init__(self, path: str | Path = DEFAULT_F5_METADATA_PATH) -> None:
        self.path = Path(path)

    def list_records(self) -> tuple[FundCostAndMetadata, ...]:
        if not self.path.exists():
            return ()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise FundCostMetadataStoreError("F5_COST_METADATA_STORE_NOT_LIST")
        out = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            out.append(FundCostAndMetadata(
                canonical_fund_id=str(row["canonical_fund_id"]),
                management_fee=Decimal(str(row["management_fee"])) if row.get("management_fee") is not None else None,
                total_expense_ratio=Decimal(str(row["total_expense_ratio"])) if row.get("total_expense_ratio") is not None else None,
                risk_value=row.get("risk_value"),
                benchmark=row.get("benchmark"),
                inception_date=None,
                settlement_terms=row.get("settlement_terms"),
                minimum_transaction_amount=Decimal(str(row["minimum_transaction_amount"])) if row.get("minimum_transaction_amount") is not None else None,
                umbrella_fund=row.get("umbrella_fund"),
                founder=row.get("founder"),
                manager=row.get("manager"),
                tax_metadata=row.get("tax_metadata"),
                provider=str(row["provider"]),
                source_as_of=datetime.fromisoformat(str(row["source_as_of"])),
                fetched_at=datetime.fromisoformat(str(row["fetched_at"])),
                data_quality_state=DataQualityState(str(row["data_quality_state"])),
            ))
        return tuple(out)

    def upsert(self, records: Iterable[FundCostAndMetadata]) -> None:
        current = {r.canonical_fund_id: r for r in self.list_records()}
        for record in records:
            current[record.canonical_fund_id] = record

        serial = []
        for record in current.values():
            serial.append({
                "canonical_fund_id": record.canonical_fund_id,
                "management_fee": str(record.management_fee) if record.management_fee is not None else None,
                "total_expense_ratio": str(record.total_expense_ratio) if record.total_expense_ratio is not None else None,
                "risk_value": record.risk_value,
                "benchmark": record.benchmark,
                "settlement_terms": record.settlement_terms,
                "minimum_transaction_amount": str(record.minimum_transaction_amount) if record.minimum_transaction_amount is not None else None,
                "umbrella_fund": record.umbrella_fund,
                "founder": record.founder,
                "manager": record.manager,
                "tax_metadata": record.tax_metadata,
                "provider": record.provider,
                "source_as_of": record.source_as_of.isoformat(),
                "fetched_at": record.fetched_at.isoformat(),
                "data_quality_state": record.data_quality_state.value,
            })

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(serial, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

def fund_cost_metadata_store(path: str | Path | None = None) -> FundCostMetadataJsonStore:
    return FundCostMetadataJsonStore(path or DEFAULT_F5_METADATA_PATH)

def fetch_and_persist_kap_cost_metadata(
    fund_code: str,
    *,
    canonical_fund_id: str,
    store: FundCostMetadataJsonStore | None = None,
    timeout_seconds: int = 30,
) -> FundCostAndMetadata:
    metrics = fetch_latest_kap_fund_cost_metrics(fund_code, timeout_seconds=timeout_seconds)
    if metrics.current_period_realized_expense_ratio is None:
        raise FundCostMetadataStoreError("KAP_COST_CURRENT_REALIZED_EXPENSE_RATIO_UNAVAILABLE")
    now = datetime.now(timezone.utc)
    record = FundCostAndMetadata(
        canonical_fund_id=canonical_fund_id,
        management_fee=None,
        total_expense_ratio=metrics.current_period_realized_expense_ratio,
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
    (store or fund_cost_metadata_store()).upsert((record,))
    return record

def latest_cost_metadata_by_fund(
    store: FundCostMetadataJsonStore | None = None,
) -> dict[str, FundCostAndMetadata]:
    rows = (store or fund_cost_metadata_store()).list_records()
    return {row.canonical_fund_id: row for row in rows}
