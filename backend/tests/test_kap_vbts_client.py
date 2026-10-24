from __future__ import annotations

from datetime import date, datetime, timezone

import pytest


def _bildirim(
    *,
    bildirim_id: str,
    baslik: str,
    metin: str,
) -> dict[str, object]:
    return {
        "notification_id": bildirim_id,
        "title": baslik,
        "published_at": datetime(
            2026,
            7,
            28,
            15,
            0,
            tzinfo=timezone.utc,
        ),
        "body": metin,
        "is_verified": True,
    }


def test_kap_vbts_istemcisi_brut_takas_bildirimini_ayristirir() -> None:
    from backend.app.compliance.kap_vbts_client import KapVbtsClient

    kayitlar = [
        _bildirim(
            bildirim_id="1629762",
            baslik="Pay Piyasasında Volatilite Bazlı Tedbir Sistemi",
            metin=(
                "Volatilite Bazlı Tedbir Sistemi (VBTS) kapsamında "
                "BORLS.E paylarında 09/07/2026 tarihli işlemlerden "
                "(seans başından) 07/08/2026 tarihli işlemlere "
                "(seans sonuna) kadar brüt takas uygulanacaktır."
            ),
        )
    ]

    istemci = KapVbtsClient(
        bildirimleri_getir=lambda _baslangic, _bitis: kayitlar,
    )

    dataset = istemci.fetch_dataset(
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

    tedbir = dataset.measures[0]
    assert tedbir.symbol == "BORLS.IS"
    assert tedbir.measure_type == "BRUT_TAKAS"
    assert tedbir.start_date == date(2026, 7, 9)
    assert tedbir.end_date == date(2026, 8, 7)
    assert tedbir.source_reference == "1629762"


def test_kap_vbts_istemcisi_birden_fazla_sembolu_ve_emir_paketini_ayristirir() -> None:
    from backend.app.compliance.kap_vbts_client import KapVbtsClient

    kayitlar = [
        _bildirim(
            bildirim_id="1607502",
            baslik="Pay Piyasasında Volatilite Bazlı Tedbir Sistemi",
            metin=(
                "VBTS kapsamında ANELE.E ve BIGEN.E payları "
                "15/05/2026 tarihli işlemlerden 12/06/2026 tarihli "
                "işlemlere kadar emir paketi tedbiri ile işlem görecektir."
            ),
        )
    ]

    istemci = KapVbtsClient(
        bildirimleri_getir=lambda _baslangic, _bitis: kayitlar,
    )

    dataset = istemci.fetch_dataset(
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
        fetched_at=datetime(
            2026,
            5,
            15,
            18,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert tuple(
        (tedbir.symbol, tedbir.measure_type)
        for tedbir in dataset.measures
    ) == (
        ("ANELE.IS", "EMIR_PAKETI"),
        ("BIGEN.IS", "EMIR_PAKETI"),
    )


def test_kap_vbts_istemcisi_ilgisiz_bildirimi_tedbir_saymaz() -> None:
    from backend.app.compliance.kap_vbts_client import KapVbtsClient

    kayitlar = [
        _bildirim(
            bildirim_id="finansal-rapor-1",
            baslik="Finansal Rapor",
            metin="Şirketin 2026 yılı finansal sonuçları açıklanmıştır.",
        )
    ]

    istemci = KapVbtsClient(
        bildirimleri_getir=lambda _baslangic, _bitis: kayitlar,
    )

    dataset = istemci.fetch_dataset(
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


def test_kap_kaynagi_hata_verirse_dogrulanmamis_bos_paket_donmez() -> None:
    from backend.app.compliance.kap_vbts_client import (
        KapVbtsClient,
        KapVbtsSourceError,
    )

    def hata_veren_kaynak(
        _baslangic: date,
        _bitis: date,
    ) -> list[dict[str, object]]:
        raise TimeoutError("KAP bağlantısı zaman aşımına uğradı.")

    istemci = KapVbtsClient(
        bildirimleri_getir=hata_veren_kaynak,
    )

    with pytest.raises(KapVbtsSourceError):
        istemci.fetch_dataset(
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


def test_vbts_bildiriminin_tarihleri_ayristirilamazsa_paket_reddedilir() -> None:
    from backend.app.compliance.kap_vbts_client import (
        KapVbtsClient,
        KapVbtsParseError,
    )

    kayitlar = [
        _bildirim(
            bildirim_id="bozuk-vbts-1",
            baslik="Pay Piyasasında Volatilite Bazlı Tedbir Sistemi",
            metin=(
                "VBTS kapsamında TEST.E paylarında belirsiz bir süre "
                "boyunca brüt takas uygulanacaktır."
            ),
        )
    ]

    istemci = KapVbtsClient(
        bildirimleri_getir=lambda _baslangic, _bitis: kayitlar,
    )

    with pytest.raises(KapVbtsParseError):
        istemci.fetch_dataset(
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