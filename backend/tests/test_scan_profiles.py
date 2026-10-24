from __future__ import annotations

import pytest

from backend.app.analysis.scan_filter import (
    NOTR_GORUNUM,
    POZITIF_GORUNUM,
    TUM_GORUNUMLER,
)
from backend.app.analysis.scan_profiles import (
    profil_adlari,
    profil_al,
    tum_profilleri_getir,
)


def test_profil_adlari_dogru_sirada_doner() -> None:
    assert profil_adlari() == (
        "gevsek",
        "dengeli",
        "siki",
    )


def test_gevsek_profil_dogru_kriterleri_icerir() -> None:
    profil = profil_al("gevsek")

    assert profil.ad == "Gevşek"
    assert profil.kriterler.minimum_skor == 20
    assert profil.kriterler.minimum_hacim_orani == 0.50
    assert profil.kriterler.risk_odul_filtresi_gerekli is False
    assert profil.kriterler.izin_verilen_gorunumler == TUM_GORUNUMLER


def test_dengeli_profil_dogru_kriterleri_icerir() -> None:
    profil = profil_al("dengeli")

    assert profil.ad == "Dengeli"
    assert profil.kriterler.minimum_skor == 50
    assert profil.kriterler.minimum_hacim_orani == 1.00
    assert profil.kriterler.risk_odul_filtresi_gerekli is False
    assert profil.kriterler.izin_verilen_gorunumler == (
        POZITIF_GORUNUM,
        NOTR_GORUNUM,
    )


def test_siki_profil_dogru_kriterleri_icerir() -> None:
    profil = profil_al("siki")

    assert profil.ad == "Sıkı"
    assert profil.kriterler.minimum_skor == 70
    assert profil.kriterler.minimum_hacim_orani == 1.20
    assert profil.kriterler.risk_odul_filtresi_gerekli is True
    assert profil.kriterler.izin_verilen_gorunumler == (
        POZITIF_GORUNUM,
    )


def test_profil_adi_temizlenir() -> None:
    profil = profil_al("  DENGELI  ")

    assert profil.ad == "Dengeli"


def test_bilinmeyen_profil_hata_verir() -> None:
    with pytest.raises(
        ValueError,
        match="Bilinmeyen tarama profili",
    ):
        profil_al("bilinmeyen")


def test_tum_profiller_getirilebilir() -> None:
    profiller = tum_profilleri_getir()

    assert len(profiller) == 3

    assert [
        profil.ad
        for profil in profiller
    ] == [
        "Gevşek",
        "Dengeli",
        "Sıkı",
    ]