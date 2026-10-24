from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from datetime import date, datetime
from typing import Any

from backend.app.compliance.vbts_dataset import VbtsDataset
from backend.app.compliance.vbts_models import VbtsMeasure
from backend.app.compliance.vbts_source_status import VbtsSourceStatus


class KapVbtsError(RuntimeError):
    """KAP/VBTS istemcisinin ortak hata türü."""


class KapVbtsSourceError(KapVbtsError):
    """KAP bildirim kaynağına erişilemediğinde oluşur."""


class KapVbtsParseError(KapVbtsError):
    """Bir VBTS bildirimi güvenli biçimde ayrıştırılamadığında oluşur."""


NotificationFetcher = Callable[[date, date], Iterable[Mapping[str, Any]]]


class KapVbtsClient:
    """KAP VBTS bildirimlerini güvenli veri paketine dönüştürür."""

    _SYMBOL_PATTERN = re.compile(r"\b([A-Z0-9]{2,12})\.E\b", re.IGNORECASE)
    _DATE_PATTERN = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")

    _MEASURE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
        (
            "BRUT_TAKAS",
            re.compile(r"\bbrüt\s+takas\b", re.IGNORECASE),
        ),
        (
            "EMIR_PAKETI",
            re.compile(r"\bemir\s+paketi\s+tedbiri\b", re.IGNORECASE),
        ),
        (
            "ACIGA_SATIS_YASAGI",
            re.compile(
                r"\baçığa\s+satış(?:\s+ve\s+kredili\s+işlem)?\s+yasağı\b",
                re.IGNORECASE,
            ),
        ),
        (
            "KREDILI_ISLEM_YASAGI",
            re.compile(r"\bkredili\s+işlem\s+yasağı\b", re.IGNORECASE),
        ),
        (
            "TEK_FIYAT",
            re.compile(r"\btek\s+fiyat\s+işlem\s+yöntemi\b", re.IGNORECASE),
        ),
        (
            "INTERNET_EMIR_KISITI",
            re.compile(
                r"\binternet(?:ten)?\s+emir\s+iletim(?:i|inin)\s+kısıtlan",
                re.IGNORECASE,
            ),
        ),
    )

    def __init__(self, bildirimleri_getir: NotificationFetcher) -> None:
        if not callable(bildirimleri_getir):
            raise TypeError("Bildirim kaynağı çağrılabilir olmalıdır.")

        self._bildirimleri_getir = bildirimleri_getir

    def fetch_dataset(
        self,
        *,
        start_date: date,
        end_date: date,
        fetched_at: datetime,
    ) -> VbtsDataset:
        if end_date < start_date:
            raise ValueError("Bitiş tarihi başlangıç tarihinden önce olamaz.")

        if fetched_at.tzinfo is None:
            raise ValueError("Veri alma zamanı saat dilimi içermelidir.")

        try:
            notifications = tuple(
                self._bildirimleri_getir(start_date, end_date)
            )
        except Exception as exc:
            raise KapVbtsSourceError(
                f"KAP/VBTS bildirim kaynağına erişilemedi: {exc}"
            ) from exc

        measures: list[VbtsMeasure] = []

        for notification in notifications:
            measures.extend(self._parse_notification(notification))

        ordered_measures = tuple(
            sorted(
                measures,
                key=lambda item: (
                    item.symbol,
                    item.measure_type,
                    item.start_date,
                    item.end_date,
                    item.source_reference,
                ),
            )
        )

        status = VbtsSourceStatus(
            source="KAP",
            fetched_at=fetched_at,
            is_verified=self._all_notifications_verified(notifications),
            record_count=len(ordered_measures),
        )

        return VbtsDataset(
            measures=ordered_measures,
            status=status,
        )

    def _parse_notification(
        self,
        notification: Mapping[str, Any],
    ) -> tuple[VbtsMeasure, ...]:
        title = str(notification.get("title", "")).strip()
        body = str(notification.get("body", "")).strip()
        reference = str(notification.get("notification_id", "")).strip()

        combined_text = f"{title}\n{body}".strip()

        if not self._looks_like_vbts(combined_text):
            return ()

        measure_type = self._detect_measure_type(combined_text)

        if measure_type is None:
            return ()

        symbols = tuple(
            dict.fromkeys(
                match.group(1).upper()
                for match in self._SYMBOL_PATTERN.finditer(combined_text)
            )
        )

        if not symbols:
            raise KapVbtsParseError(
                f"VBTS bildiriminde sembol bulunamadı: {reference or 'referans yok'}"
            )

        date_values = [
            self._parse_date(match.group(1), reference)
            for match in self._DATE_PATTERN.finditer(combined_text)
        ]

        if len(date_values) < 2:
            raise KapVbtsParseError(
                f"VBTS bildiriminde başlangıç ve bitiş tarihleri bulunamadı: "
                f"{reference or 'referans yok'}"
            )

        start_date = date_values[0]
        end_date = date_values[1]

        if not reference:
            raise KapVbtsParseError(
                "VBTS bildiriminin kaynak referansı bulunamadı."
            )

        return tuple(
            VbtsMeasure(
                symbol=symbol,
                measure_type=measure_type,
                start_date=start_date,
                end_date=end_date,
                source="KAP",
                source_reference=reference,
            )
            for symbol in symbols
        )

    @classmethod
    def _looks_like_vbts(cls, text: str) -> bool:
        normalized = text.casefold()
        return (
            "volatilite bazlı tedbir sistemi" in normalized
            or "vbts kapsamında" in normalized
        )

    @classmethod
    def _detect_measure_type(cls, text: str) -> str | None:
        for measure_type, pattern in cls._MEASURE_PATTERNS:
            if pattern.search(text):
                return measure_type

        return None

    @staticmethod
    def _parse_date(value: str, reference: str) -> date:
        try:
            return datetime.strptime(value, "%d/%m/%Y").date()
        except ValueError as exc:
            raise KapVbtsParseError(
                f"VBTS bildirim tarihi ayrıştırılamadı ({value}): "
                f"{reference or 'referans yok'}"
            ) from exc

    @staticmethod
    def _all_notifications_verified(
        notifications: tuple[Mapping[str, Any], ...],
    ) -> bool:
        return all(
            bool(notification.get("is_verified", False))
            for notification in notifications
        )