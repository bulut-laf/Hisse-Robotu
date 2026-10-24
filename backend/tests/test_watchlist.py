from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.analysis.watchlist import (
    WatchlistError,
    izleme_listesi_yukle,
)


def dosya_olustur(
    tmp_path: Path,
    icerik: str,
) -> Path:
    dosya = tmp_path / "favoriler.txt"

    dosya.write_text(
        icerik,
        encoding="utf-8",
    )

    return dosya


def test_satirlardan_semboller_yuklenir(
    tmp_path: Path,
) -> None:
    dosya = dosya_olustur(
        tmp_path,
        "THYAO\nASELS\nTUPRS\n",
    )

    liste = izleme_listesi_yukle(
        dosya
    )

    assert liste.semboller == (
        "THYAO",
        "ASELS",
        "TUPRS",
    )
    assert liste.sembol_sayisi == 3


def test_farkli_ayiricilar_desteklenir(
    tmp_path: Path,
) -> None:
    dosya = dosya_olustur(
        tmp_path,
        "THYAO, ASELS; TUPRS EREGL",
    )

    liste = izleme_listesi_yukle(
        dosya
    )

    assert liste.semboller == (
        "THYAO",
        "ASELS",
        "TUPRS",
        "EREGL",
    )


def test_yorumlar_yok_sayilir(
    tmp_path: Path,
) -> None:
    dosya = dosya_olustur(
        tmp_path,
        (
            "# Ana hisseler\n"
            "THYAO  # Havacılık\n"
            "ASELS  # Savunma\n"
        ),
    )

    liste = izleme_listesi_yukle(
        dosya
    )

    assert liste.semboller == (
        "THYAO",
        "ASELS",
    )


def test_semboller_buyuk_harfe_cevrilir_ve_tekrarlar_silinir(
    tmp_path: Path,
) -> None:
    dosya = dosya_olustur(
        tmp_path,
        "thyao\nASELS\nTHYAO\nasels.is\n",
    )

    liste = izleme_listesi_yukle(
        dosya
    )

    assert liste.semboller == (
        "THYAO",
        "ASELS",
        "ASELS.IS",
    )


def test_bulunamayan_dosya_hata_verir(
    tmp_path: Path,
) -> None:
    bulunamayan = (
        tmp_path / "bulunamayan.txt"
    )

    with pytest.raises(
        WatchlistError,
        match="bulunamadı",
    ):
        izleme_listesi_yukle(
            bulunamayan
        )


def test_bos_liste_hata_verir(
    tmp_path: Path,
) -> None:
    dosya = dosya_olustur(
        tmp_path,
        "# Yalnızca açıklama var\n\n",
    )

    with pytest.raises(
        WatchlistError,
        match="geçerli hisse sembolü",
    ):
        izleme_listesi_yukle(
            dosya
        )

def test_utf8_bom_otomatik_temizlenir(tmp_path: Path) -> None:
    dosya = tmp_path / "favoriler.txt"
    dosya.write_text("\ufeffBIGEN\nCMBTN\n", encoding="utf-8")

    liste = izleme_listesi_yukle(dosya)

    assert liste.semboller == ("BIGEN", "CMBTN")
