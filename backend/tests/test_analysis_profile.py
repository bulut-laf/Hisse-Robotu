from __future__ import annotations

import pytest

from backend.app.analysis.scan_filter import (
    NOTR_GORUNUM,
    POZITIF_GORUNUM,
)
from backend.app.backtest.analysis_profile import (
    AnalysisProfile,
    ORTAK_INDIRME_DONEMI,
    ORTAK_ISLEM_GUNU,
    gorunumleri_coz,
    sembolu_hazirla,
)


def test_ortak_profil_bes_yillik_karsilastirma_donemini_kullanir() -> None:
    profil = AnalysisProfile()

    assert profil.islem_gunu == ORTAK_ISLEM_GUNU == 1253
    assert profil.indirme_donemi == ORTAK_INDIRME_DONEMI == "5y"
    assert profil.minimum_bar_sayisi == 60
    assert profil.minimum_skor == 50


def test_ortak_profil_sinyal_ve_backtest_ayarlarini_uretir() -> None:
    profil = AnalysisProfile()

    sinyal = profil.sinyal_yapilandirmasi()
    backtest = profil.backtest_yapilandirmasi()

    assert sinyal.minimum_bar_sayisi == 60
    assert sinyal.izin_verilen_gorunumler == (
        POZITIF_GORUNUM,
        NOTR_GORUNUM,
    )
    assert backtest.elde_tutma_gunu == 10
    assert backtest.minimum_skor == 50
    assert backtest.islem_maliyeti_orani == pytest.approx(0.001)
    assert backtest.zarar_durdur_orani == pytest.approx(0.05)
    assert backtest.hedef_orani == pytest.approx(0.10)


def test_ozel_profil_yuzdeleri_orana_cevirir() -> None:
    profil = AnalysisProfile(
        pozisyon_yuzde=40.0,
        maliyet_yuzde=0.25,
        stop_yuzde=3.0,
        hedef_yuzde=7.0,
    )

    ayarlar = profil.backtest_yapilandirmasi()

    assert ayarlar.pozisyon_orani == pytest.approx(0.40)
    assert ayarlar.islem_maliyeti_orani == pytest.approx(0.0025)
    assert ayarlar.zarar_durdur_orani == pytest.approx(0.03)
    assert ayarlar.hedef_orani == pytest.approx(0.07)


def test_ayar_kimligi_ayni_profillerde_ayni_degisen_profillerde_farklidir() -> None:
    birinci = AnalysisProfile()
    ikinci = AnalysisProfile()
    farkli = AnalysisProfile(minimum_skor=55)

    assert birinci.ayar_kimligi == ikinci.ayar_kimligi
    assert birinci.ayar_kimligi != farkli.ayar_kimligi
    assert len(birinci.ayar_kimligi) == 12


def test_sembol_ve_gorunum_yardimcilari_dogrulanir() -> None:
    assert sembolu_hazirla(" thyao ") == "THYAO.IS"
    assert gorunumleri_coz("pozitif-notr") == (
        POZITIF_GORUNUM,
        NOTR_GORUNUM,
    )

    with pytest.raises(ValueError, match="Geçersiz teknik görünüm"):
        gorunumleri_coz("bilinmeyen")
