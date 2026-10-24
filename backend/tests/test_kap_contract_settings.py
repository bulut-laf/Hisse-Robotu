from __future__ import annotations

from datetime import date
from typing import Any

import pytest


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.status_code = 200
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def test_kap_http_source_endpoint_header_ve_liste_anahtarini_ayardan_alir() -> None:
    from backend.app.compliance.kap_http_source import KapHttpSource

    calls: list[dict[str, object]] = []

    def fake_get(
        url: str,
        *,
        params: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        calls.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return FakeResponse(
            {
                "disclosures": [
                    {
                        "id": 1,
                        "title": "VBTS",
                        "body": "AAA.E payında brüt takas uygulanacaktır.",
                        "publishedAt": "2026-07-29T10:00:00+03:00",
                    }
                ]
            }
        )

    source = KapHttpSource(
        base_url="https://ornek.kap.test/api",
        http_get=fake_get,
        api_key="gizli",
        endpoint_path="disclosures",
        api_key_header="X-API-KEY",
        collection_key="disclosures",
    )

    records = source.fetch_notifications(
        start_date=date(2026, 7, 28),
        end_date=date(2026, 7, 29),
    )

    assert len(records) == 1
    assert calls[0]["url"] == "https://ornek.kap.test/api/disclosures"
    assert calls[0]["headers"] == {
        "Accept": "application/json",
        "X-API-KEY": "gizli",
    }


def test_kap_settings_abonelik_sozlesmesi_degerlerini_ortamdan_okur(
    monkeypatch,
) -> None:
    from backend.app.compliance.kap_settings import KapSettings

    monkeypatch.setenv("HISSE_ROBOTU_KAP_BASE_URL", "https://kap.test/api")
    monkeypatch.setenv("HISSE_ROBOTU_KAP_API_KEY", "anahtar")
    monkeypatch.setenv("HISSE_ROBOTU_KAP_ENDPOINT_PATH", "disclosures")
    monkeypatch.setenv("HISSE_ROBOTU_KAP_API_KEY_HEADER", "X-API-KEY")
    monkeypatch.setenv("HISSE_ROBOTU_KAP_COLLECTION_KEY", "disclosures")

    settings = KapSettings.from_environment()

    assert settings.endpoint_path == "disclosures"
    assert settings.api_key_header == "X-API-KEY"
    assert settings.collection_key == "disclosures"


def test_kap_settings_sozlesme_ayarlari_eksikse_guvenli_durur(
    monkeypatch,
) -> None:
    from backend.app.compliance.kap_settings import KapSettings

    monkeypatch.setenv("HISSE_ROBOTU_KAP_BASE_URL", "https://kap.test/api")
    monkeypatch.setenv("HISSE_ROBOTU_KAP_API_KEY", "anahtar")
    monkeypatch.delenv("HISSE_ROBOTU_KAP_ENDPOINT_PATH", raising=False)
    monkeypatch.delenv("HISSE_ROBOTU_KAP_API_KEY_HEADER", raising=False)
    monkeypatch.delenv("HISSE_ROBOTU_KAP_COLLECTION_KEY", raising=False)

    with pytest.raises(
        ValueError,
        match="KAP abonelik sözleşmesi ayarları",
    ):
        KapSettings.from_environment()
