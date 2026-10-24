from __future__ import annotations

from datetime import date
from typing import Any

import pytest


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: Any = None,
        json_error: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self) -> Any:
        if self._json_error is not None:
            raise self._json_error
        return self._payload


def test_kap_http_kaynagi_bildirimleri_normalize_eder() -> None:
    from backend.app.compliance.kap_http_source import KapHttpSource

    cagrilar: list[dict[str, object]] = []

    def fake_get(
        url: str,
        *,
        params: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        cagrilar.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout,
            }
        )

        return FakeResponse(
            payload={
                "notifications": [
                    {
                        "id": 1629762,
                        "title": (
                            "Pay Piyasasında Volatilite Bazlı "
                            "Tedbir Sistemi"
                        ),
                        "body": (
                            "VBTS kapsamında BORLS.E paylarında "
                            "09/07/2026 tarihli işlemlerden "
                            "07/08/2026 tarihli işlemlere kadar "
                            "brüt takas uygulanacaktır."
                        ),
                        "publishedAt": "2026-07-08T15:30:00+03:00",
                    }
                ]
            }
        )

    kaynak = KapHttpSource(
        base_url="https://ornek.kap.test/api",
        http_get=fake_get,
        timeout_seconds=8.0,
        api_key="test-anahtari",
    )

    bildirimler = kaynak.fetch_notifications(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 28),
    )

    assert bildirimler == (
        {
            "notification_id": "1629762",
            "title": (
                "Pay Piyasasında Volatilite Bazlı Tedbir Sistemi"
            ),
            "body": (
                "VBTS kapsamında BORLS.E paylarında "
                "09/07/2026 tarihli işlemlerden "
                "07/08/2026 tarihli işlemlere kadar "
                "brüt takas uygulanacaktır."
            ),
            "published_at": "2026-07-08T15:30:00+03:00",
            "is_verified": True,
        },
    )

    assert cagrilar == [
        {
            "url": "https://ornek.kap.test/api/notifications",
            "params": {
                "startDate": "2026-07-01",
                "endDate": "2026-07-28",
            },
            "headers": {
                "Accept": "application/json",
                "Authorization": "Bearer test-anahtari",
            },
            "timeout": 8.0,
        }
    ]


def test_kap_http_kaynagi_basarisiz_durum_kodunu_reddeder() -> None:
    from backend.app.compliance.kap_http_source import (
        KapHttpSource,
        KapHttpSourceError,
    )

    def fake_get(
        _url: str,
        *,
        params: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(status_code=503, payload={})

    kaynak = KapHttpSource(
        base_url="https://ornek.kap.test/api",
        http_get=fake_get,
    )

    with pytest.raises(KapHttpSourceError, match="503"):
        kaynak.fetch_notifications(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 28),
        )


def test_kap_http_kaynagi_gecersiz_json_yanitini_reddeder() -> None:
    from backend.app.compliance.kap_http_source import (
        KapHttpSource,
        KapHttpSourceError,
    )

    def fake_get(
        _url: str,
        *,
        params: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(
            json_error=ValueError("Geçersiz JSON"),
        )

    kaynak = KapHttpSource(
        base_url="https://ornek.kap.test/api",
        http_get=fake_get,
    )

    with pytest.raises(KapHttpSourceError, match="JSON"):
        kaynak.fetch_notifications(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 28),
        )


def test_kap_http_kaynagi_beklenmeyen_sema_yanitini_reddeder() -> None:
    from backend.app.compliance.kap_http_source import (
        KapHttpSource,
        KapHttpSourceError,
    )

    def fake_get(
        _url: str,
        *,
        params: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(
            payload={"unexpected": []},
        )

    kaynak = KapHttpSource(
        base_url="https://ornek.kap.test/api",
        http_get=fake_get,
    )

    with pytest.raises(KapHttpSourceError, match="şema"):
        kaynak.fetch_notifications(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 28),
        )


def test_kap_http_kaynagi_baglanti_hatasini_guvenli_hataya_cevirir() -> None:
    from backend.app.compliance.kap_http_source import (
        KapHttpSource,
        KapHttpSourceError,
    )

    def fake_get(
        _url: str,
        *,
        params: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        raise TimeoutError("Bağlantı zaman aşımına uğradı.")

    kaynak = KapHttpSource(
        base_url="https://ornek.kap.test/api",
        http_get=fake_get,
    )

    with pytest.raises(KapHttpSourceError, match="erişilemedi"):
        kaynak.fetch_notifications(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 28),
        )