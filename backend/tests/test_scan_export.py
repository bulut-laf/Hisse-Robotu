from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.analysis.scan_export import (
    ScanExportError,
    tarama_sonucunu_csv_kaydet,
)
from backend.app.analysis.scan_filter import (
    FilteredScanResult,
    ScanRejection,
)
from backend.app.analysis.stock_scanner import (
    ScanFailure,
)


def ornek_aday() -> Any:
    return SimpleNamespace(
        sembol="AAA.IS",
        analiz_tarihi="2026-07-22",
        kapanis=100.0,
        rsi14=58.25,
        hacim_orani=1.40,
        sinyal=SimpleNamespace(
            skor=72,
            karar="Pozitif Teknik Görünüm",
        ),
        risk_plani=SimpleNamespace(
            risk_odul_orani=2.25,
            hedef_fiyat=115.0,
            filtreyi_gecti=True,
        ),
    )


def ornek_sonuc() -> FilteredScanResult:
    return FilteredScanResult(
        adaylar=(
            ornek_aday(),
        ),
        elenenler=(
            ScanRejection(
                sembol="BBB.IS",
                nedenler=(
                    "Sinyal skoru yetersiz.",
                    "Risk/ödül filtresini geçemedi.",
                ),
            ),
        ),
        hatalar=(
            ScanFailure(
                sembol="HATALI.IS",
                hata="Veri bulunamadı.",
            ),
        ),
    )


def csv_satirlarini_oku(
    dosya: Path,
) -> list[dict[str, str]]:
    with dosya.open(
        encoding="utf-8-sig",
        newline="",
    ) as akim:
        return list(
            csv.DictReader(
                akim,
                delimiter=";",
            )
        )


def test_tarama_sonucu_csv_dosyasina_yazilir(
    tmp_path: Path,
) -> None:
    dosya = tmp_path / "tarama.csv"

    disari_aktarma = tarama_sonucunu_csv_kaydet(
        sonuc=ornek_sonuc(),
        dosya_yolu=dosya,
    )

    assert dosya.exists()
    assert disari_aktarma.satir_sayisi == 3
    assert disari_aktarma.dosya_yolu == str(
        dosya.resolve()
    )


def test_aday_bilgileri_csvye_dogru_yazilir(
    tmp_path: Path,
) -> None:
    dosya = tmp_path / "tarama.csv"

    tarama_sonucunu_csv_kaydet(
        sonuc=ornek_sonuc(),
        dosya_yolu=dosya,
    )

    satirlar = csv_satirlarini_oku(
        dosya
    )

    aday = satirlar[0]

    assert aday["Durum"] == "Aday"
    assert aday["Sembol"] == "AAA.IS"
    assert aday["Skor"] == "72"
    assert aday["Kapanis"] == "100.00"
    assert aday["Risk_Odul"] == "2.25"
    assert aday["Risk_Filtresi"] == "Geçti"


def test_elenen_ve_hata_satirlari_yazilir(
    tmp_path: Path,
) -> None:
    dosya = tmp_path / "tarama.csv"

    tarama_sonucunu_csv_kaydet(
        sonuc=ornek_sonuc(),
        dosya_yolu=dosya,
    )

    satirlar = csv_satirlarini_oku(
        dosya
    )

    assert satirlar[1]["Durum"] == "Elendi"
    assert satirlar[1]["Sembol"] == "BBB.IS"
    assert "Risk/ödül" in satirlar[1]["Aciklama"]

    assert satirlar[2]["Durum"] == "Hata"
    assert satirlar[2]["Sembol"] == "HATALI.IS"
    assert satirlar[2]["Aciklama"] == "Veri bulunamadı."


def test_olmayan_ust_klasor_otomatik_olusturulur(
    tmp_path: Path,
) -> None:
    dosya = (
        tmp_path
        / "raporlar"
        / "gunluk"
        / "tarama.csv"
    )

    tarama_sonucunu_csv_kaydet(
        sonuc=ornek_sonuc(),
        dosya_yolu=dosya,
    )

    assert dosya.exists()


def test_klasor_csv_yolu_olarak_kullanilamaz(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ScanExportError,
        match="klasör olamaz",
    ):
        tarama_sonucunu_csv_kaydet(
            sonuc=ornek_sonuc(),
            dosya_yolu=tmp_path,
        )


def test_elenen_hissenin_analiz_degerleri_csvye_yazilir(
    tmp_path: Path,
) -> None:
    elenen_analiz = SimpleNamespace(
        sembol="BBB.IS",
        analiz_tarihi="2026-07-22",
        kapanis=90.0,
        rsi14=42.50,
        hacim_orani=0.65,
        sinyal=SimpleNamespace(
            skor=28,
            karar="Negatif Teknik Görünüm",
        ),
        risk_plani=SimpleNamespace(
            risk_odul_orani=0.75,
            hedef_fiyat=95.0,
            filtreyi_gecti=False,
        ),
    )

    sonuc = FilteredScanResult(
        adaylar=(),
        elenenler=(
            ScanRejection(
                sembol="BBB.IS",
                nedenler=(
                    "Sinyal skoru yetersiz.",
                ),
                sonuc=elenen_analiz,
            ),
        ),
        hatalar=(),
    )

    dosya = tmp_path / "elenenler.csv"

    tarama_sonucunu_csv_kaydet(
        sonuc=sonuc,
        dosya_yolu=dosya,
    )

    satirlar = csv_satirlarini_oku(
        dosya
    )

    elenen = satirlar[0]

    assert elenen["Durum"] == "Elendi"
    assert elenen["Sembol"] == "BBB.IS"
    assert elenen["Skor"] == "28"
    assert elenen["Kapanis"] == "90.00"
    assert elenen["RSI14"] == "42.50"
    assert elenen["Hacim_Orani"] == "0.65"
    assert elenen["Risk_Odul"] == "0.75"
    assert elenen["Risk_Filtresi"] == "Elendi"