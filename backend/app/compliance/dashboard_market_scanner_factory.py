from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.app.analysis.market_scanner import (
    BistMarketScannerService,
)
from backend.app.compliance.kap_vbts_service import KapVbtsService
from backend.app.compliance.vbts_scan_filter import VbtsScanFilter


class DashboardMarketScannerFactoryError(RuntimeError):
    """KAP/VBTS korumalı dashboard taraması hazırlanamadığında oluşur."""


NowProvider = Callable[[], datetime]


def build_protected_market_scanner(
    *,
    kap_vbts_service: KapVbtsService,
    now_provider: NowProvider | None = None,
    lookback_days: int = 30,
    maximum_age: timedelta = timedelta(hours=6),
    evren_repository: Any = None,
    tarayici: Any = None,
    izleme_listesi_yolu: str | Path | None = None,
) -> BistMarketScannerService:
    """Güncel KAP/VBTS paketiyle korumalı toplu tarama servisi oluşturur."""

    if lookback_days <= 0:
        raise ValueError("KAP/VBTS geçmiş gün sayısı pozitif olmalıdır.")

    if maximum_age <= timedelta(0):
        raise ValueError("VBTS azami veri yaşı pozitif olmalıdır.")

    simdi = (
        now_provider()
        if now_provider is not None
        else datetime.now(timezone.utc)
    )

    if simdi.tzinfo is None:
        raise ValueError("VBTS kontrol zamanı saat dilimi içermelidir.")

    kontrol_tarihi = simdi.date()
    baslangic_tarihi = kontrol_tarihi - timedelta(days=lookback_days)

    try:
        dataset = kap_vbts_service.fetch_dataset(
            start_date=baslangic_tarihi,
            end_date=kontrol_tarihi,
            fetched_at=simdi,
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
            vbts_control_date=kontrol_tarihi,
            vbts_control_time=simdi,
        )

    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise

        raise DashboardMarketScannerFactoryError(
            f"KAP/VBTS korumalı tarama hazırlanamadı: {exc}"
        ) from exc
