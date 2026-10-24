from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: Any = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def test_kap_vbts_service_http_bildirimini_dataset_paketine_donusturur() -> None:
    from backend.app.compliance.kap_http_source import KapHttpSource
    from backend.app.compliance.kap_vbts_service import KapVbtsService

    def fake_get(
        _url: str,
        *,
        params: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        assert params == {
            "startDate": "2026-07-01",
            "endDate": "2026-07-28",
        }
        assert headers == {"Accept": "application/json"}
        assert timeout == 10.0

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

    service = KapVbtsService(
        http_source=KapHttpSource(
            base_url="https://ornek.kap.test/api",
            http_get=fake_get,
        )
    )

    dataset = service.fetch_dataset(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 28),
        fetched_at=datetime(
            2026,
            7,
            28,
            18,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert dataset.status.source == "KAP"
    assert dataset.status.is_verified is True
    assert dataset.status.record_count == 1
    assert len(dataset.measures) == 1

    measure = dataset.measures[0]
    assert measure.symbol == "BORLS.IS"
    assert measure.measure_type == "BRUT_TAKAS"
    assert measure.start_date == date(2026, 7, 9)
    assert measure.end_date == date(2026, 8, 7)


def test_kap_vbts_service_http_kaynak_hatasini_guvenli_hataya_cevirir() -> None:
    from backend.app.compliance.kap_http_source import KapHttpSource
    from backend.app.compliance.kap_vbts_service import (
        KapVbtsService,
        KapVbtsServiceError,
    )

    def fake_get(
        _url: str,
        *,
        params: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(
            status_code=503,
            payload={},
        )

    service = KapVbtsService(
        http_source=KapHttpSource(
            base_url="https://ornek.kap.test/api",
            http_get=fake_get,
        )
    )

    try:
        service.fetch_dataset(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 28),
            fetched_at=datetime(
                2026,
                7,
                28,
                18,
                0,
                tzinfo=timezone.utc,
            ),
        )
    except KapVbtsServiceError as exc:
        assert "KAP/VBTS veri paketi oluşturulamadı" in str(exc)
    else:
        raise AssertionError("KapVbtsServiceError bekleniyordu.")


def test_kap_vbts_service_bos_bildirim_listesini_dogrulanmis_paket_yapar() -> None:
    from backend.app.compliance.kap_http_source import KapHttpSource
    from backend.app.compliance.kap_vbts_service import KapVbtsService

    def fake_get(
        _url: str,
        *,
        params: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(
            payload={"notifications": []},
        )

    service = KapVbtsService(
        http_source=KapHttpSource(
            base_url="https://ornek.kap.test/api",
            http_get=fake_get,
        )
    )

    dataset = service.fetch_dataset(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 28),
        fetched_at=datetime(
            2026,
            7,
            28,
            18,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert dataset.measures == ()
    assert dataset.status.record_count == 0
    assert dataset.status.is_verified is True