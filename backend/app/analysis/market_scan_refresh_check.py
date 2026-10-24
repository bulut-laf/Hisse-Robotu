from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SnapshotRefreshDecision:
    refresh_required: bool
    reason: str


def check_snapshot_refresh(
    *,
    snapshot_date: str | None,
    current_data_date: str | None,
) -> SnapshotRefreshDecision:
    if not snapshot_date or not current_data_date:
        return SnapshotRefreshDecision(True, "Veri tarihi eksik")

    if snapshot_date != current_data_date:
        return SnapshotRefreshDecision(True, "Yeni veri geldi")

    return SnapshotRefreshDecision(False, "Mevcut snapshot geçerli")
