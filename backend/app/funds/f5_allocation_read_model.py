from __future__ import annotations

from .portfolio_tracking import fund_portfolio_snapshot_store


def _row_value(row, key, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def allocation_known_by_fund() -> dict[str, bool]:
    store = fund_portfolio_snapshot_store()
    snapshots = tuple(store.list_records())

    result: dict[str, bool] = {}

    for snap in snapshots:
        fund_id = str(_row_value(snap, "canonical_fund_id", "") or "").strip()
        if not fund_id:
            continue

        positions = _row_value(snap, "positions", ()) or ()
        quality = _row_value(snap, "data_quality_state", None)

        if hasattr(quality, "value"):
            quality_value = str(quality.value)
        else:
            quality_value = str(quality or "")

        is_known = bool(
            positions
            and quality_value.upper() == "VALID"
        )

        if is_known:
            result[fund_id] = True
        else:
            result.setdefault(fund_id, False)

    return result
