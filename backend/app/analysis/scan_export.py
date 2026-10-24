from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .scan_filter import FilteredScanResult


class ScanExportError(Exception):
    """Tarama sonucu dışa aktarılırken oluşan özel hata."""


@dataclass(frozen=True)
class ScanExportResult:
    """CSV dışa aktarma işleminin sonucunu temsil eder."""

    dosya_yolu: str
    satir_sayisi: int


CSV_ALANLARI = (
    "Durum",
    "Sira",
    "Sembol",
    "Analiz_Tarihi",
    "Skor",
    "Gorunum",
    "Kapanis",
    "RSI14",
    "Hacim_Orani",
    "Risk_Odul",
    "Hedef",
    "Risk_Filtresi",
    "Aciklama",
)


def tarama_sonucunu_csv_kaydet(
    sonuc: FilteredScanResult,
    dosya_yolu: str | Path,
) -> ScanExportResult:
    """
    Filtrelenmiş tarama sonucunu Excel uyumlu CSV dosyasına yazar.

    Aday ve elenen hisselerin analiz değerleri birlikte korunur.
    """
    yol = Path(dosya_yolu).expanduser()

    if yol.exists() and yol.is_dir():
        raise ScanExportError(
            f"CSV yolu bir klasör olamaz: {yol}"
        )

    satirlar = _csv_satirlarini_olustur(
        sonuc
    )

    try:
        yol.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with yol.open(
            mode="w",
            encoding="utf-8-sig",
            newline="",
        ) as dosya:
            yazici = csv.DictWriter(
                dosya,
                fieldnames=CSV_ALANLARI,
                delimiter=";",
            )

            yazici.writeheader()
            yazici.writerows(satirlar)

    except OSError as hata:
        raise ScanExportError(
            f"CSV dosyası oluşturulamadı: {hata}"
        ) from hata

    return ScanExportResult(
        dosya_yolu=str(yol.resolve()),
        satir_sayisi=len(satirlar),
    )


def _analiz_satiri_olustur(
    hisse: Any,
    durum: str,
    sira: int | str,
    aciklama: str,
) -> dict[str, object]:
    risk_filtresi = (
        "Geçti"
        if hisse.risk_plani.filtreyi_gecti
        else "Elendi"
    )

    return {
        "Durum": durum,
        "Sira": sira,
        "Sembol": hisse.sembol,
        "Analiz_Tarihi": hisse.analiz_tarihi,
        "Skor": hisse.sinyal.skor,
        "Gorunum": hisse.sinyal.karar,
        "Kapanis": f"{hisse.kapanis:.2f}",
        "RSI14": f"{hisse.rsi14:.2f}",
        "Hacim_Orani": f"{hisse.hacim_orani:.2f}",
        "Risk_Odul": (
            f"{hisse.risk_plani.risk_odul_orani:.2f}"
        ),
        "Hedef": (
            f"{hisse.risk_plani.hedef_fiyat:.2f}"
        ),
        "Risk_Filtresi": risk_filtresi,
        "Aciklama": aciklama,
    }


def _bos_satir_olustur(
    durum: str,
    sembol: str,
    aciklama: str,
) -> dict[str, object]:
    return {
        "Durum": durum,
        "Sira": "",
        "Sembol": sembol,
        "Analiz_Tarihi": "",
        "Skor": "",
        "Gorunum": "",
        "Kapanis": "",
        "RSI14": "",
        "Hacim_Orani": "",
        "Risk_Odul": "",
        "Hedef": "",
        "Risk_Filtresi": "",
        "Aciklama": aciklama,
    }


def _csv_satirlarini_olustur(
    sonuc: FilteredScanResult,
) -> list[dict[str, object]]:
    satirlar: list[dict[str, object]] = []

    for sira, hisse in enumerate(
        sonuc.adaylar,
        start=1,
    ):
        satirlar.append(
            _analiz_satiri_olustur(
                hisse=hisse,
                durum="Aday",
                sira=sira,
                aciklama="",
            )
        )

    for elenen in sonuc.elenenler:
        aciklama = " | ".join(
            elenen.nedenler
        )

        if elenen.sonuc is not None:
            satirlar.append(
                _analiz_satiri_olustur(
                    hisse=elenen.sonuc,
                    durum="Elendi",
                    sira="",
                    aciklama=aciklama,
                )
            )
        else:
            satirlar.append(
                _bos_satir_olustur(
                    durum="Elendi",
                    sembol=elenen.sembol,
                    aciklama=aciklama,
                )
            )

    for hata in sonuc.hatalar:
        satirlar.append(
            _bos_satir_olustur(
                durum="Hata",
                sembol=hata.sembol,
                aciklama=hata.hata,
            )
        )

    return satirlar