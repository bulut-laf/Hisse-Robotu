from __future__ import annotations

from datetime import date, datetime

from backend.app.compliance.kap_http_source import (
    KapHttpSource,
    KapHttpSourceError,
)
from backend.app.compliance.kap_vbts_client import (
    KapVbtsClient,
    KapVbtsError,
)
from backend.app.compliance.vbts_dataset import VbtsDataset


class KapVbtsServiceError(RuntimeError):
    """KAP/VBTS veri paketi güvenli biçimde oluşturulamadığında oluşur."""


class KapVbtsService:
    """HTTP kaynağını KAP/VBTS ayrıştırıcısı ile birleştirir."""

    def __init__(self, *, http_source: KapHttpSource) -> None:
        self._http_source = http_source

    def fetch_dataset(
        self,
        *,
        start_date: date,
        end_date: date,
        fetched_at: datetime,
    ) -> VbtsDataset:
        def bildirimleri_getir(
            baslangic: date,
            bitis: date,
        ) -> tuple[dict[str, object], ...]:
            return self._http_source.fetch_notifications(
                start_date=baslangic,
                end_date=bitis,
            )

        client = KapVbtsClient(
            bildirimleri_getir=bildirimleri_getir,
        )

        try:
            return client.fetch_dataset(
                start_date=start_date,
                end_date=end_date,
                fetched_at=fetched_at,
            )
        except (KapHttpSourceError, KapVbtsError, ValueError, TypeError) as exc:
            raise KapVbtsServiceError(
                f"KAP/VBTS veri paketi oluşturulamadı: {exc}"
            ) from exc