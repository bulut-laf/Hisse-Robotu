from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.analysis.scan_filter import (
    FilteredScanResult,
    ScanFilterCriteria,
    ScanRejection,
)
from backend.app.analysis.stock_scanner import ScanFailure
from backend.app.history.scan_history import (
    ScanHistoryError,
    ScanHistoryRepository,
)
from backend.app.history.scan_history_reader import (
    ScanHistoryReader,
)


def ornek_hisse(
    sembol: str,
    skor: int,
    gorunum: str,
    kapanis: float,
    rsi14: float,
    hacim_orani: float,
    risk_odul_orani: float,
    hedef_fiyat: float,
    risk_filtresi_gecti: bool,
) -> Any:
    return SimpleNamespace(
        sembol=sembol,
        analiz_tarihi="2026-07-22",
        kapanis=kapanis,
        rsi14=rsi14,
        hacim_orani=hacim_orani,
        sinyal=SimpleNamespace(
            skor=skor,
            karar=gorunum,
        ),
        risk_plani=SimpleNamespace(
            risk_odul_orani=risk_odul_orani,
            hedef_fiyat=hedef_fiyat,
            filtreyi_gecti=risk_filtresi_gecti,
        ),
    )


def ornek_sonuc() -> FilteredScanResult:
    birinci_aday = ornek_hisse(
        sembol="AAA.IS",
        skor=82,
        gorunum="Pozitif Teknik Görünüm",
        kapanis=100.0,
        rsi14=62.50,
        hacim_orani=1.80,
        risk_odul_orani=2.40,
        hedef_fiyat=118.0,
        risk_filtresi_gecti=True,
    )

    ikinci_aday = ornek_hisse(
        sembol="CCC.IS",
        skor=68,
        gorunum="Nötr Teknik Görünüm",
        kapanis=75.0,
        rsi14=54.25,
        hacim_orani=1.25,
        risk_odul_orani=2.05,
        hedef_fiyat=84.0,
        risk_filtresi_gecti=True,
    )

    elenen_hisse = ornek_hisse(
        sembol="BBB.IS",
        skor=25,
        gorunum="Negatif Teknik Görünüm",
        kapanis=90.0,
        rsi14=41.75,
        hacim_orani=0.60,
        risk_odul_orani=0.70,
        hedef_fiyat=95.0,
        risk_filtresi_gecti=False,
    )

    return FilteredScanResult(
        adaylar=(
            birinci_aday,
            ikinci_aday,
        ),
        elenenler=(
            ScanRejection(
                sembol="BBB.IS",
                nedenler=(
                    "Sinyal skoru yetersiz.",
                    "Risk/ödül filtresini geçemedi.",
                ),
                sonuc=elenen_hisse,
            ),
        ),
        hatalar=(
            ScanFailure(
                sembol="HATALI.IS",
                hata="Fiyat verisi bulunamadı.",
            ),
        ),
    )


def ornek_kriterler() -> ScanFilterCriteria:
    return ScanFilterCriteria(
        minimum_skor=50,
        minimum_hacim_orani=1.00,
        risk_odul_filtresi_gerekli=True,
        izin_verilen_gorunumler=(
            "Pozitif Teknik Görünüm",
            "Nötr Teknik Görünüm",
        ),
    )


def ornek_veritabani_olustur(
    tmp_path: Path,
) -> Path:
    veritabani = tmp_path / "scan_history.db"

    repository = ScanHistoryRepository(
        veritabani
    )

    repository.taramayi_kaydet(
        sonuc=ornek_sonuc(),
        kriterler=ornek_kriterler(),
        profil_adi="Dengeli",
        olusturma_zamani=(
            "2026-07-23T20:00:00+03:00"
        ),
    )

    return veritabani


def test_tarama_ozeti_ve_filtreler_okunur(
    tmp_path: Path,
) -> None:
    veritabani = ornek_veritabani_olustur(
        tmp_path
    )

    reader = ScanHistoryReader(
        veritabani
    )

    detay = reader.tarama_detayini_getir(
        tarama_id=1
    )

    assert detay.ozet.tarama_id == 1
    assert detay.ozet.profil_adi == "Dengeli"
    assert detay.ozet.olusturma_zamani == (
        "2026-07-23T20:00:00+03:00"
    )
    assert detay.ozet.minimum_skor == 50
    assert (
        detay.ozet.minimum_hacim_orani
        == pytest.approx(1.00)
    )
    assert detay.ozet.risk_odul_gerekli is True
    assert detay.ozet.izin_verilen_gorunumler == (
        "Pozitif Teknik Görünüm",
        "Nötr Teknik Görünüm",
    )
    assert detay.ozet.toplam_sayi == 4
    assert detay.ozet.aday_sayisi == 2
    assert detay.ozet.elenen_sayisi == 1
    assert detay.ozet.hatali_sayisi == 1


def test_aday_hisse_degerleri_okunur(
    tmp_path: Path,
) -> None:
    veritabani = ornek_veritabani_olustur(
        tmp_path
    )

    detay = ScanHistoryReader(
        veritabani
    ).tarama_detayini_getir(
        tarama_id=1
    )

    aday = detay.kayitlar[0]

    assert aday.durum == "Aday"
    assert aday.sira == 1
    assert aday.sembol == "AAA.IS"
    assert aday.analiz_tarihi == "2026-07-22"
    assert aday.skor == 82
    assert (
        aday.teknik_gorunum
        == "Pozitif Teknik Görünüm"
    )
    assert aday.kapanis == pytest.approx(
        100.0
    )
    assert aday.rsi14 == pytest.approx(
        62.50
    )
    assert aday.hacim_orani == pytest.approx(
        1.80
    )
    assert (
        aday.risk_odul_orani
        == pytest.approx(2.40)
    )
    assert aday.hedef_fiyat == pytest.approx(
        118.0
    )
    assert aday.risk_filtresi_gecti is True
    assert aday.aciklama == ""


def test_elenen_ve_hata_kayitlari_okunur(
    tmp_path: Path,
) -> None:
    veritabani = ornek_veritabani_olustur(
        tmp_path
    )

    detay = ScanHistoryReader(
        veritabani
    ).tarama_detayini_getir(
        tarama_id=1
    )

    elenen = next(
        kayit
        for kayit in detay.kayitlar
        if kayit.sembol == "BBB.IS"
    )

    hata = next(
        kayit
        for kayit in detay.kayitlar
        if kayit.sembol == "HATALI.IS"
    )

    assert elenen.durum == "Elendi"
    assert elenen.sira is None
    assert elenen.skor == 25
    assert elenen.kapanis == pytest.approx(
        90.0
    )
    assert (
        elenen.risk_filtresi_gecti
        is False
    )
    assert "Sinyal skoru yetersiz" in (
        elenen.aciklama
    )

    assert hata.durum == "Hata"
    assert hata.sira is None
    assert hata.skor is None
    assert hata.kapanis is None
    assert hata.rsi14 is None
    assert hata.risk_filtresi_gecti is None
    assert hata.aciklama == (
        "Fiyat verisi bulunamadı."
    )


def test_kayitlar_durum_ve_siraya_gore_siralanir(
    tmp_path: Path,
) -> None:
    veritabani = ornek_veritabani_olustur(
        tmp_path
    )

    detay = ScanHistoryReader(
        veritabani
    ).tarama_detayini_getir(
        tarama_id=1
    )

    assert [
        kayit.sembol
        for kayit in detay.kayitlar
    ] == [
        "AAA.IS",
        "CCC.IS",
        "BBB.IS",
        "HATALI.IS",
    ]

    assert [
        kayit.durum
        for kayit in detay.kayitlar
    ] == [
        "Aday",
        "Aday",
        "Elendi",
        "Hata",
    ]


def test_gecersiz_tarama_kimligi_hata_verir(
    tmp_path: Path,
) -> None:
    veritabani = ornek_veritabani_olustur(
        tmp_path
    )

    reader = ScanHistoryReader(
        veritabani
    )

    with pytest.raises(
        ValueError,
        match="pozitif",
    ):
        reader.tarama_detayini_getir(
            tarama_id=0
        )


def test_bulunmayan_tarama_hata_verir(
    tmp_path: Path,
) -> None:
    veritabani = ornek_veritabani_olustur(
        tmp_path
    )

    reader = ScanHistoryReader(
        veritabani
    )

    with pytest.raises(
        ValueError,
        match="Tarama bulunamadı",
    ):
        reader.tarama_detayini_getir(
            tarama_id=999
        )


def test_gecersiz_veritabani_yollari_hata_verir(
    tmp_path: Path,
) -> None:
    bulunmayan_dosya = (
        tmp_path
        / "bulunmayan.db"
    )

    with pytest.raises(
        ScanHistoryError,
        match="bulunamadı",
    ):
        ScanHistoryReader(
            bulunmayan_dosya
        )

    with pytest.raises(
        ScanHistoryError,
        match="klasör olamaz",
    ):
        ScanHistoryReader(
            tmp_path
        )