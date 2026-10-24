from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.compliance.manual_vbts_csv import (
    ManualVbtsCsvError,
    load_official_vbts_csv,
)
from backend.app.compliance.vbts_dataset import VbtsDataset


class DashboardManualVbtsError(RuntimeError):
    """Dashboard için manuel VBTS veri seti hazırlanamadığında oluşur."""


NowProvider = Callable[[], datetime]


def load_dashboard_vbts_dataset(
    *,
    now_provider: NowProvider | None = None,
) -> VbtsDataset:
    """Ortam ayarlarından manuel resmî VBTS CSV veri setini yükler."""

    csv_path_raw = os.getenv(
        "HISSE_ROBOTU_VBTS_CSV_PATH",
        "",
    ).strip()

    if not csv_path_raw:
        raise DashboardManualVbtsError(
            "VBTS CSV yolu ortam değişkeninde tanımlanmalıdır."
        )

    maximum_age_raw = os.getenv(
        "HISSE_ROBOTU_VBTS_CSV_MAX_AGE_HOURS",
        "24",
    ).strip()

    try:
        maximum_age_hours = float(maximum_age_raw)
    except (TypeError, ValueError) as exc:
        raise DashboardManualVbtsError(
            "VBTS CSV azami yaşı sayısal olmalıdır."
        ) from exc

    if maximum_age_hours <= 0:
        raise DashboardManualVbtsError(
            "VBTS CSV azami yaşı sıfırdan büyük olmalıdır."
        )

    now = (
        now_provider()
        if now_provider is not None
        else datetime.now(timezone.utc)
    )

    if now.tzinfo is None:
        raise DashboardManualVbtsError(
            "VBTS kontrol zamanı saat dilimi içermelidir."
        )

    try:
        return load_official_vbts_csv(
            Path(csv_path_raw),
            fetched_at=now,
            maximum_file_age=timedelta(
                hours=maximum_age_hours,
            ),
            now_provider=lambda: now,
        )
    except ManualVbtsCsvError as exc:
        raise DashboardManualVbtsError(str(exc)) from exc
