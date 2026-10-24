from __future__ import annotations

from .contracts import DataQualityState
from .portfolio_tracking import fund_portfolio_snapshot_store

def allocation_known_by_fund() -> dict[str, bool]:
    store = fund_portfolio_snapshot_store()
    snapshots = tuple(store.list_records())
    result: dict[str, bool] = {}
    for snap in snapshots:
        fund_id = getattr(snap, "canonical_fund_id", None)
        if not fund_id:
            continue
        positions = tuple(getattr(snap, "positions", ()) or ())
        quality = getattr(snap, "data_quality_state", None)
        is_known = bool(positions and quality == DataQualityState.VALID)
        if is_known:
            result[str(fund_id)] = True
        else:
            result.setdefault(str(fund_id), False)
    return result
