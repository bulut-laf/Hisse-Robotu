from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date
from typing import Any


class KapHttpSourceError(RuntimeError):
    """KAP HTTP kaynağı güvenli biçimde kullanılamadığında oluşur."""


HttpGet = Callable[..., Any]


class KapHttpSource:
    """KAP bildirimlerini HTTP üzerinden alıp ortak biçime dönüştürür."""

    def __init__(
        self,
        *,
        base_url: str,
        http_get: HttpGet,
        timeout_seconds: float = 10.0,
        api_key: str | None = None,
        endpoint_path: str = "notifications",
        api_key_header: str = "Authorization",
        collection_key: str = "notifications",
        api_key_prefix: str | None = None,
    ) -> None:
        normalized_base_url = base_url.strip().rstrip("/")
        normalized_endpoint_path = endpoint_path.strip().strip("/")
        normalized_api_key_header = api_key_header.strip()
        normalized_collection_key = collection_key.strip()
        normalized_api_key_prefix = (
            api_key_prefix.strip()
            if api_key_prefix is not None
            else (
                "Bearer"
                if normalized_api_key_header.lower() == "authorization"
                else ""
            )
        )

        if not normalized_base_url:
            raise ValueError("KAP temel adresi boş bırakılamaz.")

        if not normalized_endpoint_path:
            raise ValueError("KAP servis yolu boş bırakılamaz.")

        if not normalized_api_key_header:
            raise ValueError("KAP API anahtar başlığı boş bırakılamaz.")

        if not normalized_collection_key:
            raise ValueError("KAP yanıt liste anahtarı boş bırakılamaz.")

        if not callable(http_get):
            raise TypeError("HTTP GET işlevi çağrılabilir olmalıdır.")

        if timeout_seconds <= 0:
            raise ValueError("Zaman aşımı süresi sıfırdan büyük olmalıdır.")

        self._base_url = normalized_base_url
        self._http_get = http_get
        self._timeout_seconds = float(timeout_seconds)
        self._api_key = api_key.strip() if api_key else None
        self._endpoint_path = normalized_endpoint_path
        self._api_key_header = normalized_api_key_header
        self._collection_key = normalized_collection_key
        self._api_key_prefix = normalized_api_key_prefix

    def fetch_notifications(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> tuple[dict[str, object], ...]:
        if end_date < start_date:
            raise ValueError("Bitiş tarihi başlangıç tarihinden önce olamaz.")

        url = f"{self._base_url}/{self._endpoint_path}"
        params: dict[str, object] = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }
        headers = self._build_headers()

        try:
            response = self._http_get(
                url,
                params=params,
                headers=headers,
                timeout=self._timeout_seconds,
            )
        except Exception as exc:
            raise KapHttpSourceError(
                f"KAP HTTP kaynağına erişilemedi: {exc}"
            ) from exc

        status_code = getattr(response, "status_code", None)

        if status_code != 200:
            raise KapHttpSourceError(
                f"KAP HTTP kaynağı başarısız durum kodu döndürdü: "
                f"{status_code}"
            )

        try:
            payload = response.json()
        except Exception as exc:
            raise KapHttpSourceError(
                f"KAP HTTP kaynağından geçerli JSON alınamadı: {exc}"
            ) from exc

        notifications = self._extract_notifications(payload)

        return tuple(
            self._normalize_notification(notification)
            for notification in notifications
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}

        if self._api_key:
            value = self._api_key
            if self._api_key_prefix:
                value = f"{self._api_key_prefix} {self._api_key}"
            headers[self._api_key_header] = value

        return headers

    def _extract_notifications(
        self,
        payload: object,
    ) -> tuple[Mapping[str, Any], ...]:
        if not isinstance(payload, Mapping):
            raise KapHttpSourceError(
                "KAP HTTP yanıt şeması geçersiz."
            )

        raw_notifications = payload.get(self._collection_key)

        if not isinstance(raw_notifications, list):
            raise KapHttpSourceError(
                "KAP HTTP yanıt şeması beklenen bildirim listesini içermiyor."
            )

        normalized: list[Mapping[str, Any]] = []

        for item in raw_notifications:
            if not isinstance(item, Mapping):
                raise KapHttpSourceError(
                    "KAP HTTP yanıt şeması geçersiz bildirim kaydı içeriyor."
                )

            normalized.append(item)

        return tuple(normalized)

    @staticmethod
    def _normalize_notification(
        notification: Mapping[str, Any],
    ) -> dict[str, object]:
        notification_id = str(notification.get("id", "")).strip()
        title = str(notification.get("title", "")).strip()
        body = str(notification.get("body", "")).strip()
        published_at = str(
            notification.get("publishedAt", "")
        ).strip()

        if not notification_id:
            raise KapHttpSourceError(
                "KAP bildirim kaydında kimlik bilgisi bulunamadı."
            )

        if not title:
            raise KapHttpSourceError(
                "KAP bildirim kaydında başlık bulunamadı."
            )

        if not body:
            raise KapHttpSourceError(
                "KAP bildirim kaydında metin bulunamadı."
            )

        if not published_at:
            raise KapHttpSourceError(
                "KAP bildirim kaydında yayın zamanı bulunamadı."
            )

        return {
            "notification_id": notification_id,
            "title": title,
            "body": body,
            "published_at": published_at,
            "is_verified": True,
        }
