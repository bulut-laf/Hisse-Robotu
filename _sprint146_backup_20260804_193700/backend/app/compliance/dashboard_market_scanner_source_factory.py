from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.app.analysis.market_scanner import (
    BistMarketScannerService,
)
from backend.app.compliance.dashboard_manual_vbts import (
    DashboardManualVbtsError,
    load_dashboard_vbts_dataset,
)
from backend.app.compliance.vbts_scan_filter import VbtsScanFilter


class DashboardMarketScannerSourceError(RuntimeError):
    """Dashboard tarama servisi seçilen VBTS kaynağıyla kurulamadığında oluşur."""


NowProvider = Callable[[], datetime]


def build_dashboard_market_scanner(
    *,
    now_provider: NowProvider | None = None,
    maximum_age: timedelta = timedelta(hours=24),
    evren_repository: Any = None,
    tarayici: Any = None,
    izleme_listesi_yolu: str | Path | None = None,
) -> BistMarketScannerService:
    """Seçili VBTS veri kaynağıyla korumalı tarama servisi oluşturur."""

    source_name = os.getenv(
        "HISSE_ROBOTU_VBTS_SOURCE",
        "",
    ).strip().lower()

    if not source_name:
        raise DashboardMarketScannerSourceError(
            "VBTS veri kaynağı ortam değişkeninde tanımlanmalıdır."
        )

    now = (
        now_provider()
        if now_provider is not None
        else datetime.now(timezone.utc)
    )

    if now.tzinfo is None:
        raise DashboardMarketScannerSourceError(
            "VBTS kontrol zamanı saat dilimi içermelidir."
        )

    if maximum_age <= timedelta(0):
        raise DashboardMarketScannerSourceError(
            "VBTS azami veri yaşı sıfırdan büyük olmalıdır."
        )

    if source_name != "manual_csv":
        raise DashboardMarketScannerSourceError(
            f"VBTS veri kaynağı desteklenmiyor: {source_name}"
        )

    try:
        dataset = load_dashboard_vbts_dataset(
            now_provider=lambda: now,
        )

        vbts_filter = VbtsScanFilter(
            dataset=dataset,
            maximum_age=maximum_age,
        )

        return BistMarketScannerService(
            evren_repository=evren_repository,
            tarayici=tarayici,
            izleme_listesi_yolu=izleme_listesi_yolu,
            vbts_scan_filter=vbts_filter,
            vbts_control_date=now.date(),
            vbts_control_time=now,
        )
    except DashboardManualVbtsError as exc:
        raise DashboardMarketScannerSourceError(str(exc)) from exc
    except Exception as exc:
        raise DashboardMarketScannerSourceError(
            f"VBTS korumalı tarama servisi hazırlanamadı: {exc}"
        ) from exc
